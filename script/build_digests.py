#!/usr/bin/env python3
"""Produce scheduled news digests from Google News RSS.

Reads digests.json, decides which digests are due (based on each digest's
times / days / timezone and data/state.json), fetches matching news and writes:

  data/<id>/latest.json          newest digest
  data/<id>/<YYYY-MM-DD_HHMM>.json archived copies (last 60 kept)
  data/<id>/index.json           list of archived runs
  data/state.json                last run time per digest

Standard library only. Usage:
  python scripts/build_digests.py              # run whatever is due
  python scripts/build_digests.py --force all  # run everything now
  python scripts/build_digests.py --force sharjah,b747-mro
"""
import argparse
import datetime as dt
import email.utils
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "digests.json"
DATA = ROOT / "data"
STATE = DATA / "state.json"
KEEP_ARCHIVES = 60
UA = "Mozilla/5.0 (news-digest; +https://github.com)"


# ---------- query building (keep in sync with index.html buildQuery) ----------
def quote_term(t):
    t = t.strip()
    if not t:
        return ""
    if t.startswith('"') and t.endswith('"'):
        return t
    if any(c in t for c in " -/"):
        return f'"{t}"'
    return t


def build_query(d):
    raw = (d.get("raw_query") or "").strip()
    if raw:
        return raw
    parts = []
    for group in d.get("groups") or []:
        terms = [quote_term(t) for t in group if t and t.strip()]
        if len(terms) > 1:
            parts.append("(" + " OR ".join(terms) + ")")
        elif terms:
            parts.append(terms[0])
    for e in d.get("exclude") or []:
        q = quote_term(e)
        if q:
            parts.append("-" + q)
    return " ".join(parts)


def window_token(hours):
    hours = int(hours or 24)
    return f"when:{hours // 24}d" if hours % 24 == 0 else f"when:{hours}h"


def feed_url(query, edition, hours):
    country, lang = (edition.split(":") + ["en"])[:2]
    hl = f"{lang}-{country}" if lang == "en" else lang
    q = f"{query} {window_token(hours)}"
    params = urllib.parse.urlencode({"q": q, "hl": hl, "gl": country, "ceid": f"{country}:{lang}"})
    return f"https://news.google.com/rss/search?{params}"


# ---------- fetching ----------
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def parse_rss(xml_bytes, edition):
    items = []
    root = ET.fromstring(xml_bytes)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -(len(source) + 3)].strip()
        pub = it.findtext("pubDate")
        published = None
        if pub:
            try:
                published = email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc).isoformat()
            except Exception:
                published = None
        if title and link:
            items.append({"title": title, "link": link, "source": source,
                          "published": published, "edition": edition})
    return items


def norm_title(t):
    return "".join(c for c in t.lower() if c.isalnum())[:90]


def collect(d):
    query = build_query(d)
    hours = d.get("lookback_hours", 24)
    seen, items, errors = set(), [], []
    for ed in d.get("editions") or ["US:en"]:
        url = feed_url(query, ed, hours)
        try:
            for item in parse_rss(fetch(url), ed):
                key = norm_title(item["title"])
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)
        except Exception as e:  # keep going with other editions
            errors.append(f"{ed}: {e}")
    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return query, items[: int(d.get("max_items", 50))], errors


# ---------- scheduling ----------
def last_slot(d, now_utc):
    """Most recent scheduled moment (UTC) at or before now, within the last 8 days."""
    tz = ZoneInfo(d.get("timezone") or "Asia/Dubai")
    local_now = now_utc.astimezone(tz)
    days = set(d.get("days") if d.get("days") is not None else range(7))
    best = None
    for back in range(8):
        day = (local_now - dt.timedelta(days=back)).date()
        if day.weekday() not in days:
            continue
        for t in d.get("times") or []:
            try:
                hh, mm = (int(x) for x in t.split(":"))
            except ValueError:
                continue
            slot = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
            if slot <= local_now and (best is None or slot > best):
                best = slot
        if best:
            break
    return best.astimezone(dt.timezone.utc) if best else None


def is_due(d, now_utc, state):
    if not d.get("enabled", True):
        return False
    slot = last_slot(d, now_utc)
    if slot is None:
        return False
    last = state.get(d["id"], {}).get("last_run")
    if last is None:
        return now_utc - slot < dt.timedelta(hours=6)  # new digest: wait for its next slot unless close
    return dt.datetime.fromisoformat(last) < slot


# ---------- main ----------
def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def produce(d, now_utc, state):
    folder = DATA / d["id"]
    previous = load_json(folder / "latest.json", {})
    prev_links = {norm_title(i["title"]) for i in previous.get("items", [])}
    query, items, errors = collect(d)
    for i in items:
        i["new"] = norm_title(i["title"]) not in prev_links
    tz = ZoneInfo(d.get("timezone") or "Asia/Dubai")
    stamp = now_utc.astimezone(tz).strftime("%Y-%m-%d_%H%M")
    out = {"id": d["id"], "name": d["name"], "query": query,
           "generated": now_utc.isoformat(), "generated_local": stamp,
           "timezone": d.get("timezone"), "count": len(items),
           "new_count": sum(1 for i in items if i["new"]),
           "errors": errors, "items": items}
    write_json(folder / "latest.json", out)
    write_json(folder / f"{stamp}.json", out)
    archives = sorted(p.name for p in folder.glob("20*.json"))
    for old in archives[:-KEEP_ARCHIVES]:
        (folder / old).unlink()
    archives = archives[-KEEP_ARCHIVES:]
    write_json(folder / "index.json", {"runs": list(reversed(archives))})
    state[d["id"]] = {"last_run": now_utc.isoformat(), "count": len(items), "errors": errors}
    print(f"[{d['id']}] {len(items)} items ({out['new_count']} new){' ERRORS: ' + '; '.join(errors) if errors else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", default="", help="'all' or comma-separated digest ids")
    args = ap.parse_args()
    cfg = load_json(CONFIG, {"digests": []})
    state = load_json(STATE, {})
    now = dt.datetime.now(dt.timezone.utc)
    force = {x.strip() for x in args.force.split(",") if x.strip()}
    ran = 0
    for d in cfg.get("digests", []):
        if "all" in force or d["id"] in force or is_due(d, now, state):
            produce(d, now, state)
            ran += 1
    if ran:
        write_json(STATE, state)
    print(f"{ran} digest(s) produced.")


if __name__ == "__main__":
    sys.exit(main())
