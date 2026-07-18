#!/usr/bin/env python3
"""Generate a flat, self-contained HTML schedule from technical_papers_2026.json."""

import html
import json
import re
import urllib.parse
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

JSON_PATH = Path("technical_papers_2026.json")
CSV_PATH = Path("technical_papers_2026.csv")
HTML_PATH = Path("technical_papers_schedule.html")
IMAGE_BASE = (
    "https://s2026.conference-schedule.org/wp-content/linklings_snippets/representative_images/"
)
SOURCE_URL = "https://s2026.conference-schedule.org/?filter1=sstype132"

GOOGLE_CALENDAR_ICON = """
<svg viewBox="0 0 24 24" aria-hidden="true">
  <rect x="3" y="4" width="18" height="18" rx="2" fill="#fff" stroke="#dadce0" stroke-width="0.8"/>
  <rect x="3" y="4" width="18" height="5" fill="#1a73e8"/>
  <rect x="6" y="2" width="2.2" height="4" rx="1" fill="#1a73e8"/>
  <rect x="15.8" y="2" width="2.2" height="4" rx="1" fill="#1a73e8"/>
  <rect x="6" y="12" width="3" height="3" rx="0.5" fill="#1a73e8"/>
  <rect x="10.5" y="12" width="3" height="3" rx="0.5" fill="#fbbc04"/>
  <rect x="15" y="12" width="3" height="3" rx="0.5" fill="#34a853"/>
  <rect x="6" y="16.5" width="3" height="3" rx="0.5" fill="#ea4335"/>
  <rect x="10.5" y="16.5" width="3" height="3" rx="0.5" fill="#4285f4"/>
</svg>
""".strip()

APPLE_CALENDAR_ICON = """
<svg viewBox="0 0 24 24" aria-hidden="true">
  <rect x="3" y="4" width="18" height="18" rx="4.5" fill="#ff3b30"/>
  <rect x="3" y="4" width="18" height="6" fill="#fff" opacity="0.96"/>
  <rect x="7" y="2.2" width="1.8" height="4.2" rx="0.9" fill="#d9d9d9"/>
  <rect x="15.2" y="2.2" width="1.8" height="4.2" rx="0.9" fill="#d9d9d9"/>
  <rect x="7" y="13" width="10" height="1.2" rx="0.6" fill="#fff" opacity="0.95"/>
  <rect x="7" y="16" width="10" height="1.2" rx="0.6" fill="#fff" opacity="0.85"/>
</svg>
""".strip()

OUTLOOK_CALENDAR_ICON = """
<svg viewBox="0 0 24 24" aria-hidden="true">
  <rect x="3" y="4" width="18" height="18" rx="2" fill="#0078d4"/>
  <rect x="3" y="4" width="18" height="5" fill="#106ebe"/>
  <rect x="6" y="2" width="2.2" height="4" rx="1" fill="#106ebe"/>
  <rect x="15.8" y="2" width="2.2" height="4" rx="1" fill="#106ebe"/>
  <path d="M8.2 12.2h7.6c1.2 0 2.2 1 2.2 2.2v3.2c0 1.2-1 2.2-2.2 2.2H8.2c-1.2 0-2.2-1-2.2-2.2v-3.2c0-1.2 1-2.2 2.2-2.2z" fill="#fff"/>
  <path d="M8.8 14.2h6.4v1.1H8.8zm0 2.2h4.6v1.1H8.8z" fill="#0078d4"/>
</svg>
""".strip()


def format_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %B %d").replace(" 0", " ")


