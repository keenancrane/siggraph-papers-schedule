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
HTML_PATH = Path("index.html")
IMAGE_BASE = (
    "https://s2026.conference-schedule.org/wp-content/linklings_snippets/representative_images/"
)
SOURCE_URL = "https://s2026.conference-schedule.org/?filter1=sstype132"

# Compact labels for filter chips only (data-filter-value stays full).
FILTER_DISPLAY_LABELS = {
    "Virtual Reality": "VR",
    "Artificial Intelligence/Machine Learning": "AI/ML",
}

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
            parts.append(f'<span class="presenting">{name}</span>')
        else:
            parts.append(name)
    return ", ".join(parts)


def format_ics_datetime(iso_time: str) -> str:
    return iso_time.replace("-", "").replace(":", "")


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
    links = []

    if google_url:
        links.append(
            f'<a class="cal-add cal-add-google" href="{html.escape(google_url, quote=True)}" '
            f'target="_blank" rel="noopener" title="Add to Google Calendar">{GOOGLE_CALENDAR_ICON}</a>'
        )

    # Apple / Outlook use locally generated .ics downloads (remote SIGGRAPH
    # calendar URLs return 403 when hotlinked from other origins).
    links.append(
        f'<button type="button" class="cal-add cal-add-apple" data-ics-download '
        f'title="Add to Apple Calendar">{APPLE_CALENDAR_ICON}</button>'
    )
    links.append(
        f'<button type="button" class="cal-add cal-add-outlook" data-ics-download '
        f'title="Add to Outlook">{OUTLOOK_CALENDAR_ICON}</button>'
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
    paper_id = html.escape(paper.get("paper_id", ""), quote=True)
    start_utc = html.escape(
        paper.get("presentation_start_utc") or paper.get("start_time_utc", ""),
        quote=True,
    )
    end_utc = html.escape(
        paper.get("presentation_end_utc") or paper.get("end_time_utc", ""),
        quote=True,
    )
    session_title = html.escape(
        clean_session_title(paper.get("session_title", "")), quote=True
    )
    authors_plain = html.escape(paper.get("authors_all", ""), quote=True)
    date = html.escape(paper.get("date", ""), quote=True)
    title_attr = html.escape(paper.get("title", ""), quote=True)
    time_display = html.escape(time_range, quote=True)

    return f"""
    <article class="paper" data-paper-id="{paper_id}" data-date="{date}" data-start="{start_utc}" data-end="{end_utc}" data-time="{time_display}" data-session="{session_title}" data-authors="{authors_plain}" data-title="{title_attr}" data-url="{url}" data-search="{search_blob}" data-topics="{topic_data}" data-room="{room_data}">
      <div class="paper-media">
        {img_html}
        <button type="button" class="select-talk" aria-pressed="false" aria-label="Add to my schedule" title="Add to my schedule">
          <svg class="select-icon" viewBox="0 0 20 20" aria-hidden="true">
            <circle class="select-ring" cx="10" cy="10" r="7.25" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <path class="select-plus" d="M10 6.5v7M6.5 10h7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            <path class="select-check" d="M6.6 10.2l2.2 2.2 4.6-4.8" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      {calendar_links}
      <div class="paper-body">
        <div class="paper-meta">
          <div class="paper-time-row">
            <time><span class="conflict-mark" aria-hidden="true">⚠️</span>{html.escape(time_range)}</time>
          </div>
          {f'<div class="paper-tags">{tag_html}</div>' if tag_html else ''}
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
        <h3>{title}</h3>
        <p class="session-details">
          <span class="time">{html.escape(time_range)}</span>
          <span class="room">{room}</span>
          {chair_html}
        </p>
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


def filter_display_label(value: str, group: str) -> str:
    if value in FILTER_DISPLAY_LABELS:
        return FILTER_DISPLAY_LABELS[value]
    if group == "room" and value.startswith("Room "):
        return value[5:]
    return value


def render_filter_buttons(
    label: str,
    group: str,
    values: list[str],
    *,
    trailing_html: str = "",
) -> str:
    buttons = []
    for value in values:
        slug = html.escape(value, quote=True)
        display = html.escape(filter_display_label(value, group))
        title_attr = (
            f' title="{html.escape(value, quote=True)}"'
            if filter_display_label(value, group) != value
            else ""
        )
        buttons.append(
            f'<button type="button" class="filter-btn active" '
            f'data-filter-group="{group}" data-filter-value="{slug}"{title_attr}>{display}</button>'
        )
    trailing = f'<div class="filter-trailing">{trailing_html}</div>' if trailing_html else ""
    return f"""
    <div class="filter-group" data-filter-group="{group}">
      <div class="filter-row">
        <div class="filter-heading">
          <span class="filter-label">{html.escape(label)}</span>
          <span class="filter-actions" role="group" aria-label="{html.escape(label)} selection">
            <button type="button" class="filter-action" data-filter-action="all-on" data-filter-group="{group}">All</button>
            <span class="filter-action-sep" aria-hidden="true">|</span>
            <button type="button" class="filter-action" data-filter-action="all-off" data-filter-group="{group}">None</button>
          </span>
        </div>
        <div class="filter-buttons">{''.join(buttons)}</div>
        {trailing}
      </div>
    </div>
    """


def render_filters(keywords: list[str], rooms: list[str], total: int) -> str:
    match_count = (
        f'<span class="match-count" id="match-count">{total} of {total} papers</span>'
    )
    return f"""
    <div class="filters" id="filters">
      <div class="filters-top">
        <div class="filters-title-row">
          <span class="filters-title">Filters</span>
          <button type="button" class="filters-toggle" id="filters-toggle" aria-expanded="true" aria-controls="filters-body">Hide</button>
        </div>
        <div class="filters-controls">
          <a class="to-calendar" href="#calendar">↑ Calendar</a>
          <button type="button" class="clear-filters" id="clear-filters">Clear</button>
        </div>
      </div>
      <div class="filters-body" id="filters-body">
        <label class="search-wrap">
          <span class="visually-hidden">Search schedule</span>
          <input id="search" type="search" placeholder="Search titles, authors, topics, rooms…" autocomplete="off">
        </label>
        {render_filter_buttons("Keywords", "keyword", keywords)}
        {render_filter_buttons("Rooms", "room", rooms, trailing_html=match_count)}
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
      --sticky-offset: 110px;
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
      max-width: 70ch;
    }}

    .hero p + p {{
      margin-top: 8px;
    }}

    .timezone-note {{
      margin-left: auto;
      color: #fff;
      font-weight: 700;
      white-space: nowrap;
    }}

    .hero-downloads {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
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

    .visually-hidden {{
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }}

    .search-wrap {{
      display: block;
      margin-bottom: 6px;
    }}

    #search {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 6px 10px 6px 30px;
      font: inherit;
      font-size: 0.78rem;
      color: var(--ink);
      background: #f7f4ef url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="%235f677a" stroke-width="2"><circle cx="6" cy="6" r="4.5"/><path d="m10 10 3 3"/></svg>') 9px center no-repeat;
      transition: border-color 0.15s ease, background 0.15s ease;
    }}

    #search:focus {{
      outline: none;
      border-color: rgba(212, 75, 38, 0.45);
      background-color: #fff;
    }}

    #search::placeholder {{
      color: #8a8490;
    }}

    .calendar-shell {{
      margin-top: 22px;
    }}

    .filters-shell {{
      position: sticky;
      top: 0;
      z-index: 20;
      margin-top: 10px;
      padding: 6px 0 8px;
      backdrop-filter: blur(10px);
      background: rgba(244, 241, 236, 0.92);
      border-bottom: 1px solid rgba(221, 215, 206, 0.8);
    }}

    .filters {{
      padding: 6px 10px 7px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 10px;
      box-shadow: var(--shadow);
    }}

    .filters-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 5px;
    }}

    .filters.collapsed .filters-top {{
      margin-bottom: 0;
    }}

    .filters-title-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}

    .filters-title {{
      font-weight: 700;
      font-size: 0.7rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--navy);
    }}

    .filters-toggle {{
      border: 1px solid var(--line);
      background: #f7f4ef;
      color: var(--muted);
      border-radius: 999px;
      padding: 2px 8px;
      font: inherit;
      font-size: 0.68rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
    }}

    .filters-toggle:hover {{
      background: var(--accent-soft);
      border-color: rgba(212, 75, 38, 0.35);
      color: var(--accent);
    }}

    .filters.collapsed .filters-body {{
      display: none;
    }}

    .filters-controls {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .to-calendar {{
      border: 1px solid var(--line);
      background: #f7f4ef;
      color: var(--navy);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.68rem;
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
      padding: 2px 8px;
      font: inherit;
      font-size: 0.68rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }}

    .clear-filters.active {{
      background: var(--accent-soft);
      color: var(--accent);
      border-color: rgba(212, 75, 38, 0.35);
      box-shadow: 0 0 0 2px rgba(212, 75, 38, 0.12);
    }}

    .filter-group + .filter-group {{
      margin-top: 5px;
      padding-top: 5px;
      border-top: 1px solid rgba(221, 215, 206, 0.8);
    }}

    .filter-row {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 4px 8px;
    }}

    .filter-heading {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex: 0 0 auto;
      margin-right: 2px;
    }}

    .filter-label {{
      font-size: 0.64rem;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      white-space: nowrap;
    }}

    .filter-actions {{
      display: inline-flex;
      align-items: center;
      gap: 0;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f7f4ef;
      padding: 0 2px;
      line-height: 1;
    }}

    .filter-action {{
      border: 0;
      background: transparent;
      color: var(--accent);
      font: inherit;
      font-size: 0.64rem;
      font-weight: 600;
      cursor: pointer;
      padding: 2px 7px;
      border-radius: 999px;
    }}

    .filter-action:hover {{
      background: rgba(212, 75, 38, 0.1);
    }}

    .filter-action-sep {{
      color: #c5beb4;
      font-size: 0.64rem;
      line-height: 1;
      user-select: none;
    }}

    .filter-buttons {{
      display: flex;
      flex-wrap: wrap;
      gap: 3px;
      flex: 1 1 auto;
      min-width: 0;
    }}

    .filter-trailing {{
      flex: 0 0 auto;
      margin-left: auto;
    }}

    .filter-btn {{
      border: 1px solid var(--line);
      background: #faf8f5;
      color: var(--ink);
      border-radius: 999px;
      padding: 1px 6px;
      font: inherit;
      font-size: 0.68rem;
      line-height: 1.35;
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

    .match-count {{
      font-size: 0.68rem;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      line-height: 1.35;
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
      transition: border-color 0.15s ease;
    }}

    .day-card:hover {{
      border-color: var(--accent);
    }}

    .day-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      padding: 10px 12px 7px;
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
      max-height: 200px;
      overflow: auto;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
    }}

    .cal-session {{
      display: block;
      padding: 6px 10px;
      text-decoration: none;
      color: inherit;
      border-top: 1px solid rgba(221, 215, 206, 0.65);
      font-size: 0.78rem;
    }}

    .cal-session:hover {{
      background: #faf8f5;
    }}

    .cal-time {{
      display: block;
      color: var(--muted);
      font-size: 0.7rem;
      line-height: 1.2;
      margin-bottom: 2px;
      font-variant-numeric: tabular-nums;
    }}

    .cal-title {{
      display: block;
      color: var(--ink);
      line-height: 1.3;
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

    .papers {{
      display: grid;
    }}

    .paper {{
      position: relative;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px 14px;
      align-items: start;
      padding: 16px 88px 16px 14px;
      border-top: 1px solid rgba(221, 215, 206, 0.8);
      transition: background 0.12s ease, box-shadow 0.12s ease;
    }}

    .paper:first-child {{ border-top: 0; }}
    .paper:hover {{ background: #fcfbfa; }}

    .paper.selected {{
      background: #fff8f4;
      box-shadow: inset 3px 0 0 var(--accent);
    }}

    .paper.selected:hover {{
      background: #fff4ed;
    }}

    .paper-media {{
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      gap: 10px;
    }}

    .select-talk {{
      order: -1;
      width: 28px;
      height: 28px;
      margin-top: 28px;
      border: 0;
      padding: 0;
      background: transparent;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      color: #b7b0a6;
      transition: color 0.12s ease, background 0.12s ease, transform 0.12s ease;
      flex: 0 0 auto;
    }}

    .select-talk:hover {{
      color: var(--accent);
      background: var(--accent-soft);
    }}

    .select-icon {{
      width: 20px;
      height: 20px;
      display: block;
    }}

    .select-check {{
      opacity: 0;
    }}

    .paper.selected .select-talk {{
      color: var(--accent);
    }}

    .paper.selected .select-ring {{
      fill: var(--accent);
      stroke: var(--accent);
    }}

    .paper.selected .select-plus {{
      opacity: 0;
    }}

    .paper.selected .select-check {{
      opacity: 1;
    }}

    .paper-body {{
      min-width: 0;
    }}

    .conflict-mark {{
      display: none;
      font-size: 0.92em;
      line-height: 1;
    }}

    .paper.conflict .conflict-mark {{
      display: inline;
    }}

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
      border: 0;
      padding: 0;
      background: transparent;
      cursor: pointer;
      transition: transform 0.12s ease, opacity 0.12s ease, box-shadow 0.12s ease;
    }}

    a.cal-add {{
      text-decoration: none;
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

    .schedule-tray {{
      position: fixed;
      left: 50%;
      bottom: 18px;
      transform: translateX(-50%) translateY(20px);
      z-index: 40;
      width: min(720px, calc(100vw - 24px));
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px 10px 16px;
      background: rgba(20, 32, 51, 0.96);
      color: white;
      border-radius: 16px;
      box-shadow: 0 16px 40px rgba(20, 32, 51, 0.28);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.18s ease, transform 0.18s ease;
    }}

    .schedule-tray.visible {{
      opacity: 1;
      pointer-events: auto;
      transform: translateX(-50%) translateY(0);
    }}

    .tray-copy {{
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }}

    .tray-count {{
      font-weight: 700;
      font-size: 0.92rem;
      letter-spacing: -0.01em;
    }}

    .tray-note {{
      font-size: 0.75rem;
      color: rgba(255,255,255,0.7);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .tray-note.warn {{
      color: #ffb4a2;
    }}

    .tray-actions {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex: 0 0 auto;
    }}

    .tray-btn {{
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(255,255,255,0.08);
      color: white;
      border-radius: 999px;
      padding: 7px 12px;
      font: inherit;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.12s ease, border-color 0.12s ease;
    }}

    .tray-btn:hover {{
      background: rgba(255,255,255,0.16);
    }}

    .tray-btn.active {{
      background: var(--accent);
      border-color: var(--accent);
    }}

    .tray-btn.icon-btn {{
      width: 36px;
      height: 36px;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
    }}

    .tray-btn.icon-btn svg {{
      width: 18px;
      height: 18px;
      display: block;
    }}

    .tray-btn.primary {{
      background: white;
      color: var(--navy);
      border-color: white;
    }}

    .tray-btn.primary:hover {{
      background: #f3efe9;
    }}

    .tray-btn.primary.copied {{
      background: #dff5e5;
      color: #1f6b3a;
      border-color: #dff5e5;
    }}

    .tray-btn.hidden {{
      display: none;
    }}

    .thumb {{
      width: 122px;
      height: 90px;
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
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      margin-bottom: 6px;
      font-size: 0.86rem;
      color: var(--muted);
    }}

    .paper-time-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}

    .paper-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}

    .paper-meta time {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-weight: 700;
      color: var(--accent);
      font-variant-numeric: tabular-nums;
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

    .authors .presenting {{
      color: var(--ink);
      text-decoration: underline;
      text-underline-offset: 2px;
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
      .calendar {{
        display: flex;
        gap: 10px;
        overflow-x: auto;
        overscroll-behavior-x: contain;
        scroll-snap-type: x mandatory;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 2px;
      }}

      .day-card {{
        flex: 0 0 min(72vw, 260px);
        scroll-snap-align: start;
      }}

      .day-card-sessions {{
        max-height: none;
        overflow: visible;
      }}
    }}

    @media (max-width: 640px) {{
      .page {{ padding-inline: 14px; }}
      .paper {{
        gap: 10px;
        padding-right: 72px;
        padding-left: 10px;
      }}
      .paper-media {{
        flex-direction: column;
        align-items: center;
        gap: 6px;
      }}
      .select-talk {{
        order: 0;
        width: 24px;
        height: 24px;
        margin-top: 0;
      }}
      .thumb {{ width: 64px; height: 48px; }}
      .session-header, .paper {{ padding-inline: 12px; }}
      .paper {{ padding-left: 10px; }}
      .paper-calendars {{ right: 8px; top: 10px; }}
      .schedule-tray {{
        bottom: 10px;
        flex-wrap: wrap;
        padding: 12px;
      }}
      .tray-actions {{
        width: 100%;
        justify-content: stretch;
      }}
      .tray-btn {{
        flex: 1 1 auto;
        text-align: center;
      }}
      .filter-trailing {{
        width: auto;
        margin-top: 0;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <h1>SIGGRAPH 2026 Technical Papers</h1>
      <p>Build your schedule by selecting papers and copying / sharing / saving to calendar.</p>
      <p>You can save either individual talks or the selected schedule to your calendar.</p>
      <div class="hero-downloads">
        <a href="{html.escape(CSV_PATH.name)}" download>Download CSV</a>
        <a href="{html.escape(JSON_PATH.name)}" download>Download JSON</a>
        <span class="timezone-note">All times in PDT</span>
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

  <div class="schedule-tray" id="schedule-tray" aria-live="polite">
    <div class="tray-copy">
      <div class="tray-count" id="tray-count">0 talks selected</div>
      <div class="tray-note hidden" id="tray-note"></div>
    </div>
    <div class="tray-actions">
      <button type="button" class="tray-btn" id="tray-show-selected">Show Selected</button>
      <button type="button" class="tray-btn icon-btn primary" id="tray-copy" title="Copy" aria-label="Copy">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"/><path fill="currentColor" d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"/></svg>
      </button>
      <button type="button" class="tray-btn icon-btn" id="tray-share" title="Share" aria-label="Share">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M2.75 14A1.75 1.75 0 0 1 1 12.25v-2.5a.75.75 0 0 1 1.5 0v2.5c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25v-2.5a.75.75 0 0 1 1.5 0v2.5A1.75 1.75 0 0 1 13.25 14Z"/><path fill="currentColor" d="M7.25 7.69V2.56l-1.97 1.97a.75.75 0 0 1-1.06-1.06l3.25-3.25a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1-1.06 1.06L8.75 2.56v5.13a.75.75 0 0 1-1.5 0Z"/></svg>
      </button>
      <button type="button" class="tray-btn icon-btn" id="tray-ics" title="Download .ics" aria-label="Download .ics">
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path fill="currentColor" d="M4.75 1a.75.75 0 0 0-.75.75V3H2.75A1.75 1.75 0 0 0 1 4.75v8.5C1 14.216 1.784 15 2.75 15h10.5A1.75 1.75 0 0 0 15 13.25v-8.5A1.75 1.75 0 0 0 13.25 3H12V1.75a.75.75 0 0 0-1.5 0V3h-5V1.75A.75.75 0 0 0 4.75 1ZM2.5 6v7.25c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25V6Z"/>
          <path fill="currentColor" d="M8 7.25a.75.75 0 0 1 .75.75v2.19l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 1 1 1.06-1.06l.72.72V8a.75.75 0 0 1 .75-.75Z"/>
        </svg>
      </button>
      <button type="button" class="tray-btn" id="tray-clear">Clear</button>
    </div>
  </div>

  <script>
    const STORAGE_KEY = 'siggraph2026-my-schedule';
    const search = document.getElementById('search');
    const clearFilters = document.getElementById('clear-filters');
    const matchCount = document.getElementById('match-count');
    const stickyShell = document.getElementById('sticky-shell');
    const filtersEl = document.getElementById('filters');
    const filtersToggle = document.getElementById('filters-toggle');
    const scheduleTray = document.getElementById('schedule-tray');
    const trayCount = document.getElementById('tray-count');
    const trayNote = document.getElementById('tray-note');
    const trayCopy = document.getElementById('tray-copy');
    const trayShare = document.getElementById('tray-share');
    const trayIcs = document.getElementById('tray-ics');
    const trayClear = document.getElementById('tray-clear');
    const trayShowSelected = document.getElementById('tray-show-selected');
    const papers = Array.from(document.querySelectorAll('.paper'));
    const sessions = Array.from(document.querySelectorAll('.session'));
    const days = Array.from(document.querySelectorAll('.day'));
    const filterButtons = Array.from(document.querySelectorAll('.filter-btn'));
    const filterActions = Array.from(document.querySelectorAll('.filter-action'));
    const paperById = new Map(papers.map(paper => [paper.dataset.paperId, paper]));

    let selectedIds = new Set();
    let showSelectedOnly = false;

    const COPY_ICON = trayCopy.innerHTML;
    let canShare = false;
    try {{
      canShare = typeof navigator.share === 'function'
        && (!navigator.canShare || navigator.canShare({{ text: 'test' }}));
    }} catch (error) {{
      canShare = typeof navigator.share === 'function';
    }}
    if (!canShare) {{
      trayShare.classList.add('hidden');
    }}

    function normalize(value) {{
      return (value || '').toLowerCase().trim();
    }}

    function splitTopics(value) {{
      return (value || '').split('|').map(item => item.trim()).filter(Boolean);
    }}

    function formatDayHeading(dateStr) {{
      const date = new Date(`${{dateStr}}T12:00:00`);
      return date.toLocaleDateString('en-US', {{
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      }});
    }}

    function loadSelection() {{
      try {{
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        if (Array.isArray(saved)) {{
          selectedIds = new Set(saved.filter(id => paperById.has(id)));
        }}
      }} catch (error) {{
        selectedIds = new Set();
      }}
    }}

    function saveSelection() {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(selectedIds)));
    }}

    function selectedPapers() {{
      return Array.from(selectedIds)
        .map(id => paperById.get(id))
        .filter(Boolean)
        .sort((a, b) => (a.dataset.start || '').localeCompare(b.dataset.start || '')
          || (a.dataset.paperId || '').localeCompare(b.dataset.paperId || ''));
    }}

    function timesOverlap(a, b) {{
      const aStart = a.dataset.start || '';
      const aEnd = a.dataset.end || '';
      const bStart = b.dataset.start || '';
      const bEnd = b.dataset.end || '';
      return Boolean(aStart && aEnd && bStart && bEnd && aStart < bEnd && bStart < aEnd);
    }}

    function conflictingPaperIds(items) {{
      const conflicted = new Set();
      for (let i = 0; i < items.length; i += 1) {{
        for (let j = i + 1; j < items.length; j += 1) {{
          if (timesOverlap(items[i], items[j])) {{
            conflicted.add(items[i].dataset.paperId);
            conflicted.add(items[j].dataset.paperId);
          }}
        }}
      }}
      return conflicted;
    }}

    function countConflicts(items) {{
      let conflicts = 0;
      for (let i = 0; i < items.length; i += 1) {{
        for (let j = i + 1; j < items.length; j += 1) {{
          if (timesOverlap(items[i], items[j])) conflicts += 1;
        }}
      }}
      return conflicts;
    }}

    function togglePaper(paper) {{
      const id = paper.dataset.paperId;
      if (!id) return;
      if (selectedIds.has(id)) {{
        selectedIds.delete(id);
      }} else {{
        selectedIds.add(id);
      }}
      if (selectedIds.size === 0) {{
        showSelectedOnly = false;
      }}
      saveSelection();
      updateSelectionUI();
      applyFilters();
    }}

    function buildMarkdown() {{
      const items = selectedPapers();
      if (!items.length) return '';

      const conflicted = conflictingPaperIds(items);
      const lines = [];
      let currentDay = '';
      let currentSessionKey = '';

      items.forEach(paper => {{
        const day = paper.dataset.date || '';
        const session = paper.dataset.session || '';
        const room = paper.dataset.room || '';
        const sessionKey = day + '||' + session + '||' + room;

        if (day !== currentDay) {{
          if (currentDay) lines.push('');
          lines.push(`## ${{formatDayHeading(day)}}`, '');
          currentDay = day;
          currentSessionKey = '';
        }}

        if (sessionKey !== currentSessionKey) {{
          if (currentSessionKey) lines.push('');
          if (session) lines.push(session);
          if (room) lines.push(room);
          currentSessionKey = sessionKey;
        }}

        const title = paper.dataset.title || '';
        const time = paper.dataset.time || '';
        const conflictNote = conflicted.has(paper.dataset.paperId) ? ' [conflict]' : '';
        // Two trailing spaces = Markdown hard line break within the list item
        lines.push(`- ${{title}}  `);
        lines.push(`  ${{time}}${{conflictNote}}`);
      }});

      lines.push('');
      return lines.join('\\n');
    }}

    function icsEscape(value) {{
      return String(value || '')
        .replace(/\\\\/g, '\\\\\\\\')
        .replace(/;/g, '\\\\;')
        .replace(/,/g, '\\\\,')
        .replace(/\\n/g, '\\\\n');
    }}

    function formatIcsDate(isoTime) {{
      return String(isoTime || '')
        .replace(/\\.\\d+(?=Z|$)/, '')
        .replace(/[-:]/g, '');
    }}

    function buildEventLines(paper) {{
      const uid = `${{paper.dataset.paperId || 'talk'}}@siggraph2026-schedule`;
      const stamp = formatIcsDate(new Date().toISOString());
      const start = formatIcsDate(paper.dataset.start);
      const end = formatIcsDate(paper.dataset.end);
      const title = icsEscape(paper.dataset.title);
      const location = icsEscape(paper.dataset.room);
      const description = icsEscape(
        [
          paper.dataset.authors ? `Authors: ${{paper.dataset.authors}}` : '',
          paper.dataset.session ? `Session: ${{paper.dataset.session}}` : '',
        ].filter(Boolean).join('\\n')
      );
      return [
        'BEGIN:VEVENT',
        `UID:${{uid}}`,
        `DTSTAMP:${{stamp}}`,
        `DTSTART:${{start}}`,
        `DTEND:${{end}}`,
        `SUMMARY:${{title}}`,
        `LOCATION:${{location}}`,
        `DESCRIPTION:${{description}}`,
        'END:VEVENT',
      ];
    }}

    function buildCalendarIcs(paperList) {{
      const events = paperList.flatMap(buildEventLines);
      return [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//SIGGRAPH 2026 Technical Papers//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:My SIGGRAPH 2026 Schedule',
        ...events,
        'END:VCALENDAR',
        '',
      ].join('\\r\\n');
    }}

    function downloadIcsBlob(ics, filename) {{
      const link = document.createElement('a');
      link.download = filename;
      link.rel = 'noopener';
      link.style.display = 'none';
      document.body.appendChild(link);

      try {{
        const blob = new Blob([ics], {{ type: 'text/calendar;charset=utf-8' }});
        const url = URL.createObjectURL(blob);
        link.href = url;
        link.click();
        window.setTimeout(() => {{
          URL.revokeObjectURL(url);
          link.remove();
        }}, 2000);
      }} catch (error) {{
        link.href = 'data:text/calendar;charset=utf-8,' + encodeURIComponent(ics);
        link.click();
        link.remove();
      }}
    }}

    function downloadPaperIcs(paper) {{
      const safeTitle = (paper.dataset.title || 'siggraph-paper')
        .replace(/[^\\w\\s-]+/g, '')
        .trim()
        .replace(/[-\\s]+/g, '-')
        .slice(0, 60) || 'siggraph-paper';
      downloadIcsBlob(buildCalendarIcs([paper]), `${{safeTitle}}.ics`);
    }}

    function downloadScheduleIcs() {{
      const items = selectedPapers();
      if (!items.length) return;
      downloadIcsBlob(buildCalendarIcs(items), 'siggraph-2026-my-schedule.ics');
    }}

    async function copyMarkdown() {{
      const markdown = buildMarkdown();
      if (!markdown) return;
      try {{
        await navigator.clipboard.writeText(markdown);
      }} catch (error) {{
        const area = document.createElement('textarea');
        area.value = markdown;
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
      }}
      trayCopy.classList.add('copied');
      trayCopy.title = 'Copied!';
      window.setTimeout(() => {{
        trayCopy.classList.remove('copied');
        trayCopy.title = 'Copy';
        trayCopy.innerHTML = COPY_ICON;
      }}, 1600);
    }}

    async function shareMarkdown() {{
      const markdown = buildMarkdown();
      if (!markdown || !canShare) return;
      try {{
        // Share text only — a title gets prepended on Copy/share sheets (e.g. macOS/iOS).
        await navigator.share({{ text: markdown }});
      }} catch (error) {{
        if (error && error.name === 'AbortError') return;
        await copyMarkdown();
      }}
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
      return allButtonsActive('keyword') && allButtonsActive('room') && !normalize(search.value) && !showSelectedOnly;
    }}

    function updateClearFiltersButton() {{
      clearFilters.classList.toggle('active', !filtersAreDefault());
    }}

    function updateStickyOffset() {{
      const offset = stickyShell.offsetHeight + 16;
      document.documentElement.style.setProperty('--sticky-offset', `${{offset}}px`);
    }}

    function paperMatchesFilters(paper) {{
      if (showSelectedOnly) {{
        return selectedIds.has(paper.dataset.paperId);
      }}
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
        let visible;
        if (showSelectedOnly) {{
          visible = selectedIds.has(paper.dataset.paperId);
        }} else {{
          const haystack = paper.dataset.search || '';
          const searchMatch = !query || haystack.includes(query);
          const filterMatch = paperMatchesFilters(paper);
          visible = searchMatch && filterMatch;
        }}
        paper.classList.toggle('hidden', !visible);
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

    function updateSelectionUI() {{
      const items = selectedPapers();
      const conflicted = conflictingPaperIds(items);

      papers.forEach(paper => {{
        const selected = selectedIds.has(paper.dataset.paperId);
        paper.classList.toggle('selected', selected);
        paper.classList.toggle('conflict', conflicted.has(paper.dataset.paperId));
        const button = paper.querySelector('.select-talk');
        if (button) {{
          button.setAttribute('aria-pressed', selected ? 'true' : 'false');
          button.setAttribute(
            'aria-label',
            selected ? 'Remove from my schedule' : 'Add to my schedule'
          );
          button.title = selected ? 'Remove from my schedule' : 'Add to my schedule';
        }}
      }});

      const count = items.length;
      scheduleTray.classList.toggle('visible', count > 0);
      document.body.style.paddingBottom = count > 0 ? '88px' : '';
      trayCount.textContent = count === 1 ? '1 talk selected' : `${{count}} talks selected`;

      const conflicts = countConflicts(items);
      if (conflicts > 0) {{
        trayNote.textContent = conflicts === 1
          ? '1 time conflict in your picks'
          : `${{conflicts}} time conflicts in your picks`;
        trayNote.classList.add('warn');
        trayNote.classList.remove('hidden');
      }} else {{
        trayNote.textContent = '';
        trayNote.classList.remove('warn');
        trayNote.classList.add('hidden');
      }}

      trayShowSelected.classList.toggle('active', showSelectedOnly);
    }}

    papers.forEach(paper => {{
      const button = paper.querySelector('.select-talk');
      if (!button) return;
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        togglePaper(paper);
      }});
    }});

    document.querySelectorAll('[data-ics-download]').forEach(button => {{
      button.addEventListener('click', event => {{
        event.preventDefault();
        event.stopPropagation();
        const paper = button.closest('.paper');
        if (paper) downloadPaperIcs(paper);
      }});
    }});

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
      showSelectedOnly = false;
      setGroupState('keyword', true);
      setGroupState('room', true);
      updateSelectionUI();
    }});

    trayShowSelected.addEventListener('click', () => {{
      showSelectedOnly = !showSelectedOnly;
      updateSelectionUI();
      applyFilters();
    }});

    trayCopy.addEventListener('click', copyMarkdown);
    trayShare.addEventListener('click', shareMarkdown);
    trayIcs.addEventListener('click', downloadScheduleIcs);

    trayClear.addEventListener('click', () => {{
      selectedIds.clear();
      showSelectedOnly = false;
      saveSelection();
      updateSelectionUI();
      applyFilters();
    }});

    search.addEventListener('input', applyFilters);

    filtersToggle.addEventListener('click', () => {{
      const collapsed = filtersEl.classList.toggle('collapsed');
      filtersToggle.textContent = collapsed ? 'Show' : 'Hide';
      filtersToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      updateStickyOffset();
    }});

    window.addEventListener('load', updateStickyOffset);
    window.addEventListener('resize', updateStickyOffset);

    loadSelection();
    updateSelectionUI();
    updateStickyOffset();
    applyFilters();
  </script>
</body>
</html>
"""


def main():
    with JSON_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    content = generate_html(data)
    HTML_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {HTML_PATH} ({HTML_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
