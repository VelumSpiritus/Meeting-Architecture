#!/usr/bin/env python3
"""
Void Filler — the RNA probe loop.

Detect → Amplify → Capture → Retrain.

Generic structure, specific tooling. The loop itself never changes:
    1. DETECT  — probe finds voids (absence = signal)
    2. SEARCH  — generate queries from void coordinates
    3. CAPTURE — parse returns into four-column entries
    4. LOAD    — append to trace store
    5. RETRAIN — probe learns from expanded data, finds finer voids
    6. REPEAT  — descent ordered by confidence score

The specificity lives in two replaceable dictionaries:
    SECTOR_LEXICON  — maps keywords to sector coordinates
    QUERY_TEMPLATES — generates search strings from void coordinates

Swap those two, keep everything else, point at a different sky.
The structure IS the generalist. The words ARE the specialist.

Usage:
    # Run one pass of the loop
    python void_filler.py run

    # Run with custom lexicon
    python void_filler.py run --lexicon my_lexicon.json

    # Just detect (no search)
    python void_filler.py detect

    # Just search from existing voids
    python void_filler.py search --candidates closed_door_candidates_v2.json

    # Show what the next pass would search
    python void_filler.py plan
"""

import json, sys, os, time, hashlib
from pathlib import Path
from datetime import datetime

# ── paths ──
SCRATCHPAD = Path("F:/Codebook Analysis Engine/scratchpad")
TRACE_DIR = Path("F:/Codebook Analysis Engine/meeting_trace")
sys.path.insert(0, str(SCRATCHPAD))


# ═══════════════════════════════════════════════════════════════════
#  THE REPLACEABLE TOOLING — swap these to retool the descent
# ═══════════════════════════════════════════════════════════════════

SECTOR_LEXICON = {
    # sector_id: (name, keywords)
    # Keywords map text → sector coordinate for the probe.
    # The probe doesn't care what the words mean. It cares where they land.
    0:  ("Banking / Finance",
         ["banking", "finance", "bank", "federal reserve", "morgan",
          "wall street", "bailout", "currency", "gold", "tax",
          "debt", "loan", "treasury", "securities", "stock"]),
    2:  ("Government / Legislative",
         ["government", "congress", "senate", "legislative", "huac",
          "hearing", "declaration", "treaty", "executive order",
          "administration", "wpa", "new deal"]),
    4:  ("Military / Intelligence",
         ["military", "war", "intelligence", "fbi", "cia",
          "cointelpro", "infiltrat", "assassinat", "surveillance",
          "pentagon", "nsa", "dod", "paperclip", "nazi"]),
    6:  ("Media / Entertainment",
         ["media", "entertainment", "studio", "film", "television",
          "disney", "mockingbird", "cinderella", "broadcast",
          "radio", "newspaper", "press", "propaganda"]),
    8:  ("Technology / Infrastructure",
         ["technology", "wireless", "tesla", "patent", "monsanto",
          "seed", "terminator", "wardenclyffe", "ibm", "computer",
          "internet", "silicon", "software"]),
    -2: ("Energy / Resources",
         ["energy", "tower", "electric", "oil", "gas", "coal",
          "nuclear", "pipeline", "utility", "power grid"]),
    -4: ("Judiciary / Legal",
         ["judiciary", "legal", "court", "law", "citizens united",
          "santa clara", "ruling", "scotus", "antitrust",
          "verdict", "prosecution", "indictment"]),
    -6: ("Pharmaceutical / Medical",
         ["pharmaceutical", "medical", "syphilis", "tuskegee",
          "experiment", "penicillin", "theranos", "blood",
          "vaccine", "drug", "fda", "clinical"]),
    -8: ("Education / Academic",
         ["education", "academic", "university", "school",
          "curriculum", "foundation", "scholarship", "college",
          "peabody", "rockefeller education"]),
    -9: ("Religion / Ideology",
         ["religion", "scientology", "church", "nation of islam",
          "hubbard", "malcolm", "temple", "faith", "sect"]),
}