def short_weekday(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a")


def short_month_day(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%b %d").replace(" 0", " ")


def clean_session_title(title: str) -> str:
    cleaned = re.sub(r"^Technical Paper\s*", "", title or "").strip()
    return cleaned or title


def image_url(representative_image: str) -> str:
    if not representative_image:
        return ""
    basename = urllib.parse.unquote(urllib.parse.urlparse(representative_image).path)
    basename = basename.split("/")[-1].replace("_gj9f", "")
    return IMAGE_BASE + basename


SKIP_TRACKS = {"Full Conference", "Full Conference Supporter"}


def meaningful_tracks(tracks: list) -> list:
    names = []
    for track in tracks:
        name = track["name"] if isinstance(track, dict) else track
        if name not in SKIP_TRACKS and name not in names:
            names.append(name)
    return names


def collect_filter_options(papers: list) -> tuple[list[str], list[str]]:
    keywords = []
    rooms = []
    seen_kw = set()
    seen_room = set()
    for paper in papers:
        room = paper.get("session_room", "").strip()
        if room and room not in seen_room:
            seen_room.add(room)
            rooms.append(room)
        for topic in meaningful_tracks(paper.get("tracks") or []):
            if topic not in seen_kw:
                seen_kw.add(topic)
                keywords.append(topic)
    keywords.sort(key=str.lower)
    rooms.sort()
    return keywords, rooms


def format_authors(authors: list) -> str:
    parts = []
    for author in authors:
        name = html.escape(author["name"])
        if author.get("presenting"):
            parts.append(f"<strong>{name}</strong>")
        else:
            parts.append(name)
    return ", ".join(parts)


def tooltip_text(paper: dict) -> str:
    lines = []
    keywords = paper.get("keywords") or []
    tracks = meaningful_tracks(paper.get("tracks") or [])
    if keywords:
        lines.append("Keywords: " + ", ".join(keywords))
    if tracks:
        lines.append("Tracks: " + ", ".join(tracks))
    if paper.get("paper_category") == "TOG Journal Paper":
        lines.append("ACM TOG journal paper")
    return " · ".join(lines)


def format_ics_datetime(iso_time: str) -> str:
    return iso_time.replace("-", "").replace(":", "")


def ics_filename(title: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", title or "", flags=re.UNICODE)
    safe = re.sub(r"[-\s]+", "-", safe).strip("-")
    return (safe[:60] or "siggraph-paper") + ".ics"


def google_calendar_url(paper: dict) -> str:
    start = paper.get("presentation_start_utc") or paper.get("start_time_utc", "")
    end = paper.get("presentation_end_utc") or paper.get("end_time_utc", "")
    if not start or not end:
        return ""

    details_lines = []
    if paper.get("authors_all"):
        details_lines.append(f"Authors: {paper['authors_all']}")
    session_title = clean_session_title(paper.get("session_title", ""))
    if session_title:
        details_lines.append(f"Session: {session_title}")
    if paper.get("url"):
        details_lines.append(paper["url"])

    params = urllib.parse.urlencode(
        {
            "action": "TEMPLATE",
            "text": paper.get("title", ""),
            "dates": f"{format_ics_datetime(start)}/{format_ics_datetime(end)}",
            "details": "\n".join(details_lines),
            "location": paper.get("session_room", ""),
        }
    )
    return f"https://calendar.google.com/calendar/render?{params}"


def render_calendar_links(paper: dict) -> str:
    google_url = google_calendar_url(paper)
    ics_url = paper.get("calendar_url", "")
    if not google_url and not ics_url:
        return ""

    ics_name = html.escape(ics_filename(paper.get("title", "")), quote=True)
    links = []

    if google_url:
        links.append(
            f'<a class="cal-add cal-add-google" href="{html.escape(google_url, quote=True)}" '
            f'target="_blank" rel="noopener" title="Add to Google Calendar">{GOOGLE_CALENDAR_ICON}</a>'
        )

    if ics_url:
        escaped_ics = html.escape(ics_url, quote=True)
        links.append(
            f'<a class="cal-add cal-add-apple" href="{escaped_ics}" download="{ics_name}" '
            f'title="Add to Apple Calendar">{APPLE_CALENDAR_ICON}</a>'
        )
        links.append(
            f'<a class="cal-add cal-add-outlook" href="{escaped_ics}" download="{ics_name}" '
            f'title="Add to Outlook">{OUTLOOK_CALENDAR_ICON}</a>'
        )

    return f'<div class="paper-calendars">{"".join(links)}</div>'


def build_structure(papers: list) -> OrderedDict:
    days = OrderedDict()
    for paper in papers:
        date = paper["date"]
        session_id = paper["session_id"]
        days.setdefault(date, OrderedDict())
        if session_id not in days[date]:
            days[date][session_id] = {
                "session_id": session_id,
                "title": clean_session_title(paper.get("session_title", "")),
                "room": paper.get("session_room", ""),
                "start": paper.get("session_start_time_display", ""),
                "end": paper.get("session_end_time_display", ""),
                "timezone": paper.get("timezone", "PDT"),
                "chair": ", ".join(
                    chair["name"] for chair in paper.get("session_chairs", [])
                ),
                "papers": [],
            }
        days[date][session_id]["papers"].append(paper)
    return days


def render_paper(paper: dict) -> str:
    title = html.escape(paper["title"])
    url = html.escape(paper.get("url", ""), quote=True)
    authors = format_authors(paper.get("authors") or [])
    time_range = (
        f"{paper.get('start_time_display', '')}–{paper.get('end_time_display', '')}"
    )
    img = image_url(paper.get("representative_image", ""))
    tip = html.escape(tooltip_text(paper), quote=True)
    badge = (
        '<span class="badge tog">TOG</span>' if paper.get("paper_category") == "TOG Journal Paper" else ""
    )
    tracks = meaningful_tracks(paper.get("tracks") or [])
    tag_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tracks[:3])

    img_html = (
        f'<img class="thumb" src="{html.escape(img, quote=True)}" alt="" loading="lazy">'
        if img
        else '<div class="thumb placeholder"></div>'
    )

    topics = meaningful_tracks(paper.get("tracks") or [])
    search_blob = html.escape(
        " ".join(
            [
                paper.get("title", ""),
                " ".join(a["name"] for a in paper.get("authors") or []),
                " ".join(topics),
                paper.get("session_room", ""),
            ]
        ).lower()
    )
    topic_data = html.escape("|".join(topics), quote=True)
    room_data = html.escape(paper.get("session_room", ""), quote=True)
    calendar_links = render_calendar_links(paper)

    return f"""
    <article class="paper" data-search="{search_blob}" data-topics="{topic_data}" data-room="{room_data}" title="{tip}">
      {calendar_links}
      {img_html}
      <div class="paper-body">
        <div class="paper-meta">
          <time>{html.escape(time_range)}</time>
          {badge}
          {tag_html}
        </div>
        <h4 class="paper-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></h4>
        <p class="authors">{authors}</p>
      </div>
    </article>
    """


def render_session(session: dict) -> str:
    session_id = session["session_id"]
    title = html.escape(session["title"])
    room = html.escape(session.get("room", ""))
    chair = html.escape(session.get("chair", ""))
    time_range = f"{session.get('start', '')}–{session.get('end', '')} {session.get('timezone', 'PDT')}"
    papers_html = "".join(render_paper(p) for p in session["papers"])
    search_blob = html.escape(
        " ".join([session["title"], session.get("room", ""), session.get("chair", "")]).lower()
    )

    chair_html = f'<span class="chair">Chair: {chair}</span>' if chair else ""
    return f"""
    <section class="session" data-search="{search_blob}" data-room="{html.escape(session.get('room', ''), quote=True)}">
      <span class="scroll-anchor" id="session-{html.escape(session_id)}"></span>
      <header class="session-header">
        <div>
          <h3>{title}</h3>
          <p class="session-details">
            <span class="time">{html.escape(time_range)}</span>
            <span class="room">{room}</span>
            {chair_html}
          </p>
        </div>
        <span class="count">{len(session["papers"])} papers</span>
      </header>
      <div class="papers">{papers_html}</div>
    </section>
    """


def render_day(date: str, sessions: OrderedDict) -> str:
    label = format_date(date)
    session_items = "".join(render_session(session) for session in sessions.values())
    paper_count = sum(len(s["papers"]) for s in sessions.values())
    return f"""
    <section class="day">
      <span class="scroll-anchor" id="day-{date}"></span>
      <header class="day-header">
        <h2>{html.escape(label)}</h2>
        <p>{len(sessions)} sessions · {paper_count} papers</p>
      </header>
      {session_items}
    </section>
    """


def render_filter_buttons(label: str, group: str, values: list[str]) -> str:
    buttons = []
    for value in values:
        slug = html.escape(value, quote=True)
        buttons.append(
            f'<button type="button" class="filter-btn active" '
            f'data-filter-group="{group}" data-filter-value="{slug}">{html.escape(value)}</button>'
        )
    return f"""
    <div class="filter-group" data-filter-group="{group}">
      <div class="filter-group-head">
        <span class="filter-label">{html.escape(label)}</span>
        <span class="filter-actions">
          <button type="button" class="filter-action" data-filter-action="all-on" data-filter-group="{group}">All on</button>
          <button type="button" class="filter-action" data-filter-action="all-off" data-filter-group="{group}">All off</button>
        </span>
      </div>
      <div class="filter-buttons">{''.join(buttons)}</div>
    </div>
    """


def render_filters(keywords: list[str], rooms: list[str], total: int) -> str:
    return f"""
    <div class="filters" id="filters">
      <div class="filters-top">
        <span class="filters-title">Filters</span>
        <div class="filters-controls">
          <a class="to-calendar" href="#calendar">↑ Calendar</a>
          <button type="button" class="clear-filters" id="clear-filters">Clear Filters</button>
        </div>
      </div>
      {render_filter_buttons("Keywords", "keyword", keywords)}
      {render_filter_buttons("Rooms", "room", rooms)}
      <div class="filters-footer">
        <span class="match-count" id="match-count">{total} of {total} papers</span>
      </div>
    </div>
    """


def render_calendar(days: OrderedDict) -> str:
    cards = []
    for date, sessions in days.items():
        session_links = []
        for session in sessions.values():
            sid = session["session_id"]
            stitle = html.escape(session["title"])
            stime = html.escape(f"{session['start']}–{session['end']}")
            session_links.append(
                f'<a class="cal-session" href="#session-{html.escape(sid)}">'
                f'<span class="cal-time">{stime}</span>'
                f"<span class=\"cal-title\">{stitle}</span></a>"
            )
        cards.append(
            f"""
            <div class="day-card">
              <a class="day-card-top" href="#day-{date}">
                <span class="weekday">{html.escape(short_weekday(date))}</span>
                <span class="monthday">{html.escape(short_month_day(date))}</span>
              </a>
              <div class="day-card-sessions">{''.join(session_links)}</div>
            </div>
            """
        )
    return f'<nav class="calendar" id="calendar" aria-label="Conference days">{"".join(cards)}</nav>'


def generate_html(data: dict) -> str:
    papers = data["papers"]
    days = build_structure(papers)
    keywords, rooms = collect_filter_options(papers)
    total = data["total_papers"]
    calendar = render_calendar(days)
    filters = render_filters(keywords, rooms, total)
    schedule = "".join(render_day(date, sessions) for date, sessions in days.items())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SIGGRAPH 2026 Technical Papers</title>
  <style>
    :root {{
      --bg: #f4f1ec;
      --surface: #ffffff;
      --ink: #1a1f2e;
      --muted: #5f677a;
      --line: #ddd7ce;
      --accent: #d44b26;
      --accent-soft: #fdeee8;
      --navy: #142033;
      --navy-soft: #24324a;
      --shadow: 0 10px 30px rgba(20, 32, 51, 0.08);
      --radius: 16px;
      --sticky-offset: 140px;
    }}

    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font: 16px/1.5 "Segoe UI", system-ui, -apple-system, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(212, 75, 38, 0.08), transparent 28%),
        linear-gradient(180deg, #ebe6df 0%, var(--bg) 220px);
    }}

    .page {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px 20px 80px;
    }}

    .hero {{
      background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%);
      color: white;
      border-radius: calc(var(--radius) + 4px);
      padding: 28px 28px 24px;
      box-shadow: var(--shadow);
    }}

    .hero h1 {{
      margin: 0 0 8px;
      font-size: clamp(1.6rem, 2.5vw, 2.35rem);
      letter-spacing: -0.03em;
    }}

    .hero p {{
      margin: 0;
      color: rgba(255,255,255,0.78);
      max-width: 60ch;
    }}

    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
      align-items: center;
    }}

    .stat {{
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 0.92rem;
    }}

    .hero-downloads {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}

    .hero-downloads a {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 999px;
      padding: 6px 12px;
      color: white;
      font-size: 0.86rem;
      font-weight: 600;
      text-decoration: none;
      transition: background 0.15s ease, border-color 0.15s ease;
    }}

    .hero-downloads a:hover {{
      background: rgba(255,255,255,0.18);
      border-color: rgba(255,255,255,0.32);
    }}

    .search-wrap {{
      flex: 1 1 260px;
      min-width: 220px;
    }}

    #search {{
      width: 100%;
      border: 0;
      border-radius: 999px;
      padding: 12px 16px 12px 42px;
      font: inherit;
      background: white url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="%235f677a" stroke-width="2"><circle cx="8" cy="8" r="6"/><path d="m13 13 4 4"/></svg>') 14px center no-repeat;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
    }}

    .calendar-shell {{
      margin-top: 22px;
    }}

    .filters-shell {{
      position: sticky;
      top: 0;
      z-index: 20;
      margin-top: 12px;
      padding: 8px 0 10px;
      backdrop-filter: blur(10px);
      background: rgba(244, 241, 236, 0.92);
      border-bottom: 1px solid rgba(221, 215, 206, 0.8);
    }}

    .filters {{
      padding: 8px 12px 10px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: var(--shadow);
    }}

    .filters-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }}

    .filters-title {{
      font-weight: 700;
      font-size: 0.78rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--navy);
    }}

    .filters-controls {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .to-calendar {{
      border: 1px solid var(--line);
      background: #f7f4ef;
      color: var(--navy);
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 0.74rem;
      font-weight: 600;
      text-decoration: none;
      white-space: nowrap;
      transition: background 0.15s ease, border-color 0.15s ease;
    }}

    .to-calendar:hover {{
      background: var(--accent-soft);
      border-color: rgba(212, 75, 38, 0.35);
      color: var(--accent);
    }}

    .clear-filters {{
      border: 1px solid var(--line);
      background: #f7f4ef;
      color: var(--muted);
      border-radius: 999px;
      padding: 4px 10px;
      font: inherit;
      font-size: 0.74rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }}

    .clear-filters.active {{
      background: var(--accent-soft);
      color: var(--accent);
      border-color: rgba(212, 75, 38, 0.35);
      box-shadow: 0 0 0 3px rgba(212, 75, 38, 0.12);
    }}

    .filter-group + .filter-group {{
      margin-top: 7px;
      padding-top: 7px;
      border-top: 1px solid rgba(221, 215, 206, 0.8);
    }}

    .filter-group-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 5px;
    }}

    .filter-label {{
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .filter-actions {{
      display: flex;
      gap: 6px;
    }}

    .filter-action {{
      border: 0;
      background: transparent;
      color: var(--accent);
      font: inherit;
      font-size: 0.68rem;
      font-weight: 600;
      cursor: pointer;
      padding: 0;
    }}

    .filter-action:hover {{
      text-decoration: underline;
    }}

    .filter-buttons {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }}

    .filter-btn {{
      border: 1px solid var(--line);
      background: #faf8f5;
      color: var(--ink);
      border-radius: 999px;
      padding: 3px 8px;
      font: inherit;
      font-size: 0.72rem;
      line-height: 1.3;
      cursor: pointer;
      transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease, opacity 0.12s ease;
    }}

    .filter-btn.active {{
      background: var(--navy);
      color: white;
      border-color: var(--navy);
    }}

    .filter-btn:not(.active) {{
      opacity: 0.72;
    }}

    .filters-footer {{
      display: flex;
      justify-content: flex-end;
      margin-top: 7px;
      padding-top: 6px;
      border-top: 1px solid rgba(221, 215, 206, 0.65);
    }}

    .match-count {{
      font-size: 0.72rem;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }}

    .match-count.filtered {{
      color: var(--accent);
      font-weight: 700;
    }}

    .calendar {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}

    .day-card {{
      display: block;
      color: inherit;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: var(--shadow);
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}

    .day-card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent);
    }}

    .day-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      padding: 12px 14px 8px;
      background: var(--accent-soft);
      border-bottom: 1px solid var(--line);
      text-decoration: none;
      color: inherit;
    }}

    .day-card-top:hover .monthday {{
      color: var(--accent);
    }}

    .weekday {{
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-size: 0.78rem;
    }}

    .monthday {{
      font-weight: 700;
      font-size: 1.05rem;
    }}

    .day-card-sessions {{
      display: grid;
      gap: 0;
      max-height: 220px;
      overflow: auto;
    }}

    .cal-session {{
      display: block;
      padding: 8px 12px;
      text-decoration: none;
      color: inherit;
      border-top: 1px solid rgba(221, 215, 206, 0.65);
      font-size: 0.82rem;
    }}

    .cal-session:hover {{
      background: #faf8f5;
    }}

    .cal-time {{
      display: block;
      color: var(--muted);
      font-size: 0.76rem;
      line-height: 1.25;
      margin-bottom: 3px;
      font-variant-numeric: tabular-nums;
    }}

    .cal-title {{
      display: block;
      color: var(--ink);
      line-height: 1.35;
    }}

    .cal-session.hidden {{
      display: none;
    }}

    .scroll-anchor {{
      display: block;
      position: relative;
      top: calc(-1 * var(--sticky-offset));
      height: 0;
      scroll-margin-top: var(--sticky-offset);
    }}

    #calendar {{
      scroll-margin-top: 12px;
    }}

    .day, .session, .paper {{ scroll-margin-top: var(--sticky-offset); }}

    .day-header {{
      margin: 34px 0 18px;
      padding-bottom: 12px;
      border-bottom: 2px solid var(--navy);
    }}

    .day-header h2 {{
      margin: 0;
      font-size: 1.55rem;
      letter-spacing: -0.02em;
    }}

    .day-header p {{
      margin: 6px 0 0;
      color: var(--muted);
    }}

    .session {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      margin-bottom: 18px;
      overflow: hidden;
    }}

    .session-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      padding: 18px 20px;
      background: linear-gradient(180deg, #faf8f5, #fff);
      border-bottom: 1px solid var(--line);
    }}

    .session-header h3 {{
      margin: 0 0 8px;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
    }}

    .session-details {{
      margin: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 0.94rem;
    }}

    .session-details .time {{
      color: var(--ink);
      font-weight: 600;
    }}

    .count {{
      flex: 0 0 auto;
      background: var(--navy);
      color: white;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.82rem;
      white-space: nowrap;
    }}

    .papers {{
      display: grid;
    }}

    .paper {{
      position: relative;
      display: grid;
      grid-template-columns: 92px 1fr;
      gap: 16px;
      padding: 16px 88px 16px 20px;
      border-top: 1px solid rgba(221, 215, 206, 0.8);
      transition: background 0.12s ease;
    }}

    .paper:first-child {{ border-top: 0; }}
    .paper:hover {{ background: #fcfbfa; }}

    .paper-calendars {{
      position: absolute;
      top: 12px;
      right: 14px;
      display: flex;
      gap: 5px;
      align-items: center;
    }}

    .cal-add {{
      display: inline-flex;
      width: 22px;
      height: 22px;
      border-radius: 6px;
      overflow: hidden;
      opacity: 0.88;
      transition: transform 0.12s ease, opacity 0.12s ease, box-shadow 0.12s ease;
    }}

    .cal-add:hover {{
      opacity: 1;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(20, 32, 51, 0.12);
    }}

    .cal-add svg {{
      display: block;
      width: 22px;
      height: 22px;
    }}

    .thumb {{
      width: 92px;
      height: 68px;
      object-fit: cover;
      border-radius: 10px;
      background: #ece7df;
      border: 1px solid var(--line);
    }}

    .thumb.placeholder {{
      background: linear-gradient(135deg, #ece7df, #f7f4ef);
    }}

    .paper-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 6px;
      font-size: 0.86rem;
      color: var(--muted);
    }}

    .paper-meta time {{
      font-weight: 700;
      color: var(--accent);
      font-variant-numeric: tabular-nums;
    }}

    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    .badge.tog {{
      background: #e8eef8;
      color: #2b4c7e;
    }}

    .tag {{
      display: inline-block;
      background: #f1ede7;
      color: var(--muted);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.75rem;
    }}

    .paper-title {{
      margin: 0 0 6px;
      font-size: 1.02rem;
      line-height: 1.35;
      letter-spacing: -0.01em;
    }}

    .paper-title a {{
      color: var(--ink);
      text-decoration: none;
    }}

    .paper-title a:hover {{
      color: var(--accent);
    }}

    .authors {{
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .authors strong {{
      color: var(--ink);
      font-weight: 700;
    }}

    .footer-note {{
      margin-top: 36px;
      color: var(--muted);
      font-size: 0.9rem;
      text-align: center;
    }}

    .footer-note a {{ color: var(--accent); }}

    .hidden {{ display: none !important; }}

    @media (max-width: 980px) {{
      .calendar {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}

    @media (max-width: 640px) {{
      .page {{ padding-inline: 14px; }}
      .calendar {{ grid-template-columns: 1fr; }}
      .paper {{ grid-template-columns: 72px 1fr; gap: 12px; }}
      .thumb {{ width: 72px; height: 54px; }}
      .session-header, .paper {{ padding-inline: 14px; }}
      .paper {{ padding-right: 78px; }}
      .paper-calendars {{ right: 10px; }}
      .filters-top {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <h1>SIGGRAPH 2026 Technical Papers</h1>
      <p>A flat, scannable schedule of all {total} paper presentations — grouped by day and session, with quick jump navigation.</p>
      <div class="hero-downloads">
        <a href="{html.escape(CSV_PATH.name)}" download>Download CSV</a>
        <a href="{html.escape(JSON_PATH.name)}" download>Download JSON</a>
      </div>
      <div class="hero-meta">
        <span class="stat">{total} papers</span>
        <span class="stat">{len(days)} days</span>
        <span class="stat">Times in PDT</span>
        <label class="search-wrap">
          <input id="search" type="search" placeholder="Search titles, authors, topics, rooms…" autocomplete="off">
        </label>
      </div>
    </header>

    <div class="calendar-shell">
      {calendar}
    </div>

    <div class="filters-shell" id="sticky-shell">
      {filters}
    </div>

    <main id="schedule">
      {schedule}
    </main>

    <p class="footer-note">
      Generated from the <a href="{html.escape(SOURCE_URL)}" target="_blank" rel="noopener">official SIGGRAPH 2026 schedule</a>.
      Paper details and thumbnails link back to ACM SIGGRAPH.
    </p>
  </div>

  <script>
    const search = document.getElementById('search');
    const clearFilters = document.getElementById('clear-filters');
    const matchCount = document.getElementById('match-count');
    const stickyShell = document.getElementById('sticky-shell');
    const papers = Array.from(document.querySelectorAll('.paper'));
    const sessions = Array.from(document.querySelectorAll('.session'));
    const days = Array.from(document.querySelectorAll('.day'));
    const filterButtons = Array.from(document.querySelectorAll('.filter-btn'));
    const filterActions = Array.from(document.querySelectorAll('.filter-action'));

    function normalize(value) {{
      return (value || '').toLowerCase().trim();
    }}

    function splitTopics(value) {{
      return (value || '').split('|').map(item => item.trim()).filter(Boolean);
    }}

    function activeValues(group) {{
      return new Set(
        filterButtons
          .filter(btn => btn.dataset.filterGroup === group && btn.classList.contains('active'))
          .map(btn => btn.dataset.filterValue)
      );
    }}

    function allButtonsActive(group) {{
      return filterButtons
        .filter(btn => btn.dataset.filterGroup === group)
        .every(btn => btn.classList.contains('active'));
    }}

    function filtersAreDefault() {{
      return allButtonsActive('keyword') && allButtonsActive('room') && !normalize(search.value);
    }}

    function updateClearFiltersButton() {{
      clearFilters.classList.toggle('active', !filtersAreDefault());
    }}

    function updateStickyOffset() {{
      const offset = stickyShell.offsetHeight + 16;
      document.documentElement.style.setProperty('--sticky-offset', `${{offset}}px`);
    }}

    function paperMatchesFilters(paper) {{
      const activeKeywords = activeValues('keyword');
      const activeRooms = activeValues('room');
      const topics = splitTopics(paper.dataset.topics);
      const room = paper.dataset.room || '';

      const keywordMatch = topics.length === 0
        ? activeKeywords.size > 0
        : topics.some(topic => activeKeywords.has(topic));
      const roomMatch = !room || activeRooms.has(room);
      return keywordMatch && roomMatch;
    }}

    function updateMatchCount() {{
      const visibleCount = papers.filter(paper => !paper.classList.contains('hidden')).length;
      matchCount.textContent = `${{visibleCount}} of ${{papers.length}} papers`;
      matchCount.classList.toggle('filtered', visibleCount !== papers.length);
    }}

    function applyFilters() {{
      const query = normalize(search.value);

      papers.forEach(paper => {{
        const haystack = paper.dataset.search || '';
        const searchMatch = !query || haystack.includes(query);
        const filterMatch = paperMatchesFilters(paper);
        paper.classList.toggle('hidden', !(searchMatch && filterMatch));
      }});

      sessions.forEach(session => {{
        const visible = session.querySelector('.paper:not(.hidden)');
        session.classList.toggle('hidden', !visible);
      }});

      days.forEach(day => {{
        const visible = day.querySelector('.session:not(.hidden)');
        day.classList.toggle('hidden', !visible);
      }});

      updateClearFiltersButton();
      updateMatchCount();
      updateCalendarVisibility();
    }}

    function updateCalendarVisibility() {{
      document.querySelectorAll('.cal-session').forEach(link => {{
        const id = (link.getAttribute('href') || '').replace('#', '');
        const target = id ? document.getElementById(id)?.closest('.session') : null;
        link.classList.toggle('hidden', !!target && target.classList.contains('hidden'));
      }});
    }}

    function setGroupState(group, active) {{
      filterButtons
        .filter(btn => btn.dataset.filterGroup === group)
        .forEach(btn => btn.classList.toggle('active', active));
      applyFilters();
    }}

    filterButtons.forEach(button => {{
      button.addEventListener('click', () => {{
        button.classList.toggle('active');
        applyFilters();
      }});
    }});

    filterActions.forEach(button => {{
      button.addEventListener('click', () => {{
        const group = button.dataset.filterGroup;
        const turnOn = button.dataset.filterAction === 'all-on';
        setGroupState(group, turnOn);
      }});
    }});

    clearFilters.addEventListener('click', () => {{
      search.value = '';
      setGroupState('keyword', true);
      setGroupState('room', true);
    }});

    search.addEventListener('input', applyFilters);
    window.addEventListener('load', updateStickyOffset);
    window.addEventListener('resize', updateStickyOffset);
    updateStickyOffset();
    updateMatchCount();
    updateClearFiltersButton();
  </script>
</body>
</html>
"""


def main():
    with JSON_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    content = generate_html(data)
    for path in (HTML_PATH, Path("index.html")):
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
