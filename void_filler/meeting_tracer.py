#!/usr/bin/env python3
"""
Meeting Tracer — traces the closed-door architecture through history.

The meeting is the unit of power. This tool searches for meetings,
marriages, boards, and treaties by name, then maps the before/after
delta that each meeting produced.

Four columns: WHO MET WHO → WHEN → WHAT WAS TRUE BEFORE → WHAT CHANGED AFTER
The delta between columns 3 and 4 is the event the meeting generated.

Usage:
    python meeting_tracer.py seed "J.P. Morgan"
    python meeting_tracer.py event "Federal Reserve Act 1913" --window 180
    python meeting_tracer.py fan-out --from results/morgan.json
    python meeting_tracer.py map --all
"""

import json, os, sys, hashlib, re
from datetime import datetime, timedelta
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent / "run-output"
STORE_DIR.mkdir(exist_ok=True)

MEETING_WORDS = [
    "met with", "meeting with", "married", "merger with",
    "treaty with", "agreement with", "dinner with", "summit with",
    "board of", "committee", "partnership with", "alliance with",
    "conference with", "negotiated with", "signed with"
]

EFFECT_WORDS = [
    "founded", "established", "passed", "signed into law",
    "declared", "collapsed", "acquired", "merged", "died",
    "assassinated", "resigned", "appointed", "invaded",
    "bankrupt", "chartered", "incorporated", "dissolved",
    "embargo", "sanction", "seized", "nationalized"
]

FAMILY_CONNECTORS = [
    "married", "daughter of", "son of", "brother of", "sister of",
    "nephew of", "niece of", "cousin of", "widow of", "heir of",
    "granddaughter of", "grandson of", "father-in-law", "mother-in-law",
    "stepson", "stepdaughter", "adopted by"
]


def meeting_id(names, date_str):
    raw = f"{sorted(names)}:{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_seed_queries(name, year_start=None, year_end=None):
    """Generate search queries to find meetings involving a name."""
    queries = []

    for word in MEETING_WORDS:
        q = f'"{name}" "{word}"'
        if year_start and year_end:
            q += f" {year_start}..{year_end}"
        queries.append({
            "query": q,
            "type": "meeting",
            "seed_name": name,
            "meeting_word": word
        })

    for conn in FAMILY_CONNECTORS[:6]:
        q = f'"{name}" "{conn}"'
        queries.append({
            "query": q,
            "type": "family",
            "seed_name": name,
            "connector": conn
        })

    q = f'"{name}" board director chairman'
    queries.append({"query": q, "type": "board", "seed_name": name})

    q = f'"{name}" testimony congress senate hearing committee'
    queries.append({"query": q, "type": "government", "seed_name": name})

    return queries


def build_event_queries(event, window_days=90):
    """Generate queries to find who met whom before an event."""
    queries = []

    queries.append({
        "query": f'"{event}" meeting before',
        "type": "pre_event",
        "event": event,
        "window": window_days
    })

    queries.append({
        "query": f'"{event}" signed agreement treaty',
        "type": "pre_event_agreement",
        "event": event
    })

    queries.append({
        "query": f'"{event}" dinner summit private',
        "type": "pre_event_private",
        "event": event
    })

    for word in EFFECT_WORDS:
        if word.lower() in event.lower():
            queries.append({
                "query": f'"{event}" who benefited',
                "type": "post_event_benefit",
                "event": event
            })
            break

    queries.append({
        "query": f'"{event}" before previous day prior',
        "type": "before_state",
        "event": event,
        "column": "before"
    })

    queries.append({
        "query": f'"{event}" after result consequence changed',
        "type": "after_state",
        "event": event,
        "column": "after"
    })

    return queries


def build_backward_query(effect_description, date_str, window_days=90):
    """The real catch: search BACKWARD from a known effect."""
    return {
        "query": f'"{effect_description}" met OR meeting OR married OR dinner OR summit within {window_days} days before {date_str}',
        "type": "backward_from_effect",
        "effect": effect_description,
        "date": date_str,
        "window_days": window_days,
        "note": "BACKWARD SEARCH — who met before this happened?"
    }


