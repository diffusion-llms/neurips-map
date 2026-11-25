# NeurIPS 2026 Discrete Diffusion Map

An interactive guide to every discrete diffusion paper, tutorial and workshop at NeurIPS 2026, across the Sydney main venue and the Atlanta and Paris satellites.

The site is a single static page: `docs/index.html`. Open it in a browser, or serve it with GitHub Pages (Settings → Pages → deploy from branch, folder `/docs`). Its look is adapted from the [Principles of Diffusion Models tutorial site](https://d-llms.com/neurips26/).

## What's on the page

- **Schedule** (the landing view): a week grid by venue (in each venue's local dates), then a day-by-day list of every poster session, oral session, tutorial and workshop that has discrete diffusion content, with poster board numbers.
- **Papers**: 223 papers: 177 on discrete diffusion itself and 46 on neighbouring work, such as continuous diffusion for text, listed together. Search across titles, authors, affiliations and abstracts. Filter by venue, format (orals, spotlights), topic and method tag. Each card shows a one-line summary, the poster session, board number and oral slot, with links to OpenReview, the NeurIPS page and code.
- **Tutorials & workshops**: the tutorial *The Principles of Diffusion Models: Toward Fast and Scalable Diffusion LLMs*, the two dedicated workshops (*Diffusion Language Models* and *Beyond Next Token Prediction*) and four adjacent events.
- **My agenda**: star papers and events to get a time-ordered personal schedule with overlaps flagged. Stars are kept in the browser's local storage.

All times can be shown in venue time (AEDT, EST, CET) or in the viewer's own time zone.

## How it is built

```
scripts/fetch_data.py   download raw data from neurips.cc into data/raw/ (git-ignored)
scripts/build.py        merge the data and classifications, render docs/index.html
site/template.html      the page: HTML, CSS and JS with a /*__DATA__*/ slot
```

```bash
python3 scripts/fetch_data.py   # ~2 min; the Downloads export is generated on request
python3 scripts/build.py        # standard library only
```

Data sources, both public:

1. `neurips.cc/static/virtual/data/neurips-2026-orals-posters.json`: sessions, times, rooms, poster boards, decisions, OpenReview and code links.
2. The `neurips.cc/Downloads/2026` export: abstracts, plus author and organizer lists for tutorials and workshops.

### Which papers are included

All 9,142 accepted papers were screened. A keyword filter over titles and abstracts kept 668 candidates. Each candidate abstract was then read and labelled by a model as:

- `core`: discrete diffusion is a main object of the paper.
- `related`: neighbouring work, such as continuous diffusion for text or non-autoregressive generation.
- `exclude`: everything else.

The site lists `core` and `related` papers together; `exclude` papers are left out.

Each included paper also gets a topic, method tags and a one-line summary. The results are in `data/classification.json`.

Those labels are model-assisted and can be wrong. To correct one, add an entry to `data/overrides.json` and rebuild:

```json
{ "123456": { "rel": "core", "cat": "sampling", "tldr": "..." } }
```

To feature another workshop or tutorial, add it to `data/events_config.json`, then run `fetch_data.py events` and `build.py`.

### Files

| Path | What it is |
|---|---|
| `docs/index.html` | The built site, self-contained apart from Google Fonts |
| `data/papers.json` | Included papers with schedule, links, topic, tags and summary |
| `data/classification.json` | Per-candidate labels from the screening pass |
| `data/overrides.json` | Hand corrections, applied on top of the labels |
| `data/events_config.json` | Featured tutorials and workshops, and their venues |
| `data/site_meta.json` | Venue dates, phases and topic names |

Times and rooms come from the official programme as of the build date. The NeurIPS site remains the source of truth.
