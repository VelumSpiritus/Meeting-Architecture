"""Lossless, content-addressed pages for Vigil's sparse v3 sigma delta log.

The historical log remains authoritative and untouched.  This module derives a
page-map head from it with bounded memory, then exposes the current sparse
tables as lazy mutable mappings.  A page is materialized only when the existing
Predictor asks for an address in that band.
"""
from __future__ import annotations

import hashlib
import io
import os
from collections import OrderedDict
from collections.abc import Mapping, MutableMapping
from pathlib import Path
import shutil
import tempfile

import ark_io
import native_json as json


SCHEMA = "ark-vigil-sigma-page-carrier-v1"
PAGE_MAGIC = b"ARKSIGP1"
ENTRY_BYTES = 20
DEFAULT_SPOOL_HANDLES = 64


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
    pending = path.with_suffix(path.suffix + ".%d.pending" % os.getpid())
    ark_io.give_file(str(pending), raw)
    os.replace(pending, path)


def _mature_head(page_root: Path, source_path: Path, page_bits: int) -> dict | None:
    """Receive an unchanged append-only generation without replaying its lineage.

    The sigma log's only admitted mutation is append. Size and mtime identity therefore witness
    that HEAD still names the current generation; page content remains independently digest-gated
    when touched. Any movement returns to full derivation instead of being narrated as a miss.
    """
    try:
        head = json.loads(ark_io.receive_file(str(page_root / "HEAD.json")).decode("utf-8"))
        if head.get("schema") != SCHEMA:
            return None
        address = str(head.get("manifest") or "")
        manifest = json.loads(ark_io.receive_file(
            str(page_root / "manifests" / (address + ".json"))).decode("utf-8"))
        stat = source_path.stat()
        if not (
            manifest.get("schema") == SCHEMA
            and int(manifest.get("page_bits", -1)) == int(page_bits)
            and os.path.abspath(str(manifest.get("source") or "")) == os.path.abspath(str(source_path))
            and int(manifest.get("source_bytes", -1)) == stat.st_size
            and int(manifest.get("source_mtime_ns", -1)) == stat.st_mtime_ns
            and int(manifest.get("complete_cursor", -1)) == stat.st_size
            and int(manifest.get("torn_tail_bytes", -1)) == 0
        ):
            return None
        return manifest
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _header(stream) -> tuple[dict, bytes, int]:
    raw = stream.readline()
    if not raw.endswith(b"\n"):
        raise ValueError("sigma-page-source-has-no-complete-header")
    try:
        value = json.loads(raw[:-1].decode("utf-8"))
    except Exception as exc:
        raise ValueError("sigma-page-source-header-unreadable") from exc
    if value.get("format") != "ark-sigma-v3-delta-log":
        raise ValueError("sigma-page-source-is-not-v3-delta-log")
    return value, raw, len(raw)


def _frames(stream, start: int):
    """Yield complete frames; a torn tail remains an addressed source residual."""
    stream.seek(start)
    cursor = start
    while True:
        mark = stream.read(1)
        if not mark:
            return
        size_raw = stream.read(8)
        if mark != b"F" or len(size_raw) != 8:
            return
        size = int.from_bytes(size_raw, "big")
        frame = stream.read(size)
        if len(frame) != size:
            return
        newline = frame.find(b"\n")
        if newline < 0 or (len(frame) - newline - 1) % 22:
            return
        try:
            state = json.loads(frame[:newline].decode("utf-8"))
        except Exception:
            return
        cursor += 9 + size
        yield cursor, state, memoryview(frame)[newline + 1:]


def _entry(raw: bytes) -> tuple[int, int, int, int, int]:
    if len(raw) != 22 or raw[:1] != b"D":
        raise ValueError("sigma-page-delta-entry-unreadable")
    return (
        raw[1], int.from_bytes(raw[2:6], "big"),
        int.from_bytes(raw[6:10], "big", signed=True),
        int.from_bytes(raw[10:14], "big"),
        int.from_bytes(raw[14:22], "big", signed=True),
    )


