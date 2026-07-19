# AGENTS.md — SIGGRAPH 2026 Technical Papers Schedule

Guidelines for agents working on this project. Prefer these over improvising conflicting UX or workflow choices.

## Purpose

Build a **flat, self-contained, highly scannable** schedule of SIGGRAPH 2026 **technical paper** presentations that is clearer and more searchable than the official ACM / Linklings schedule.

Primary user job: **build a personal schedule** by selecting talks, then **copy / share / save to calendar**.

## Source of truth & workflow

- **Ship / iterate on `index.html` only.** Do not create or maintain `technical_papers_schedule.html` or other duplicate schedule pages.
- Data files:
  - `technical_papers_2026.json`
  - `technical_papers_2026.csv`
- Regenerators (when needed):
  - `extract_technical_papers.py` — parse saved `schedule.html` → JSON/CSV
  - `generate_schedule_page.py` — JSON → `index.html`
- Prefer editing `generate_schedule_page.py` and regenerating `index.html`, unless the user asks to edit `index.html` directly for a quick one-off.
- Keep CSV/JSON download links in the hero pointing at the year-suffixed filenames above.

## What belongs in the schedule

- **Include only technical paper presentations** (`papers_*` conference papers and `paperstog_*` TOG journal papers).
- **Ignore** courses, panels, talks, BoFs, CAF, posters-as-non-papers, `misc_*` session fillers, etc.
- Order chronologically by presentation start time (ties may break arbitrarily).

## Product / UX principles

### Always flat — no folds

- **No collapsed or collapsible UI** for schedule content (no `<details>` disclosure for days/sessions/papers).
- Exception: the sticky **Filters** panel may Hide/Show (toggle next to the Filters title) so the schedule can reclaim vertical space.
- One of the main promises of this page vs. the ACM site: **all information is bare, exposed, and easily searchable**.
- Nested scroll regions that trap page scrolling (especially on mobile) are a UX failure — avoid them on small screens. Horizontal swipe through day cards with **fully visible** session lists is fine.

### Scannable & low clutter

- Optimize for humans quickly scanning, not for dumping every CSV column.
- Do **not** repeat redundant author splits (e.g. authors + presenting + not-presenting as separate lists). Prefer one author line with presenters underlined.
- Omit registration categories, internal IDs, TOG labels, and other TMI from the main UI.
- No hover tooltips on paper rows (keywords/tracks are already shown as chips when useful).
- Be thoughtful about what’s always visible vs. omitted.
- Prefer best-practice UI/UX: tighten layout without sacrificing legibility or aesthetic quality.

### Layout structure

1. **Hero** — brand/title, what you can do, calendar note, filter tip, CSV/JSON downloads, “All times in PDT”, and a static QR code for the shareable GitHub Pages URL (top-right on desktop; centered below on mobile). No useless stats (e.g. “345 papers / 4 days”).
2. **Calendar overview** — day cards with session times; click day/session to jump via anchors. **Not sticky.**
3. **Sticky filters** — search + keywords + rooms; compact; Hide/Show. Include “↑ Calendar” to jump back up.
4. **Linear schedule** — day → session → papers (always expanded).
5. **Selection tray** — appears only when ≥1 talk is selected (keeps the page clean otherwise).

### Filters

- Keywords and rooms default to **all on**.
- Compact **search** lives inside the Filters body (above keyword/room chips); Hide/Show collapses it with the chips.
- **Hide / Show** toggle immediately after the Filters title collapses the keyword/room chip groups (keeps ↑ Calendar + Clear). Recalculate sticky offset on toggle. On mobile (≤640px), filters start **hidden**.
- Each group has compact **`[ All | None ]`** controls immediately after the section label, visually demarcated from chips.
- Filter-only abbreviations (do **not** change paper row labels):
  - `Artificial Intelligence/Machine Learning` → `AI/ML`
  - `Virtual Reality` → `VR`
  - `Room 403 A` → `403 A` (etc.)
- Full names remain in `data-filter-value` / tooltips for matching.
- Match count (`N of Y papers`) lives in the Rooms row (bottom-right), not its own bar.
- **Show Selected** bypasses keyword, room, and search filters so the full personal schedule is always visible; turning it off restores normal filtering with prior filter state intact.
- **Clear** resets search + filters to the default all-on state (and clears Show Selected).

### Calendar links (per paper)

- **Google Calendar** — template URL (`calendar/render?action=TEMPLATE`).
- **Apple / Outlook** — generate `.ics` **locally in the browser**. Do not hotlink SIGGRAPH `get_cal.php` URLs (they return 403 from other origins).
- Use small identifiable icons; tooltips for accessibility.

### Personal schedule builder

- Minimal select control per paper (add/remove); selected state should be obvious but not noisy.
- Persist selections in `localStorage`.
- Selection tray actions:
  - **Show Selected**
  - **Copy** (icon; tooltip “Copy”) — Markdown, chronological, **no URLs**, no authors, no title H1
  - **Share** (icon; up-arrow share glyph; tooltip “Share”) — Web Share API with **text only** (no title — titles get prepended on Copy sheets); hide when unsupported; clipboard fallback on failure
  - **Download .ics** (calendar+download icon; tooltip “Download .ics”) — one multi-event `.ics` for the whole selection
  - **Clear**
- Warn about time conflicts among selected talks when relevant.
- Prefix conflicting talk times with ⚠️ in the schedule UI (whenever those talks are selected).
- In copied/shared Markdown, append ` [conflict]` after the time for conflicting talks.
- Markdown format: `## Day` headings; within each day, session title + room line, then a list of selected talks. Each talk is one list item: title (trailing spaces for hard break) then time on the next line. No bold/italic, no authors.

### Assets & self-containment

- Page should be self-contained (embedded CSS/JS/QR SVG) except **representative images**, which load from:
  `https://s2026.conference-schedule.org/wp-content/linklings_snippets/representative_images/…`
- Shareable-site QR lives in `qr-schedule.svg` and is inlined into the hero at generate time (points at `https://keenancrane.github.io/siggraph-papers-schedule/`).
- Do not assume local thumbnail paths from the saved `schedule.html` bundle.

### Mobile

- Filters stay sticky but compact so papers remain usable.
- Calendar: horizontal swipe of day cards; no nested vertical scroll traps; full session lists visible.
- Page scrolling must feel natural.

## Implementation notes

- Prefer changing `generate_schedule_page.py` then running:
  ```bash
  .venv/bin/python3 generate_schedule_page.py
  ```
- After generator changes, verify the **generated** `index.html` actually contains the new behavior (listeners, copy, etc.) — stale or dual-output mistakes have bitten us before.
- Times displayed to users are PDT; keep UTC in data attributes for calendars / sorting.

## Out of scope / don’t do

- Don’t reintroduce accordion/collapse “folds” for schedule browsing (Filters Hide/Show is the only allowed collapse).
- Don’t add Google Calendar API / OAuth unless explicitly requested.
- Don’t regenerate or keep parallel schedule HTML filenames.
- Don’t expand scope to non–technical-paper program tracks unless asked.