def _sector_name(sector_id):
    if sector_id in SECTOR_LEXICON:
        return SECTOR_LEXICON[sector_id][0]
    best = min(SECTOR_LEXICON.keys(), key=lambda k: abs(k - sector_id))
    return SECTOR_LEXICON[best][0]


def _classify_text(text):
    text = text.lower()
    for sid, (name, keywords) in SECTOR_LEXICON.items():
        for kw in keywords:
            if kw in text:
                return sid
    return 0


QUERY_TEMPLATES = [
    # Each template: (name, format_string)
    # {year}, {year_range}, {sector_name} from void coordinates.
    # {keywords} from the lexicon — the actual words that generate.
    # Replace THESE to search a different sky. The loop doesn't care.
    ("who_met",
     '({keywords}) secret meeting OR closed door OR private {year_range}'),
    ("what_changed",
     '({keywords}) established OR founded OR passed OR signed {year_range}'),
    ("who_benefited",
     '({keywords}) profit OR benefit OR acquired OR control {year_range}'),
    ("backward_from_effect",
     '({keywords}) before OR prior OR led to {year_range}'),
    ("family_connection",
     '({keywords}) married OR daughter OR son OR heir {year_range}'),
    ("board_overlap",
     '({keywords}) board director chairman trustee {year_range}'),
]


# ═══════════════════════════════════════════════════════════════════
#  THE LOOP — this never changes
# ═══════════════════════════════════════════════════════════════════