def _page_bytes(*, context: int, band: int, page_bits: int,
                cells: dict[int, tuple[int, int, int]]) -> bytes:
    head = json.dumps({"schema": SCHEMA, "context": context, "band": band,
                       "page_bits": page_bits, "cells": len(cells)},
                      ensure_ascii=True, sort_keys=True).encode("utf-8")
    body = bytearray(PAGE_MAGIC + len(head).to_bytes(4, "big") + head)
    for index in sorted(cells):
        w, count, remainder = cells[index]
        if not (w or count or remainder):
            continue
        body += (int(index).to_bytes(4, "big")
                 + int(w).to_bytes(4, "big", signed=True)
                 + int(count).to_bytes(4, "big")
                 + int(remainder).to_bytes(8, "big", signed=True))
    return bytes(body)


class _PackedCells(Mapping):
    """Immutable addressed view of a page whose sorted keys were already witnessed."""

    def __init__(self, raw: bytes, start: int):
        self.raw, self.start = raw, start
        self.count = (len(raw) - start) // ENTRY_BYTES

    def __len__(self):
        return self.count

    def _key(self, slot):
        offset = self.start + slot * ENTRY_BYTES
        return int.from_bytes(self.raw[offset:offset + 4], "big")

    def _value(self, slot):
        offset = self.start + slot * ENTRY_BYTES
        return (int.from_bytes(self.raw[offset + 4:offset + 8], "big", signed=True),
                int.from_bytes(self.raw[offset + 8:offset + 12], "big"),
                int.from_bytes(self.raw[offset + 12:offset + 20], "big", signed=True))

    def __getitem__(self, key):
        lo, hi = 0, self.count
        while lo < hi:
            mid = (lo + hi) // 2
            found = self._key(mid)
            if found < key:
                lo = mid + 1
            elif found > key:
                hi = mid
            else:
                return self._value(mid)
        raise KeyError(key)

    def __iter__(self):
        for slot in range(self.count):
            yield self._key(slot)

    def items(self):
        for slot in range(self.count):
            yield self._key(slot), self._value(slot)


def _read_page(raw: bytes, *, expected: str,
               ordered: set[str] | None = None) -> tuple[dict, Mapping]:
    if _sha(raw) != expected:
        raise ValueError("sigma-page-object-digest-mismatch")
    if not raw.startswith(PAGE_MAGIC) or len(raw) < len(PAGE_MAGIC) + 4:
        raise ValueError("sigma-page-object-unreadable")
    offset = len(PAGE_MAGIC)
    head_size = int.from_bytes(raw[offset:offset + 4], "big")
    offset += 4
    try:
        head = json.loads(raw[offset:offset + head_size].decode("utf-8"))
    except Exception as exc:
        raise ValueError("sigma-page-object-header-unreadable") from exc
    offset += head_size
    if head.get("schema") != SCHEMA or (len(raw) - offset) % ENTRY_BYTES:
        raise ValueError("sigma-page-object-shape")
    start = offset
    # The digest still runs on EVERY receipt. A prior order witness applies only to these
    # exact immutable bytes, so an evicted page can answer one cell without rebuilding all
    # its neighbours. Older unordered pages retain the full decoder's existing behavior.
    if ordered is not None and expected in ordered:
        return head, _PackedCells(raw, start)
    cells = {}
    previous_index = None
    strictly_ordered = True
    while offset < len(raw):
        index = int.from_bytes(raw[offset:offset + 4], "big")
        if previous_index is not None and index <= previous_index:
            strictly_ordered = False
        previous_index = index
        cells[index] = (
            int.from_bytes(raw[offset + 4:offset + 8], "big", signed=True),
            int.from_bytes(raw[offset + 8:offset + 12], "big"),
            int.from_bytes(raw[offset + 12:offset + 20], "big", signed=True),
        )
        offset += ENTRY_BYTES
    if len(cells) != int(head.get("cells") or 0):
        raise ValueError("sigma-page-object-cell-count")
    # The serialized keys, not the deduplicated dict, must be strictly increasing.
    # Legacy duplicate keys retain the decoder's last-write-wins mapping semantics.
    if ordered is not None and strictly_ordered:
        ordered.add(expected)
        return head, _PackedCells(raw, start)
    return head, cells


