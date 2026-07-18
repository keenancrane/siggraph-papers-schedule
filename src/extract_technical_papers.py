#!/usr/bin/env python3
"""Extract SIGGRAPH 2026 technical paper presentations from saved schedule HTML."""

import csv
import json
import re
from html import unescape

from bs4 import BeautifulSoup

HTML_PATH = "schedule.html"
CSV_PATH = "technical_papers_2026.csv"
JSON_PATH = "technical_papers_2026.json"
SOURCE_URL = "https://s2026.conference-schedule.org/"


def clean_text(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))


def parse_people(container):
    people = []
    if container is None:
        return people
    for div in container.find_all(
        "div", class_=lambda c: c and "presenter-details" in c.split()
    ):
        is_presenting = (
            "presenting" in div.get("class", [])
            and "not-presenting" not in div.get("class", [])
        )
        anchor = div.find("a", href=True)
        if not anchor:
            continue
        uid_match = re.search(r"uid=(\d+)", anchor["href"])
        people.append(
            {
                "name": clean_text(anchor),
                "uid": uid_match.group(1) if uid_match else "",
                "url": unescape(anchor["href"].replace("&amp;", "&")),
                "presenting": is_presenting,
            }
        )
    return people


def parse_program_tracks(container):
    tracks = []
    if container is None:
        return tracks
    for pt in container.find_all("div", class_=lambda c: c and "program-track" in c.split()):
        track_id = next((x for x in pt.get("class", []) if x.startswith("ptrack")), None)
        if track_id:
            tracks.append(
                {
                    "id": track_id,
                    "name": clean_text(pt),
                }
            )
    return tracks


def parse_tag_groups(container, label_class):
    tags = []
    if container is None:
        return tags
    for tg in container.find_all(class_=lambda c: c and label_class in c.split()):
        tags.append(clean_text(tg))
    return tags


def get_time_info(row):
    info = {}
    time_td = row.find("td", class_="presentation-time-td") or row
    start = time_td.find("span", class_="start-time")
    end = time_td.find("span", class_="end-time")
    tz = time_td.find("span", class_="timezone")
    if start:
        info["start_time_utc"] = start.get("utc_time", "")
        info["start_time_display"] = clean_text(start)
    if end:
        info["end_time_utc"] = end.get("utc_time", "")
        info["end_time_display"] = clean_text(end)
    if tz:
        info["timezone"] = clean_text(tz)
    return info


def parse_session_header(tr, ptrack_map, etype_map):
    track_ids = tr.get("ptracks", "").split() if tr.get("ptracks") else []
    data = {
        "session_id": tr.get("psid", ""),
        "session_start_utc": tr.get("s_utc", ""),
        "session_end_utc": tr.get("e_utc", ""),
        "session_event_type_id": tr.get("etypes", ""),
        "session_event_type": etype_map.get(tr.get("etypes", ""), tr.get("etypes", "")),
        "session_room_id": tr.get("room", ""),
        "session_track_ids": track_ids,
        "session_tracks": [ptrack_map.get(track_id, track_id) for track_id in track_ids],
    }
    type_td = tr.find("td", class_="type-td")
    if type_td:
        data["session_type_display"] = clean_text(type_td)

    combo = tr.find("td", class_="combo-sess-pres")
    if combo:
        data["session_title"] = clean_text(combo)

    session_times = get_time_info(tr)
    data["session_start_time_display"] = session_times.get("start_time_display", "")
    data["session_end_time_display"] = session_times.get("end_time_display", "")
    data["session_timezone"] = session_times.get("timezone", "")

    loc_td = tr.find("td", class_="location-td")
    if loc_td:
        ploc = loc_td.find(class_="presentation-location")
        data["session_room"] = clean_text(ploc) if ploc else clean_text(loc_td)

    tag_td = tr.find("td", class_="full-tag-td")
    if tag_td:
        data["session_tracks_display"] = parse_program_tracks(tag_td)
        data["session_keywords"] = parse_tag_groups(tag_td, "keyword")
        data["session_registration_categories"] = parse_tag_groups(
            tag_td, "registration-category"
        )

    return data


def parse_session_chairs(container):
    chairs = []
    if container is None:
        return chairs
    for anchor in container.find_all("a", href=True):
        uid_match = re.search(r"uid=(\d+)", anchor["href"])
        chairs.append(
            {
                "name": clean_text(anchor),
                "uid": uid_match.group(1) if uid_match else "",
                "url": unescape(anchor["href"].replace("&amp;", "&")),
                "presenting": False,
            }
        )
    return chairs


def parse_session_slidedown(tr):
    chairs_sect = tr.find(class_="session-chairs-list-sect")
    return {"session_chairs": parse_session_chairs(chairs_sect) if chairs_sect else []}


def is_technical_paper_session(session_data):
    if session_data.get("session_event_type_id") == "sstype132":
        return True
    return "Technical Paper" in session_data.get("session_type_display", "")


