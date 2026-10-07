# GroundTruth for SaaSquatch — Video Script (1:45)

## 0:00–0:20 — What I studied, what I didn't build

I spent time inside SaaSquatch before writing a line of code. The product already has AI revenue estimation, AI company scoring, email validation, an AI email generator, and a LinkedIn messenger. I also looked at dozens of public submissions for this challenge — nearly all of them rebuild a 0-to-100 lead scorer, MX email validation, or cold-email generation. That's work SaaSquatch already ships. I deliberately built none of it.

## 0:20–0:50 — The blind spot

SaaSquatch pulls from Apollo, Crunchbase, LinkedIn, and Growjo. Those sources skew toward tech and funded companies. But acquisition entrepreneurs buy HVAC shops, dental practices, landscapers, trucking firms — businesses that barely exist in those databases. SaaSquatch can only guess their revenue with AI.

Meanwhile, the U.S. government published loan-level records for 11.5 million of exactly these businesses through the PPP program. Each record includes a near-exact payroll figure tied to a six-digit NAICS code. Nobody in lead-gen uses this data. GroundTruth does.

## 0:50–1:25 — Live demo

Here's how it works. I upload a SaaSquatch CSV export. GroundTruth auto-detects the column mapping — company name, city, state, zip, estimated revenue — and lets me confirm or override before matching.

I hit Match. The system blocks by state and city, then scores each candidate using fuzzy name matching, zip code, street number, and NAICS consistency. Every match comes with plain-English reasons — "name 94% similar, zip matched, street number 1420 matched."

The results table shows match confidence tiers, PPP-implied revenue alongside the SaaSquatch estimate, headcount at filing, SBA loan history, and a recommendation — Worth a Credit, Verify First, or Skip — with the exact rule that fired. The sidebar filters by revenue range, franchise status, and match tier.

Now the key chart. For every lead where SaaSquatch provided a revenue estimate, I plot it against the PPP-implied figure on log-log axes. The dashed line is perfect agreement. Points off that line are leads where the AI estimate disagrees with what the business told the federal government. The histogram shows how many leads are off by more than two-x — those are enrichment credits you might be about to waste.

## 1:25–1:45 — Architecture and what's next

The backend is FastAPI querying Parquet files through DuckDB — columnar storage with partition pruning, no database server to manage. The frontend is React with TypeScript and Tailwind. Matching runs at 70 rows per second against four states. The whole demo subset is 1.4 megabytes.

What I'd build next: closed-loop learning. When Caprae's team calls a lead and it converts — or doesn't — feed that outcome back into the recommendation engine. That's a dataset only Caprae has, and it would make every future credit decision sharper.