class BandSpoolFeeder:
    """Feed arbitrarily many bands through one finite descriptor window.

    The window is a physical projection, never a bound on the lineage. A band
    evicted from the window is closed and later reopened append-only at the same
    address, so descriptor pressure changes neither ordering within that band
    nor any byte it receives.
    """

    def __init__(self, root: Path, max_open: int = DEFAULT_SPOOL_HANDLES):
        self.root = Path(root)
        self.max_open = max(1, int(max_open))
        self.handles = OrderedDict()
        self.bands = set()
        self.peak_open = 0

    def feed(self, key: tuple[int, int], raw: bytes) -> None:
        handle = self.handles.pop(key, None)
        if handle is None:
            if len(self.handles) >= self.max_open:
                _old_key, old_handle = self.handles.popitem(last=False)
                old_handle.close()
            handle = (self.root / ("%03d-%08x.bin" % key)).open("ab")
        self.handles[key] = handle
        self.bands.add(key)
        self.peak_open = max(self.peak_open, len(self.handles))
        handle.write(raw)

    def close(self) -> None:
        while self.handles:
            _key, handle = self.handles.popitem(last=False)
            handle.close()


def _objects_whole(page_root: Path, manifest: dict) -> bool:
    """Witness every object named by a generation before reusing it for repair."""
    objects = page_root / "objects"
    try:
        for address in set((manifest.get("pages") or {}).values()):
            raw = ark_io.receive_file(str(objects / (str(address) + ".page")))
            if _sha(raw) != str(address):
                return False
        return True
    except OSError:
        return False


def _seat_object(target: Path, raw: bytes, address: str) -> None:
    """Land immutable bytes atomically; retain any interrupted prior landing as evidence."""
    if target.is_file():
        try:
            prior = ark_io.receive_file(str(target))
        except FileNotFoundError:
            prior = None
        if prior is None:
            pass
        elif _sha(prior) == address:
            return
        else:
            prior_digest = _sha(prior)
            witness = target.with_name(target.name + ".corrupt-" + prior_digest)
            if not witness.exists():
                # A competing repair may move the same bad landing first. Either outcome preserves it.
                try:
                    os.replace(target, witness)
                except FileNotFoundError:
                    pass
    fd, pending_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".pending",
                                        dir=str(target.parent))
    os.close(fd)
    pending = Path(pending_name)
    try:
        ark_io.give_file(str(pending), raw)
        landed = ark_io.receive_file(str(pending))
        if _sha(landed) != address:
            raise ValueError("sigma-page-object-atomic-landing-mismatch")
        os.replace(pending, target)
    finally:
        try:
            pending.unlink()
        except FileNotFoundError:
            pass