def parse_paper_row(tr, session_data, date):
    ssid = tr.get("ssid", "")
    prefix, num = ssid.split("_", 1) if "_" in ssid else ("", ssid)
    title_td = tr.find("td", class_="title-speakers-td")
    title_a = title_td.find("a", href=True) if title_td else None
    authors_div = title_td.find(class_="author") if title_td else None
    img = tr.find("img", class_="representative-img")
    tag_td = tr.find(
        "td",
        class_=lambda c: c and "hide-med" in c.split() and "hide-small" in c.split(),
    )
    ical = tr.find("a", class_="ical-link")

    authors = parse_people(authors_div) if authors_div else []
    tracks = parse_program_tracks(tag_td)
    keywords = parse_tag_groups(tag_td, "keyword")
    reg_cats = parse_tag_groups(tag_td, "registration-category")

    return {
        "date": date,
        "paper_id": ssid,
        "paper_category": "TOG Journal Paper" if prefix == "paperstog" else "Conference Paper",
        "paper_number": num,
        "presentation_start_utc": tr.get("s_utc", ""),
        "presentation_end_utc": tr.get("e_utc", ""),
        **get_time_info(tr),
        "title": clean_text(title_a) if title_a else clean_text(title_td),
        "url": unescape(title_a["href"].replace("&amp;", "&")) if title_a else "",
        "data_link_type": title_a.get("data-link-type", "") if title_a else "",
        "calendar_url": unescape(ical["href"].replace("&amp;", "&")) if ical else "",
        "authors": authors,
        "authors_all": "; ".join(person["name"] for person in authors),
        "authors_presenting": "; ".join(
            person["name"] for person in authors if person["presenting"]
        ),
        "authors_not_presenting": "; ".join(
            person["name"] for person in authors if not person["presenting"]
        ),
        "tracks": tracks,
        "track_names": "; ".join(track["name"] for track in tracks),
        "keywords": keywords,
        "keywords_list": "; ".join(keywords),
        "registration_categories": reg_cats,
        "registration_categories_list": "; ".join(reg_cats),
        "representative_image": img.get("src", "") if img else "",
        **session_data,
    }


def flatten_paper(paper):
    nested_keys = {
        "authors",
        "tracks",
        "keywords",
        "registration_categories",
        "session_tracks_display",
        "session_chairs",
        "session_track_ids",
        "session_tracks",
        "session_keywords",
        "session_registration_categories",
    }
    flat = {key: value for key, value in paper.items() if key not in nested_keys}
    flat["authors_json"] = json.dumps(paper["authors"], ensure_ascii=False)
    flat["tracks_json"] = json.dumps(paper["tracks"], ensure_ascii=False)
    flat["session_chairs"] = "; ".join(
        chair["name"] for chair in paper.get("session_chairs", [])
    )
    flat["session_track_ids"] = "; ".join(paper.get("session_track_ids", []))
    flat["session_tracks"] = "; ".join(paper.get("session_tracks", []))
    flat["session_keywords_list"] = "; ".join(paper.get("session_keywords", []))
    flat["session_registration_categories_list"] = "; ".join(
        paper.get("session_registration_categories", [])
    )
    return flat


def extract_papers(html):
    soup = BeautifulSoup(html, "lxml")

    ptrack_map = {}
    etype_map = {}
    for opt in soup.find_all("option"):
        val = opt.get("value", "")
        text = opt.get_text(strip=True)
        if val.startswith("ptrack"):
            ptrack_map[val] = text
        elif val.startswith("sstype"):
            etype_map[val] = text

    papers = []
    sessions_cache = {}

    for date_div in soup.find_all("div", class_=lambda c: c and "date-disp" in c.split()):
        date = None
        for cls in date_div.get("class", []):
            if re.match(r"\d{4}-\d{2}-\d{2}", cls):
                date = cls
                break
        if not date:
            tablesched = date_div.find("div", class_="tablesched")
            if tablesched:
                date = tablesched.get("date", "")
        if not date:
            continue

        table = date_div.find("table")
        if not table:
            continue

        current_session = {}
        for tr in table.find_all("tr", recursive=True):
            classes = tr.get("class", [])

            if "primary-session" in classes and tr.get("psid"):
                current_session = parse_session_header(tr, ptrack_map, etype_map)
                if not is_technical_paper_session(current_session):
                    current_session = {}
                else:
                    sessions_cache[current_session["session_id"]] = dict(current_session)

            session_id = current_session.get("session_id")
            if (
                current_session
                and "slots-slidedown" in classes
                and session_id
                and session_id in classes
            ):
                slidedown = parse_session_slidedown(tr)
                current_session.update(slidedown)
                sessions_cache[session_id].update(slidedown)

            ssid = tr.get("ssid", "")
            if current_session and re.match(r"^(papers|paperstog)_\d+$", ssid):
                session_data = sessions_cache.get(tr.get("psid", ""), current_session)
                papers.append(parse_paper_row(tr, session_data, date))

    papers.sort(key=lambda paper: (paper.get("presentation_start_utc", ""), paper.get("paper_id", "")))
    return papers


def main():
    with open(HTML_PATH, "r", encoding="utf-8") as handle:
        html = handle.read()

    papers = extract_papers(html)
    flat_papers = [flatten_paper(paper) for paper in papers]

    all_keys = []
    seen = set()
    for flat in flat_papers:
        for key in flat:
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat_papers)

    output = {
        "source": SOURCE_URL,
        "extracted_at": "2026-07-18",
        "timezone_note": "Times shown in America/Los_Angeles (PDT)",
        "total_papers": len(papers),
        "conference_papers": sum(
            1 for paper in papers if paper["paper_category"] == "Conference Paper"
        ),
        "tog_journal_papers": sum(
            1 for paper in papers if paper["paper_category"] == "TOG Journal Paper"
        ),
        "papers": papers,
    }

    with open(JSON_PATH, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)

    print(f"Extracted {len(papers)} technical paper presentations")
    print(f"Wrote {CSV_PATH} and {JSON_PATH}")


if __name__ == "__main__":
    main()