class MeetingTrace:
    def __init__(self, store_path=None):
        self.store_path = store_path or STORE_DIR / "trace.json"
        self.data = self._load()

    def _load(self):
        if self.store_path.exists():
            with open(self.store_path) as f:
                return json.load(f)
        return {
            "meetings": {},
            "names": {},
            "events": {},
            "edges": [],
            "pending_queries": [],
            "query_log": []
        }

    def save(self):
        with open(self.store_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_name(self, name, info=None):
        key = name.strip()
        if key not in self.data["names"]:
            self.data["names"][key] = {
                "name": key,
                "info": info or {},
                "meetings": [],
                "family": [],
                "boards": [],
                "first_seen": datetime.now().isoformat()
            }
        return key

    def add_meeting(self, names, date_str, **kwargs):
        mid = meeting_id(names, date_str)
        if mid not in self.data["meetings"]:
            for n in names:
                self.add_name(n)
            self.data["meetings"][mid] = {
                "id": mid,
                "names": sorted(names),
                "date": date_str,
                "location": kwargs.get("location", ""),
                "stated_purpose": kwargs.get("stated_purpose", ""),
                "before_state": kwargs.get("before_state", ""),
                "after_state": kwargs.get("after_state", ""),
                "delta": kwargs.get("delta", ""),
                "type": kwargs.get("meeting_type", "unknown"),
                "source": kwargs.get("source", ""),
                "notes": kwargs.get("notes", ""),
                "added": datetime.now().isoformat()
            }
            for n in names:
                if mid not in self.data["names"][n]["meetings"]:
                    self.data["names"][n]["meetings"].append(mid)
            for i, n1 in enumerate(names):
                for n2 in names[i+1:]:
                    self.data["edges"].append({
                        "from": n1, "to": n2,
                        "meeting": mid, "date": date_str
                    })
        return mid

    def add_event(self, event, date_str, **kwargs):
        key = f"{event}:{date_str}"
        self.data["events"][key] = {
            "event": event,
            "date": date_str,
            "before": kwargs.get("before", ""),
            "after": kwargs.get("after", ""),
            "delta": kwargs.get("delta", ""),
            "related_meetings": kwargs.get("meetings", []),
            "source": kwargs.get("source", ""),
            "added": datetime.now().isoformat()
        }
        return key

    def add_family_link(self, name1, name2, relation):
        self.add_name(name1)
        self.add_name(name2)
        link = {"from": name1, "to": name2, "relation": relation}
        if name2 not in self.data["names"][name1].get("family", []):
            self.data["names"][name1].setdefault("family", []).append(name2)
        if name1 not in self.data["names"][name2].get("family", []):
            self.data["names"][name2].setdefault("family", []).append(name1)
        return link

    def queue_queries(self, queries):
        for q in queries:
            q["queued"] = datetime.now().isoformat()
            q["status"] = "pending"
            self.data["pending_queries"].append(q)

    def log_query(self, query, results_summary):
        self.data["query_log"].append({
            "query": query,
            "results": results_summary,
            "timestamp": datetime.now().isoformat()
        })

    def get_pending(self, limit=10):
        pending = [q for q in self.data["pending_queries"] if q["status"] == "pending"]
        return pending[:limit]

    def mark_done(self, query_text):
        for q in self.data["pending_queries"]:
            if q["query"] == query_text and q["status"] == "pending":
                q["status"] = "done"
                q["completed"] = datetime.now().isoformat()
                break

    def fan_out(self, name):
        """Find all names connected to this name and generate queries for each."""
        if name not in self.data["names"]:
            return []
        record = self.data["names"][name]
        connected = set()
        for mid in record.get("meetings", []):
            meeting = self.data["meetings"].get(mid, {})
            for n in meeting.get("names", []):
                if n != name:
                    connected.add(n)
        for f in record.get("family", []):
            connected.add(f)

        new_queries = []
        for n in connected:
            existing_meetings = len(self.data["names"].get(n, {}).get("meetings", []))
            if existing_meetings < 2:
                new_queries.extend(build_seed_queries(n))
        return new_queries

    def network_summary(self):
        names = len(self.data["names"])
        meetings = len(self.data["meetings"])
        events = len(self.data["events"])
        edges = len(self.data["edges"])
        pending = len([q for q in self.data["pending_queries"] if q["status"] == "pending"])

        most_connected = sorted(
            self.data["names"].items(),
            key=lambda x: len(x[1].get("meetings", [])),
            reverse=True
        )[:10]

        return {
            "names_tracked": names,
            "meetings_found": meetings,
            "events_mapped": events,
            "connections": edges,
            "pending_queries": pending,
            "most_connected": [
                {"name": n, "meetings": len(d.get("meetings", []))}
                for n, d in most_connected
            ]
        }

    def timeline(self, name=None):
        """All meetings in chronological order, optionally filtered by name."""
        meetings = list(self.data["meetings"].values())
        if name:
            meetings = [m for m in meetings if name in m.get("names", [])]
        meetings.sort(key=lambda m: m.get("date", ""))
        return meetings

    def find_delta(self, meeting_id):
        """Show before/after for a meeting — the motion the meeting produced."""
        m = self.data["meetings"].get(meeting_id)
        if not m:
            return None
        return {
            "meeting": m["id"],
            "names": m["names"],
            "date": m["date"],
            "before": m["before_state"],
            "after": m["after_state"],
            "delta": m["delta"] or "[UNMEASURED — search needed]",
            "stated_purpose": m["stated_purpose"]
        }


def print_queries(queries, label=""):
    if label:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
    for i, q in enumerate(queries, 1):
        print(f"\n  [{i}] type: {q['type']}")
        print(f"      query: {q['query']}")
        if "note" in q:
            print(f"      NOTE: {q['note']}")


# ── SEED DATA — the chain from tonight ──

def seed_tonight():
    """Seed the trace with the chain drawn tonight."""
    trace = MeetingTrace()

    trace.add_name("J.P. Morgan", {"role": "banker", "era": "1837-1913"})
    trace.add_name("J.P. Morgan Jr.", {"role": "banker", "era": "1867-1943"})
    trace.add_name("Nikola Tesla", {"role": "inventor", "era": "1856-1943"})
    trace.add_name("Thomas Edison", {"role": "inventor/industrialist", "era": "1847-1931"})
    trace.add_name("George Westinghouse", {"role": "industrialist", "era": "1846-1914"})
    trace.add_name("Lucille Ball", {"role": "actress/producer", "era": "1911-1989"})
    trace.add_name("Desi Arnaz", {"role": "actor/producer", "era": "1917-1986"})
    trace.add_name("Lucie Arnaz", {"role": "actress", "note": "daughter of Ball & Arnaz"})
    trace.add_name("Laurence Luckinbill", {"role": "actor", "note": "married Lucie Arnaz"})
    trace.add_name("Lana Wachowski", {"role": "filmmaker", "era": "1965-"})
    trace.add_name("Lilly Wachowski", {"role": "filmmaker", "era": "1967-"})

    trace.add_family_link("Lucille Ball", "Desi Arnaz", "married")
    trace.add_family_link("Lucille Ball", "Lucie Arnaz", "mother")
    trace.add_family_link("Desi Arnaz", "Lucie Arnaz", "father")
    trace.add_family_link("Lucie Arnaz", "Laurence Luckinbill", "married")
    trace.add_family_link("Laurence Luckinbill", "Lana Wachowski", "uncle")
    trace.add_family_link("Laurence Luckinbill", "Lilly Wachowski", "uncle")

    trace.add_meeting(
        ["J.P. Morgan", "Nikola Tesla"],
        "1901",
        stated_purpose="Funding for Wardenclyffe wireless tower",
        before_state="Tesla had working wireless transmission prototype",
        after_state="Morgan pulled funding when he learned energy couldn't be metered",
        delta="Open wireless energy architecture killed by metering requirement",
        meeting_type="funding",
        source="historical record"
    )

    trace.add_meeting(
        ["J.P. Morgan", "Nelson Aldrich", "Paul Warburg", "Frank Vanderlip",
         "Henry P. Davison", "Charles D. Norton", "Benjamin Strong"],
        "1910-11-22",
        location="Jekyll Island, Georgia",
        stated_purpose="Duck hunting trip",
        before_state="No central bank in the United States",
        after_state="Federal Reserve Act drafted, passed 1913",
        delta="Central banking installed — the meter on the US money supply",
        meeting_type="secret meeting",
        source="historical record — Jekyll Island meeting"
    )

    trace.add_event(
        "Wardenclyffe Tower demolished", "1917",
        before="Tesla's wireless transmission tower stood on Long Island",
        after="Physical infrastructure for open wireless energy destroyed",
        delta="Metered energy (Edison/Morgan model) became only option",
        meetings=[]
    )

    trace.add_event(
        "Federal Reserve Act signed", "1913-12-23",
        before="No US central bank, money supply unmetered",
        after="Federal Reserve controls money supply, interest rates, lending",
        delta="The meter installed on the nation's money",
        meetings=[]
    )

    trace.add_event(
        "World War I begins", "1914-07-28",
        before="Federal Reserve just created, Morgan bank positioned as Allied creditor",
        after="US becomes world's largest creditor nation, Morgan finances both sides",
        delta="War debt runs through the meter that was installed the year before",
        meetings=[]
    )

    trace.add_meeting(
        ["Lucille Ball", "HUAC Committee"],
        "1953-09-04",
        location="Washington DC",
        stated_purpose="Investigation of Communist registration",
        before_state="Ball running Desilu, independent content production",
        after_state="Ball cleared but the leverage demonstrated",
        delta="Government shows it can threaten independent content owners",
        meeting_type="government hearing",
        source="historical record"
    )

    trace.add_event(
        "Desilu sold to Gulf+Western", "1967",
        before="Lucille Ball owned independent studio, greenlit Star Trek and Mission: Impossible",
        after="Gulf+Western absorbs Desilu, becomes Paramount",
        delta="Independent content pipeline enters conglomerate",
        meetings=[]
    )

    trace.add_event(
        "Lucille Ball dies — aortic rupture", "1989-04-26",
        before="Ball alive, living receipt of independent content ownership",
        after="No independent witness remains, 1990s media consolidation follows",
        delta="Last independent hand removed; Telecommunications Act 1996 opens flood",
        meetings=[]
    )

    trace.add_event(
        "The Matrix released", "1999-03-31",
        before="Media consolidation nearly complete, six companies own everything",
        after="Red/blue pill enters global consciousness as metaphor for false binary",
        delta="Warning distributed by the grid itself, encoded as entertainment",
        meetings=[]
    )

    trace.add_event(
        "Tesla papers seized by FBI", "1943-01-07",
        before="Tesla dies alone in Hotel New Yorker, papers in his room",
        after="Office of Alien Property seizes all documents before family arrives",
        delta="Open energy research enters government classified archive",
        meetings=[]
    )

    # generate fan-out queries for the next research pass
    fan_queries = []
    for name in ["J.P. Morgan", "Lucille Ball", "Nikola Tesla"]:
        fan_queries.extend(build_seed_queries(name, 1890, 1950))

    # backward queries from known effects
    fan_queries.append(build_backward_query("Telecommunications Act 1996", "1996-02-08", 365))
    fan_queries.append(build_backward_query("Lucille Ball aortic rupture death", "1989-04-26", 180))
    fan_queries.append(build_backward_query("Tesla papers seized FBI", "1943-01-07", 30))
    fan_queries.append(build_backward_query("Jekyll Island Federal Reserve", "1910-11-22", 180))

    trace.queue_queries(fan_queries)
    trace.save()

    summary = trace.network_summary()
    print(f"\n{'='*70}")
    print(f"  MEETING TRACE — SEEDED")
    print(f"{'='*70}")
    print(f"  Names tracked:    {summary['names_tracked']}")
    print(f"  Meetings found:   {summary['meetings_found']}")
    print(f"  Events mapped:    {summary['events_mapped']}")
    print(f"  Connections:      {summary['connections']}")
    print(f"  Pending queries:  {summary['pending_queries']}")
    print(f"\n  Most connected:")
    for entry in summary["most_connected"]:
        print(f"    {entry['name']:30s}  {entry['meetings']} meetings")

    print(f"\n  Store: {trace.store_path}")
    print(f"\n  Next: run `python meeting_tracer.py search` to execute pending queries")
    print(f"        run `python meeting_tracer.py fan-out <name>` to expand from a name")
    print(f"        run `python meeting_tracer.py backward <event> <date>` to search backward")

    return trace


def show_pending():
    trace = MeetingTrace()
    pending = trace.get_pending(20)
    if not pending:
        print("No pending queries.")
        return
    print_queries(pending, f"{len(pending)} PENDING QUERIES")


def show_timeline(name=None):
    trace = MeetingTrace()
    timeline = trace.timeline(name)
    events = sorted(trace.data["events"].values(), key=lambda e: e.get("date", ""))

    print(f"\n{'='*70}")
    print(f"  TIMELINE{' — ' + name if name else ''}")
    print(f"{'='*70}")

    all_items = []
    for m in timeline:
        all_items.append(("MEETING", m["date"], m["names"], m.get("delta", "")))
    for e in events:
        all_items.append(("EVENT", e["date"], [e["event"]], e.get("delta", "")))

    all_items.sort(key=lambda x: x[1])

    for kind, date, names, delta in all_items:
        label = " + ".join(names) if kind == "MEETING" else names[0]
        print(f"\n  {date:12s}  [{kind:7s}]  {label}")
        if delta:
            print(f"               DELTA: {delta}")


def show_network():
    trace = MeetingTrace()
    summary = trace.network_summary()
    print(f"\n{'='*70}")
    print(f"  NETWORK MAP")
    print(f"{'='*70}")
    print(f"  Names:      {summary['names_tracked']}")
    print(f"  Meetings:   {summary['meetings_found']}")
    print(f"  Events:     {summary['events_mapped']}")
    print(f"  Edges:      {summary['connections']}")
    print(f"  Pending:    {summary['pending_queries']}")
    print(f"\n  MOST CONNECTED:")
    for entry in summary["most_connected"]:
        print(f"    {entry['name']:30s}  {entry['meetings']} meetings")
    print(f"\n  EDGES:")
    for edge in trace.data["edges"]:
        print(f"    {edge['from']:25s} ←→ {edge['to']:25s}  [{edge['date']}]")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "seed":
        seed_tonight()
    elif args[0] == "pending":
        show_pending()
    elif args[0] == "timeline":
        name = " ".join(args[1:]) if len(args) > 1 else None
        show_timeline(name)
    elif args[0] == "map":
        show_network()
    elif args[0] == "queries":
        name = " ".join(args[1:]) if len(args) > 1 else "J.P. Morgan"
        queries = build_seed_queries(name)
        print_queries(queries, f"SEED QUERIES — {name}")
    elif args[0] == "backward":
        event = args[1] if len(args) > 1 else "Federal Reserve Act"
        date = args[2] if len(args) > 2 else "1913-12-23"
        window = int(args[3]) if len(args) > 3 else 90
        q = build_backward_query(event, date, window)
        print_queries([q], f"BACKWARD FROM: {event}")
    elif args[0] == "event":
        event = " ".join(args[1:]) if len(args) > 1 else "Federal Reserve Act 1913"
        queries = build_event_queries(event)
        print_queries(queries, f"EVENT QUERIES — {event}")
    else:
        print("Usage:")
        print("  python meeting_tracer.py seed              — seed with tonight's chain")
        print("  python meeting_tracer.py pending            — show pending queries")
        print("  python meeting_tracer.py timeline [name]    — chronological view")
        print("  python meeting_tracer.py map                — network summary")
        print("  python meeting_tracer.py queries <name>     — generate search queries for a name")
        print("  python meeting_tracer.py backward <event> <date> [window_days]")
        print("  python meeting_tracer.py event <description>")