def advance_deposit(sigma, source: str, *, frame: bytes, prior_size: int) -> dict:
    """Advance a witnessed page head from the exact append just given to the delta log.

    This is the inverse side of the finite page realization: the application already holds the
    changed cells and the exact frame it appended, so replaying historical frames would add no
    evidence.  If any parent/source relation disagrees, refuse this fast path and let ``build``
    retain its full authoritative recovery derivation on the next rise.
    """
    store = getattr(sigma, "page_store", None)
    if store is None:
        raise ValueError("sigma-page-advance-has-no-parent-store")
    source_path = Path(source)
    parent = store.manifest
    if (int(parent.get("complete_cursor", -1)) != int(prior_size)
            or int(parent.get("torn_tail_bytes", -1)) != 0):
        raise ValueError("sigma-page-advance-parent-not-complete")
    stat = source_path.stat()
    if stat.st_size != int(prior_size) + len(frame):
        raise ValueError("sigma-page-advance-source-moved")

    parsed = list(_frames(io.BytesIO(frame), 0))
    if len(parsed) != 1 or parsed[0][0] != len(frame):
        raise ValueError("sigma-page-advance-frame-unreadable")
    _cursor, state, entries = parsed[0]
    updates = {}
    for offset in range(0, len(entries), 22):
        context, index, w, count, remainder = _entry(bytes(entries[offset:offset + 22]))
        updates.setdefault((context, index >> store.page_bits), {})[index] = (
            w, count, remainder)

    pages = dict(parent.get("pages") or {})
    occupied = int(parent.get("occupied_buckets") or 0)
    precision = int(parent.get("precision_axes") or 0)
    changed_pages = []
    # Freeze only the already-admitted finite decoded lease.  Advancing an uncached early band
    # may evict a later changed band from the live LRU; without this snapshot, iteration order
    # decides whether evidence physically present at entry is needlessly rematerialized.
    held_pages = {key: dict(cells) for key, cells in store.cache.items()}
    for (context, band), changed in sorted(updates.items()):
        key = "%d:%d" % (context, band)
        address = pages.get(key)
        cache_key = (context, band)
        held_cells = held_pages.get(cache_key)
        if held_cells is not None:
            # This application's reading already paid for this exact parent page.  Copy the
            # decoded relation before applying its delta; rereading the immutable object here
            # rematerializes evidence that is still physically present in the admitted lease.
            cells = dict(held_cells)
            if cache_key in store.cache:
                store.cache.move_to_end(cache_key)
        elif address:
            raw = ark_io.receive_file(str(store.root / "objects" / (address + ".page")))
            _head, cells = _read_page(raw, expected=address)
        else:
            cells = {}
        for index, value in changed.items():
            old = cells.get(index, (0, 0, 0))
            occupied += int(bool(value[1])) - int(bool(old[1]))
            precision += int(bool(value[2])) - int(bool(old[2]))
            if any(value):
                cells[index] = value
            else:
                cells.pop(index, None)
        if cells:
            raw = _page_bytes(context=context, band=band,
                              page_bits=store.page_bits, cells=cells)
            address = _sha(raw)
            _seat_object(store.root / "objects" / (address + ".page"), raw, address)
            pages[key] = address
        else:
            pages.pop(key, None)
            address = None
        # The cache remains finite, but what it holds now belongs to the newly seated head.  A
        # later reading of the same relation therefore receives these cells without replaying
        # either the parent object or the append it just witnessed.
        store.cache[cache_key] = dict(cells)
        store.cache.move_to_end(cache_key)
        while len(store.cache) > store.cache_pages:
            store.cache.popitem(last=False)
        changed_pages.append({"page": key, "address": address})

    parent_address = str(parent.get("generation_address")
                         or parent.get("source_sha256") or "")
    append_sha256 = _sha(frame)
    generation_address = _sha(
        (parent_address + "\0" + str(prior_size) + "\0" + append_sha256).encode("ascii"))
    manifest = dict(parent)
    manifest.update({
        "generation_address": generation_address,
        "generation_kind": "witnessed-append-chain",
        "parent_generation": parent_address,
        "append_sha256": append_sha256,
        "append_bytes": len(frame),
        "source_sha256": None,
        "source_bytes": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "complete_cursor": stat.st_size,
        "torn_tail_bytes": 0,
        "torn_tail": None,
        "pages": pages,
        "registers": {"hist": int(state.get("hist", 0)),
                      "bitreg": int(state.get("bitreg", 0)),
                      "c0": int(state.get("c0", 1))},
        "occupied_buckets": occupied,
        "precision_axes": precision,
        "incremental_changed_pages": len(changed_pages),
    })
    manifest_path = store.root / "manifests" / (generation_address + ".json")
    _atomic_json(manifest_path, manifest)
    _atomic_json(store.root / "HEAD.json", {
        "schema": SCHEMA, "manifest": generation_address})
    store.manifest = manifest

    # The exact values are now seated in the new immutable page head.  Release application
    # overlays so the same cells are not held twice or re-emitted by later page iteration.
    for tables in (sigma.w, sigma.cnt, sigma.rem):
        for table in tables:
            if isinstance(table, PagedTable):
                table.delta.clear()
                table.deleted.clear()
    return {"status": "returned-to-pages", "generation": generation_address,
            "parent": parent_address, "append_bytes": len(frame),
            "changed_pages": len(changed_pages)}