class VoidFiller:
    """
    The RNA probe loop. Generic descent structure.

    detect()  → finds voids (calls the probe)
    plan()    → generates search queries from voids, ordered by score
    search()  → executes queries (needs a search function injected)
    capture() → parses search results into four-column trace entries
    load()    → appends entries to the trace store
    retrain() → retrains the probe on expanded data

    The loop: detect → plan → search → capture → load → retrain → detect
    Descent ordered by confidence score. Highest-scoring voids first.
    """

    def __init__(self, lexicon=None, templates=None,
                 trace_path=None, candidates_path=None):
        self.lexicon = lexicon or SECTOR_LEXICON
        self.templates = templates or QUERY_TEMPLATES
        self.trace_path = trace_path or TRACE_DIR / "trace.json"
        self.candidates_path = candidates_path
        self.search_fn = None  # injected by caller
        self.parse_fn = None   # injected by caller
        self._log = []

    def _log_step(self, step, detail):
        entry = {
            "time": datetime.now().isoformat(),
            "step": step,
            "detail": detail
        }
        self._log.append(entry)
        print(f"  [{step}] {detail}")

    # ── 1. DETECT ──
    def detect(self, grid=(90, 45), epochs=1500, target_n=20):
        """Run the probe. Returns list of void candidates sorted by score."""
        import numpy as np
        from closed_door_probe import (
            ProbeMatrix, activity_density_map, build_training_data,
            find_closed_doors, date_to_num, sector_label
        )

        # Load trace
        with open(self.trace_path) as f:
            data = json.load(f)

        # Build sector map from lexicon
        sector_map = {}
        for sid, (name, keywords) in self.lexicon.items():
            for kw in keywords:
                sector_map[kw] = sid

        # Convert trace to probe format
        records = []
        for mid, m in data.get('meetings', {}).items():
            try: year = int(m.get('date', '')[:4])
            except: continue
            text = ' '.join([
                m.get('stated_purpose', ''), m.get('location', ''),
                m.get('delta', ''), ' '.join(m.get('names', []))
            ]).lower()
            sector = 0
            for kw, val in sector_map.items():
                if kw in text:
                    sector = val
                    break
            records.append({
                'date_num': date_to_num(year),
                'sector_num': sector + np.random.normal(0, 0.3),
                'weight': 1.5
            })
        for eid, e in data.get('events', {}).items():
            try: year = int(e.get('date', '')[:4])
            except: continue
            text = ' '.join([
                e.get('event', ''), e.get('delta', ''),
                e.get('before', ''), e.get('after', '')
            ]).lower()
            sector = 0
            for kw, val in sector_map.items():
                if kw in text:
                    sector = val
                    break
            records.append({
                'date_num': date_to_num(year),
                'sector_num': sector + np.random.normal(0, 0.3),
                'weight': 1
            })

        self._log_step("DETECT", f"{len(records)} data points from trace")

        events = [(r['date_num'], r['sector_num'], r.get('weight', 1), '')
                  for r in records]
        observed, t_edges, s_edges = activity_density_map(
            events, t_bins=grid[0], s_bins=grid[1], s_range=10)

        X, y, tc, sc = build_training_data(observed, t_edges, s_edges)

        model = ProbeMatrix(seed=42)
        for ep in range(1, epochs + 1):
            loss = model.backward(X, y, lr=0.001)
            if ep % (epochs // 5) == 0:
                self._log_step("DETECT", f"epoch {ep}/{epochs}  MSE={loss:.6f}")

        predicted = model.forward(X)
        candidates = find_closed_doors(predicted, observed, tc, sc,
                                       target_n=target_n)

        self._log_step("DETECT", f"{len(candidates)} voids found")

        # Save candidates
        out_path = self.candidates_path or (
            SCRATCHPAD / "void_filler_candidates.json")
        with open(out_path, "w") as f:
            json.dump(candidates, f, indent=2)

        return candidates

    # ── 2. PLAN ──
    def plan(self, candidates=None):
        """
        Generate search queries from void coordinates.
        Ordered by score — highest confidence voids first.
        Returns list of (candidate, queries) tuples.
        """
        if candidates is None:
            cp = self.candidates_path or (
                SCRATCHPAD / "void_filler_candidates.json")
            with open(cp) as f:
                candidates = json.load(f)

        # Sort by score descending — the descent order
        candidates = sorted(candidates,
                           key=lambda c: c.get('reward', 0),
                           reverse=True)

        plans = []
        for c in candidates:
            year = c['year']
            sector = c.get('sector', 0)
            sector_name = c.get('sector_name', _sector_name(sector))
            score = c.get('reward', 0)

            # Year range: ±5 years around the void
            y_lo = int(year - 5)
            y_hi = int(year + 5)
            year_range = f"{y_lo}..{y_hi}"

            # Pull keywords from the lexicon — match by name first, then by coordinate
            matched_sid = None
            for sid, (name, kws) in self.lexicon.items():
                if name == sector_name or sector_name.startswith(name.split('/')[0].strip()):
                    matched_sid = sid
                    break
            if matched_sid is None:
                matched_sid = min(self.lexicon.keys(),
                                  key=lambda k: abs(k - sector))
            keywords = self.lexicon[matched_sid][1]
            specific_kw = [k for k in keywords
                          if len(k) > 3 and ' ' not in k][:3]
            kw_string = ' OR '.join(specific_kw) if specific_kw else sector_name

            queries = []
            for tname, template in self.templates:
                q = template.format(
                    year=int(year),
                    year_range=year_range,
                    sector=sector,
                    sector_name=sector_name,
                    keywords=kw_string
                )
                queries.append({
                    "query": q,
                    "template": tname,
                    "void_year": year,
                    "void_sector": sector_name,
                    "void_score": score,
                    "query_id": hashlib.sha256(
                        q.encode()).hexdigest()[:12]
                })

            plans.append((c, queries))

        total_queries = sum(len(qs) for _, qs in plans)
        self._log_step("PLAN",
                       f"{len(plans)} voids → {total_queries} queries")
        return plans

    # ── 3. SEARCH ──
    def search(self, plans, search_fn=None, max_queries=None):
        """
        Execute search queries. Needs a search function:
            search_fn(query_string) → list of result dicts

        Each result dict should have at minimum:
            {"title": str, "snippet": str, "url": str}

        Returns list of (candidate, query, results) tuples.
        """
        fn = search_fn or self.search_fn
        if fn is None:
            self._log_step("SEARCH",
                           "NO SEARCH FUNCTION — returning plan only")
            return [(c, q, []) for c, qs in plans for q in qs]

        results = []
        n = 0
        for candidate, queries in plans:
            for q in queries:
                if max_queries and n >= max_queries:
                    break
                try:
                    hits = fn(q['query'])
                    results.append((candidate, q, hits))
                    self._log_step("SEARCH",
                                   f"[{q['template']}] {len(hits)} hits "
                                   f"for {q['void_year']:.0f} "
                                   f"{q['void_sector']}")
                except Exception as e:
                    self._log_step("SEARCH", f"ERROR: {e}")
                    results.append((candidate, q, []))
                n += 1

        self._log_step("SEARCH", f"{n} queries executed")
        return results

    # ── 4. CAPTURE ──
    def capture(self, search_results, parse_fn=None):
        """
        Parse search results into four-column trace entries.

        Needs a parse function:
            parse_fn(title, snippet, url, void_context)
                → dict with keys: event, date, before, after, delta, source
                   OR None to skip

        If no parse_fn, returns raw results for manual capture.
        """
        fn = parse_fn or self.parse_fn
        entries = []

        for candidate, query, hits in search_results:
            void_ctx = {
                "year": candidate.get('year'),
                "sector": candidate.get('sector_name'),
                "score": candidate.get('reward'),
                "template": query.get('template'),
            }

            for hit in hits:
                if fn:
                    try:
                        entry = fn(
                            hit.get('title', ''),
                            hit.get('snippet', ''),
                            hit.get('url', ''),
                            void_ctx
                        )
                        if entry:
                            entry['_void_year'] = void_ctx['year']
                            entry['_void_sector'] = void_ctx['sector']
                            entry['_void_score'] = void_ctx['score']
                            entry['_query_template'] = void_ctx['template']
                            entries.append(entry)
                    except Exception as e:
                        self._log_step("CAPTURE", f"parse error: {e}")
                else:
                    entries.append({
                        "raw_title": hit.get('title', ''),
                        "raw_snippet": hit.get('snippet', ''),
                        "raw_url": hit.get('url', ''),
                        "_void_year": void_ctx['year'],
                        "_void_sector": void_ctx['sector'],
                        "_void_score": void_ctx['score'],
                        "_needs_manual_capture": True
                    })

        self._log_step("CAPTURE",
                       f"{len(entries)} entries "
                       f"({'parsed' if fn else 'raw, needs manual'})")
        return entries

    # ── 5. LOAD ──
    def load(self, entries):
        """Append captured entries to the trace store."""
        from meeting_tracer import MeetingTrace
        trace = MeetingTrace(self.trace_path)

        loaded = 0
        for e in entries:
            if e.get('_needs_manual_capture'):
                continue
            if e.get('event'):
                trace.add_event(
                    e['event'],
                    e.get('date', ''),
                    before=e.get('before', ''),
                    after=e.get('after', ''),
                    delta=e.get('delta', ''),
                    source=e.get('source', '')
                )
                loaded += 1

        if loaded > 0:
            trace.save()

        summary = trace.network_summary()
        self._log_step("LOAD",
                       f"{loaded} entries → trace "
                       f"({summary['names_tracked']} names, "
                       f"{summary['events_mapped']} events)")
        return summary

    # ── 6. RETRAIN (loops back to DETECT) ──
    def retrain(self, **detect_kwargs):
        """Retrain = detect again on expanded data. The loop."""
        self._log_step("RETRAIN", "retraining on expanded trace...")
        return self.detect(**detect_kwargs)

    # ── THE FULL LOOP ──
    def run(self, search_fn=None, parse_fn=None,
            passes=1, max_queries_per_pass=None, **detect_kwargs):
        """
        Run the full loop N passes.

        Each pass: detect → plan → search → capture → load → retrain
        Descent ordered by confidence. Each pass sharpens the voids.
        """
        self.search_fn = search_fn or self.search_fn
        self.parse_fn = parse_fn or self.parse_fn

        for p in range(passes):
            print(f"\n{'='*72}")
            print(f"  VOID FILLER — PASS {p+1}/{passes}")
            print(f"{'='*72}")

            candidates = self.detect(**detect_kwargs)
            plans = self.plan(candidates)
            results = self.search(plans,
                                  max_queries=max_queries_per_pass)
            entries = self.capture(results)

            if any(not e.get('_needs_manual_capture') for e in entries):
                self.load([e for e in entries
                          if not e.get('_needs_manual_capture')])

            print(f"\n  Pass {p+1} complete: "
                  f"{len(candidates)} voids, "
                  f"{sum(len(qs) for _, qs in plans)} queries, "
                  f"{len(entries)} captures")

        return {
            "passes": passes,
            "final_candidates": candidates,
            "total_entries": len(entries),
            "log": self._log
        }

    # ── EXPORT ──
    def export_plan(self, candidates=None):
        """Export the search plan as a readable manifest."""
        plans = self.plan(candidates)
        lines = []
        for c, queries in plans:
            lines.append(
                f"\n── VOID: {c['year']:.1f} × {c.get('sector_name', '?')} "
                f"(score {c.get('reward', 0):.3f}) ──")
            for q in queries:
                lines.append(f"  [{q['template']}] {q['query']}")
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════
#  LEXICON I/O — save/load the replaceable tooling
# ═══════════════════════════════════════════════════════════════════

def save_lexicon(lexicon, path):
    """Save a sector lexicon to JSON for reuse / retooling."""
    out = {}
    for sid, (name, keywords) in lexicon.items():
        out[str(sid)] = {"name": name, "keywords": keywords}
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


def load_lexicon(path):
    """Load a sector lexicon from JSON."""
    with open(path) as f:
        raw = json.load(f)
    lexicon = {}
    for sid_str, val in raw.items():
        lexicon[int(sid_str)] = (val["name"], val["keywords"])
    return lexicon


def save_templates(templates, path):
    """Save query templates to JSON for reuse / retooling."""
    with open(path, "w") as f:
        json.dump(templates, f, indent=2)


def load_templates(path):
    """Load query templates from JSON."""
    with open(path) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8',
                           errors='replace')

    args = sys.argv[1:]
    cmd = args[0] if args else "plan"

    filler = VoidFiller()

    # Load custom lexicon if provided
    for i, a in enumerate(args):
        if a == '--lexicon' and i + 1 < len(args):
            filler.lexicon = load_lexicon(args[i + 1])
        if a == '--candidates' and i + 1 < len(args):
            filler.candidates_path = Path(args[i + 1])

    if cmd == "detect":
        print("═" * 72)
        print("  VOID FILLER — DETECT")
        print("═" * 72)
        candidates = filler.detect()
        print(f"\n  {len(candidates)} voids found")
        for i, c in enumerate(candidates, 1):
            print(f"  {i:2d}. {c['year']:.1f} × "
                  f"{c.get('sector_name', '?'):30s} "
                  f"score={c.get('reward', 0):.4f}")

    elif cmd == "plan":
        print("═" * 72)
        print("  VOID FILLER — PLAN (what would be searched)")
        print("═" * 72)
        plan_text = filler.export_plan()
        print(plan_text)

    elif cmd == "search":
        print("═" * 72)
        print("  VOID FILLER — SEARCH (needs search_fn injection)")
        print("  Run from Python with filler.search_fn = your_fn")
        print("═" * 72)
        plans = filler.plan()
        print(f"  {sum(len(qs) for _, qs in plans)} queries ready")
        print("  Inject a search function to execute them.")

    elif cmd == "run":
        print("═" * 72)
        print("  VOID FILLER — FULL LOOP")
        print("═" * 72)
        result = filler.run()
        print(f"\n  Done: {result['passes']} passes, "
              f"{result['total_entries']} captures")

    elif cmd == "export-lexicon":
        out = SCRATCHPAD / "void_filler_lexicon.json"
        save_lexicon(SECTOR_LEXICON, out)
        print(f"Lexicon saved to {out}")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: detect, plan, search, run, export-lexicon")
