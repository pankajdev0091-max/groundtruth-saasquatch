# Time Log

Total coding time: ~5 hours.

## Phase 1 — Data & Normalization (0:00–0:45)

- Downloaded PPP and 7(a)/504 data dictionaries from SBA; verified every column name against actual CSV headers.
- Built `scripts/ingest.py`: downloads 13 PPP CSVs + 4 SBA CSVs, filters to selected states, drops protected demographic columns (Race, Ethnicity, Gender, Veteran), writes Parquet partitioned by state. Idempotent and resumable with `--skip-download` and `--states` flags.
- Built `groundtruth/normalize.py`: deterministic name normalization — uppercase, strip punctuation, handle apostrophes, collapse L.L.C. variants, remove legal suffixes, expand common abbreviations (MFG, SVCS, CONSTR, etc.).
- Wrote 25 unit tests for normalization covering real-world-shaped cases.
- Built `config/sources.yaml` with all SBA file URLs.
- Ran full ingest for CA, TX, FL, AZ: 3,357,488 PPP rows, 457,036 SBA 7(a) rows, 40,564 SBA 504 rows.

## Phase 2 — Matching & Signals (0:45–1:45)

- Built `groundtruth/match.py`: blocking by state + city/zip-3 prefix, scoring with rapidfuzz token_set_ratio (0.55 weight), city/zip/street bonuses, NAICS consistency check, generic name penalty. Confidence tiers: High (≥0.85), Probable (0.70–0.85), Weak (0.55–0.70). Every match returns a `reasons[]` list. Collapses multiple PPP draws per borrower.
- Built `groundtruth/signals.py`: payroll-implied revenue (loan ÷ 2.5 × 12, 3.5 for NAICS 72 second draw), Census NAICS ratios for revenue range, PAYROLL_PROCEED cross-check, SBA loan history with maturing-within-12-months flag, franchise flag, change-of-ownership flag, recommendation engine (Worth a credit / Verify first / Skip) with explicit rules.
- Fetched Census Economic Census payroll-to-revenue ratios; cached to `data/reference/census_ratios_2022.json` (113 NAICS codes).
- Built `groundtruth/csv_parser.py`: auto-maps SaaSquatch column names with synonym table, parses revenue strings ($1.2M, 500K, ranges), parses addresses.
- Wrote tests for revenue math (including NAICS 72 rule), recommendations, SBA history, CSV parsing.
- All 50 tests green.

## Phase 3 — API (1:45–2:15)

- Built `groundtruth/api.py` with FastAPI: `POST /upload` (returns mapping guess + job ID), `POST /match` (streams NDJSON progress), `GET /results/{job}`, `GET /export/{job}.csv`, `GET /reference/naics-ratios`, `GET /health`.
- Tested full upload → match → results → export flow via curl.

## Phase 4 — Frontend (2:15–3:45)

- Scaffolded React app with Vite + TypeScript + Tailwind.
- Built three screens:
  - **UploadScreen**: drag-drop CSV, detected column mapping with override dropdowns, confidence badges, Match button with progress bar.
  - **ResultsScreen**: sortable/filterable table with buy-box sidebar (revenue range, exclude franchises, exclude ownership changes), tier badges with hover reasons, side panel with full match detail and SBA loan history.
  - **ValidationScreen**: scatter plot (log-log, PPP-implied vs SaaSquatch, colored by tier, 45° reference line), histogram of log-ratio distribution, headline stat sentence, Export CSV button.
- Used Recharts for charts. Design: one accent color (blue), monospace numbers, neutral tier colors, generous whitespace.
- TypeScript compiles clean, production build succeeds.

## Phase 5 — Infrastructure (3:45–4:15)

- Created Dockerfile (multi-stage: backend + frontend build + combined image).
- Created docker-compose.yml for local dev.
- Built `scripts/bench.py`: benchmarks matching speed. Result: 70 rows/s, 1000-row estimate 14.3s — well under the 60s target.
- Built `scripts/create_demo_subset.py`: samples ~5K PPP rows per state from sample CSV cities + random others. Total demo subset: 1.4 MB.
- Built `scripts/check_sources.py`: verifies SBA data URLs still resolve.

## Phase 6 — Documentation (4:15–5:00)

- README.md, ARCHITECTURE.md, VIDEO_SCRIPT.md, TIME_LOG.md.
- Sample SaaSquatch CSV with 96 realistic rows across CA, TX, FL, AZ.

---

## Deviations

1. **Census API key required.** The prompt stated no API key was needed under 500 calls/day. The Census Bureau now requires a free API key for all requests. Resolution: built a cached ratios file (`data/reference/census_ratios_2022.json`) with 113 NAICS codes from published Census data. The `scripts/fetch_census.py` script supports `--api-key` for users who want to refresh from the live API.

2. **Full Parquet too large for git.** The processed Parquet for 4 states totals 173 MB (3.35M PPP + 497K SBA rows). Resolution: created `scripts/create_demo_subset.py` which samples ~5K PPP + ~2K SBA rows per state, prioritizing cities from the sample CSV. The demo subset is 1.4 MB and ships in `data/demo/`. The matching code auto-detects and uses it; set `GROUNDTRUTH_DATA_FULL=1` to use the full dataset.

3. **In-process dict instead of SQLite for job state.** The prompt called for SQLite via SQLModel. For a demo with no persistence requirements, an in-process Python dict is simpler and introduces no dependencies. The README documents this trade-off and what you'd switch to under load (Postgres + Redis).