def build(source: str, *, root: str | None = None, page_bits: int = 12,
          verify_objects: bool = False) -> dict:
    """Derive one immutable page-map generation without materializing whole sigma."""
    source_path = Path(source)
    if not source_path.is_file():
        raise ValueError("sigma-page-source-not-present")
    page_root = Path(root or (str(source_path) + ".pages"))
    objects = page_root / "objects"
    manifests = page_root / "manifests"
    objects.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)

    mature = _mature_head(page_root, source_path, page_bits)
    if mature is not None and (not verify_objects or _objects_whole(page_root, mature)):
        return mature

    source_hash = hashlib.sha256()
    with source_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            source_hash.update(chunk)
    source_digest = source_hash.hexdigest()
    manifest_path = manifests / (source_digest + ".json")
    if manifest_path.is_file():
        manifest = json.loads(ark_io.receive_file(str(manifest_path)).decode("utf-8"))
        if (manifest.get("source_sha256") == source_digest
                and (not verify_objects or _objects_whole(page_root, manifest))):
            # A generation created before mature-head identity existed has just been witnessed
            # byte-for-byte by the hash above. Seat the missing stat identity atomically so this
            # is its last replay; subsequent unchanged lives receive HEAD directly.
            stat = source_path.stat()
            if (manifest.get("source_mtime_ns") != stat.st_mtime_ns
                    or manifest.get("source_bytes") != stat.st_size):
                manifest["source_bytes"] = stat.st_size
                manifest["source_mtime_ns"] = stat.st_mtime_ns
                _atomic_json(manifest_path, manifest)
            _atomic_json(page_root / "HEAD.json", {
                "schema": SCHEMA, "manifest": source_digest})
            return manifest

    # POSIX uses private system scratch; Windows keeps its existing den-local custody.
    # Durable pages, manifests and HEAD stay at the owned page root.
    temporary = Path(tempfile.mkdtemp(
        prefix="vigil-sigma-spool-", dir=str(page_root) if os.name == "nt" else None))
    registers = {"hist": 0, "bitreg": 0, "c0": 1}
    complete_cursor = 0
    try:
        spools = temporary / "spools"
        spools.mkdir()
        with source_path.open("rb") as stream:
            header, header_raw, header_end = _header(stream)
            complete_cursor = header_end
            feeder = BandSpoolFeeder(
                spools, int(os.environ.get("VIGIL_SIGMA_SPOOL_HANDLES",
                                           str(DEFAULT_SPOOL_HANDLES))))
            try:
                for cursor, state, entries in _frames(stream, header_end):
                    registers = {"hist": int(state.get("hist", 0)),
                                 "bitreg": int(state.get("bitreg", 0)),
                                 "c0": int(state.get("c0", 1))}
                    for offset in range(0, len(entries), 22):
                        ci, index, w, count, remainder = _entry(bytes(entries[offset:offset + 22]))
                        band = index >> page_bits
                        key = (ci, band)
                        feeder.feed(
                            key, index.to_bytes(4, "big")
                            + w.to_bytes(4, "big", signed=True)
                            + count.to_bytes(4, "big")
                            + remainder.to_bytes(8, "big", signed=True))
                    complete_cursor = cursor
            finally:
                feeder.close()

        pages = {}
        occupied = precision = 0
        for spool in sorted(spools.glob("*.bin")):
            context_text, band_text = spool.stem.split("-", 1)
            context, band = int(context_text), int(band_text, 16)
            cells = {}
            with spool.open("rb") as stream:
                while True:
                    raw = stream.read(ENTRY_BYTES)
                    if not raw:
                        break
                    if len(raw) != ENTRY_BYTES:
                        raise ValueError("sigma-page-spool-torn")
                    index = int.from_bytes(raw[:4], "big")
                    value = (int.from_bytes(raw[4:8], "big", signed=True),
                             int.from_bytes(raw[8:12], "big"),
                             int.from_bytes(raw[12:20], "big", signed=True))
                    if any(value):
                        cells[index] = value
                    else:
                        cells.pop(index, None)
            if not cells:
                continue
            raw = _page_bytes(context=context, band=band, page_bits=page_bits, cells=cells)
            address = _sha(raw)
            target = objects / (address + ".page")
            _seat_object(target, raw, address)
            pages["%d:%d" % (context, band)] = address
            occupied += sum(1 for _w, count, _rem in cells.values() if count)
            precision += sum(1 for _w, _count, rem in cells.values() if rem)

        source_stat = source_path.stat()
        source_bytes = source_stat.st_size
        torn_tail_bytes = source_bytes - complete_cursor
        torn_tail = None
        if torn_tail_bytes:
            with source_path.open("rb") as stream:
                stream.seek(complete_cursor)
                residual_raw = stream.read()
            if len(residual_raw) != torn_tail_bytes:
                raise ValueError("sigma-page-source-moved-during-build")
            torn_tail = _sha(residual_raw)
            residual_target = objects / (torn_tail + ".residual")
            if not residual_target.exists():
                ark_io.give_file(str(residual_target), residual_raw)

        manifest = {
            "schema": SCHEMA, "source": str(source_path),
            "source_sha256": source_digest, "source_bytes": source_bytes,
            "source_mtime_ns": source_stat.st_mtime_ns,
            "complete_cursor": complete_cursor,
            "torn_tail_bytes": torn_tail_bytes, "torn_tail": torn_tail,
            "header": header, "header_sha256": _sha(header_raw),
            "page_bits": int(page_bits), "pages": pages, "registers": registers,
            "occupied_buckets": occupied, "precision_axes": precision,
            "spool_bands": len(feeder.bands), "spool_peak_handles": feeder.peak_open,
            "spool_handle_limit": feeder.max_open,
        }
        _atomic_json(manifest_path, manifest)
        _atomic_json(page_root / "HEAD.json", {"schema": SCHEMA, "manifest": source_digest})
        return manifest
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


class PageStore:
    """Bounded page cache over one witnessed immutable manifest."""

    def __init__(self, source: str, *, root: str | None = None,
                 page_bits: int = 12, cache_pages: int = 32):
        self.source = str(source)
        self.root = Path(root or (self.source + ".pages"))
        self.manifest = build(self.source, root=str(self.root), page_bits=page_bits)
        self.page_bits = int(self.manifest["page_bits"])
        self.cache_pages = max(1, int(cache_pages))
        self.cache = OrderedDict()
        self.ordered_pages = set()
        self.loads = 0

    def _page(self, context: int, index: int) -> dict:
        band = int(index) >> self.page_bits
        key = (int(context), band)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        address = self.manifest["pages"].get("%d:%d" % key)
        cells = {}
        if address:
            raw = ark_io.receive_file(str(self.root / "objects" / (address + ".page")))
            try:
                head, cells = _read_page(raw, expected=address, ordered=self.ordered_pages)
            except ValueError as exc:
                if str(exc) != "sigma-page-object-digest-mismatch":
                    raise
                # The append-only source and its immutable manifest are canonical. Rebuild once,
                # retaining the interrupted object beside its address as a contrary witness.
                self.manifest = build(
                    self.source, root=str(self.root), page_bits=self.page_bits,
                    verify_objects=True)
                address = self.manifest["pages"].get("%d:%d" % key)
                if not address:
                    head, cells = {}, {}
                else:
                    raw = ark_io.receive_file(
                        str(self.root / "objects" / (address + ".page")))
                    head, cells = _read_page(raw, expected=address, ordered=self.ordered_pages)
            if (int(head.get("context", -1)), int(head.get("band", -1))) != key:
                raise ValueError("sigma-page-object-address-mismatch")
        self.cache[key] = cells
        self.loads += 1
        while len(self.cache) > self.cache_pages:
            self.cache.popitem(last=False)
        return cells

    def value(self, kind: str, context: int, index: int, default=0):
        value = self._page(context, index).get(int(index))
        if value is None:
            return default
        return value[{"w": 0, "cnt": 1, "rem": 2}[kind]]

    def table(self, kind: str, context: int):
        return PagedTable(self, kind, context)


class PagedTable(MutableMapping):
    """Mutable application overlay whose ground is restored a page at a time."""

    def __init__(self, store: PageStore, kind: str, context: int):
        if kind not in {"w", "cnt", "rem"}:
            raise ValueError("sigma-page-table-kind")
        self.store, self.kind, self.context = store, kind, int(context)
        self.delta = {}
        self.deleted = set()

    def _capture_projection_entry(self, key):
        key = int(key)
        return (key in self.delta, self.delta.get(key), key in self.deleted)

    def _restore_projection_entry(self, key, prior):
        key = int(key)
        present, value, deleted = prior
        if present:
            self.delta[key] = value
        else:
            self.delta.pop(key, None)
        if deleted:
            self.deleted.add(key)
        else:
            self.deleted.discard(key)

    def __getitem__(self, key):
        key = int(key)
        if key in self.delta:
            return self.delta[key]
        if key in self.deleted:
            raise KeyError(key)
        value = self.store.value(self.kind, self.context, key, None)
        if value is None or value == 0:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        key = int(key)
        self.deleted.discard(key)
        self.delta[key] = int(value)

    def __delitem__(self, key):
        key = int(key)
        if key not in self:
            raise KeyError(key)
        self.delta.pop(key, None)
        self.deleted.add(key)

    def __iter__(self):
        # Whole-table iteration is deliberately explicit and expensive. Normal prediction and
        # delta deposit never invoke it; it exists for equivalence witnesses and Mapping fidelity.
        seen = set()
        for page_key in sorted(self.store.manifest["pages"]):
            context_text, band_text = page_key.split(":", 1)
            if int(context_text) != self.context:
                continue
            band = int(band_text)
            cells = self.store._page(self.context, band << self.store.page_bits)
            component = {"w": 0, "cnt": 1, "rem": 2}[self.kind]
            for index, value in cells.items():
                if (value[component] and index not in self.deleted
                        and index not in seen and index not in self.delta):
                    seen.add(index)
                    yield index
        for index in self.delta:
            if index not in seen and index not in self.deleted:
                yield index

    def __len__(self):
        return sum(1 for _ in self)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        try:
            value = self[key]
        except KeyError:
            return default
        del self[key]
        return value


def revive(source: str, ground: str, *, root: str | None = None,
           page_bits: int = 12, cache_pages: int = 32):
    """Return the existing Predictor backed by lazy sovereign pages."""
    from .f_operator import new_sigma

    store = PageStore(source, root=root, page_bits=page_bits, cache_pages=cache_pages)
    header = store.manifest["header"]
    if str(header.get("ground")) != str(ground):
        return None
    bit_orders = tuple(header.get("bit_orders") or ())
    mask = int(header.get("mask", (1 << 18) - 1))
    predictor = new_sigma(bit_grain=bit_orders if bit_orders else False)
    if predictor.mask != mask or len(predictor.w) != int(header.get("n_ctx", -1)):
        tbits = (mask + 1).bit_length() - 1
        from f_codec import new_predictor
        predictor = new_predictor(maxorder=int(header.get("maxorder", 4)), tbits=tbits,
                                  use_match=False,
                                  use_bit_grain=bit_orders if bit_orders else False)
    predictor.w = [store.table("w", context) for context in range(predictor.n_ctx)]
    predictor.cnt = [store.table("cnt", context) for context in range(predictor.n_ctx)]
    predictor.rem = [store.table("rem", context) for context in range(predictor.n_ctx)]
    registers = store.manifest["registers"]
    predictor.hist = int(registers["hist"])
    predictor.bitreg = int(registers["bitreg"])
    predictor.c0 = int(registers["c0"])
    predictor.occupied_buckets = int(store.manifest["occupied_buckets"])
    predictor.precision_axes_count = int(store.manifest["precision_axes"])
    predictor.precision_opened = 0
    predictor.precision_witness = None
    predictor.dirty = set()
    predictor.page_store = store
    predictor.page_residual = {
        "source": store.manifest["source"],
        "complete_cursor": int(store.manifest["complete_cursor"]),
        "torn_tail_bytes": int(store.manifest["torn_tail_bytes"]),
        "torn_tail": store.manifest.get("torn_tail"),
    }
    return predictor
