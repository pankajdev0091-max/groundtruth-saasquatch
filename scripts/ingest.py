"""
Download SBA PPP and 7(a)/504 loan data, filter to selected states,
and write Parquet partitioned by state. Idempotent and resumable.
"""
import argparse
import sys
import time
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

DEFAULT_STATES = ["CA", "TX", "FL", "AZ"]

PPP_BASE = "https://data.sba.gov/sites/default/files/distribution/SBA-OCA-2022-07-001"
PPP_FILES = [
    f"{PPP_BASE}/public_150k_plus_240930.csv",
    *[f"{PPP_BASE}/public_up_to_150k_{n}_240930.csv" for n in range(1, 13)],
]

SBA7A_BASE = "https://data.sba.gov/sites/default/files/uploaded_resources"
SBA7A_FILES = [
    f"{SBA7A_BASE}/FOIA_7a_FY2000_FY2009_asof_260630.csv",
    f"{SBA7A_BASE}/FOIA_7a_FY2010_FY2019_asof_260630.csv",
    f"{SBA7A_BASE}/FOIA_7a_FY2020_Present_asof_260630.csv",
]

SBA504_FILES = [
    f"{SBA7A_BASE}/FOIA_504_FY2010_Present_asof_260630.csv",
]

PPP_KEEP_COLUMNS = [
    "LoanNumber", "DateApproved", "ProcessingMethod",
    "BorrowerName", "BorrowerAddress", "BorrowerCity",
    "BorrowerState", "BorrowerZip", "LoanStatus",
    "InitialApprovalAmount", "CurrentApprovalAmount",
    "FranchiseName", "BusinessAgeDescription",
    "JobsReported", "NAICSCode", "PAYROLL_PROCEED",
    "BusinessType", "ForgivenessAmount", "ForgivenessDate",
    "RuralUrbanIndicator", "Term",
]

PPP_DROP_COLUMNS = ["Race", "Ethnicity", "Gender", "Veteran"]

SBA7A_KEEP_COLUMNS = [
    "BorrName", "BorrStreet", "BorrCity", "BorrState", "BorrZip",
    "BankName", "GrossApproval", "ApprovalDate", "ApprovalFY",
    "TermInMonths", "NaicsCode", "NaicsDescription",
    "FranchiseCode", "FranchiseName", "BusinessType", "BusinessAge",
    "LoanStatus", "JobsSupported", "ProcessingMethod", "Program",
]

SBA504_KEEP_COLUMNS = [
    "BorrName", "BorrStreet", "BorrCity", "BorrState", "BorrZip",
    "CDC_Name", "GrossApproval", "ApprovalDate", "ApprovalFY",
    "TermInMonths", "NaicsCode", "NaicsDescription",
    "FranchiseCode", "FranchiseName", "BusinessType", "BusinessAge",
    "LoanStatus", "JobsSupported", "ProcessingMethod", "Program",
]


def download_file(url: str, dest: Path) -> Path:
    import subprocess
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  [skip] {dest.name} already exists ({dest.stat().st_size:,} bytes)")
        return dest
    print(f"  [download] {dest.name}...")
    subprocess.run(
        ["curl", "-sL", "-o", str(dest), url],
        check=True,
    )
    print(f"  [done] {dest.name} ({dest.stat().st_size:,} bytes)")
    return dest


_udf_registered: set[int] = set()


def add_normalized_name(conn: duckdb.DuckDBPyConnection, table: str, name_col: str):
    """Add a normalized_name column using SQL-based normalization."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from groundtruth.normalize import normalize_name

    conn_id = id(conn)
    if conn_id not in _udf_registered:
        conn.create_function("normalize_name_udf", lambda x: normalize_name(x or "").normalized, [str], str)
        _udf_registered.add(conn_id)
    conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS normalized_name VARCHAR")
    conn.execute(f"UPDATE {table} SET normalized_name = normalize_name_udf({name_col})")


def ingest_ppp(states: list[str], skip_download: bool = False):
    print("\n=== PPP Loan Data ===")
    t0 = time.time()

    csv_paths = []
    if not skip_download:
        for url in PPP_FILES:
            name = url.split("/")[-1]
            path = download_file(url, DATA_RAW / name)
            csv_paths.append(path)
    else:
        csv_paths = sorted(DATA_RAW.glob("public_*.csv"))
        if not csv_paths:
            print("  No PPP CSV files found in data/raw/. Run without --skip-download.")
            return

    conn = duckdb.connect()
    state_filter = ", ".join(f"'{s}'" for s in states)
    select_cols = ", ".join(PPP_KEEP_COLUMNS)

    total_rows = 0
    state_counts: dict[str, int] = {}

    for i, csv_path in enumerate(csv_paths):
        print(f"  Processing {csv_path.name} ({i+1}/{len(csv_paths)})...")
        conn.execute(f"""
            CREATE OR REPLACE TABLE ppp_chunk AS
            SELECT {select_cols}
            FROM read_csv_auto('{csv_path}', header=true, ignore_errors=true)
            WHERE BorrowerState IN ({state_filter})
        """)
        chunk_count = conn.execute("SELECT COUNT(*) FROM ppp_chunk").fetchone()[0]
        if chunk_count == 0:
            continue

        add_normalized_name(conn, "ppp_chunk", "BorrowerName")

        for state in states:
            out_dir = DATA_PROCESSED / "ppp" / f"state={state}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"part_{i:02d}.parquet"

            count = conn.execute(f"""
                COPY (SELECT * FROM ppp_chunk WHERE BorrowerState = '{state}')
                TO '{out_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """).fetchone()

            sc = conn.execute(f"SELECT COUNT(*) FROM ppp_chunk WHERE BorrowerState = '{state}'").fetchone()[0]
            state_counts[state] = state_counts.get(state, 0) + sc
            total_rows += sc

    elapsed = time.time() - t0
    print(f"\n  PPP Ingest Summary ({elapsed:.1f}s):")
    print(f"  {'State':<8} {'Rows':>12}")
    print(f"  {'-'*8} {'-'*12}")
    for state in sorted(state_counts):
        print(f"  {state:<8} {state_counts[state]:>12,}")
    print(f"  {'TOTAL':<8} {total_rows:>12,}")
    conn.close()


def ingest_sba7a(states: list[str], skip_download: bool = False):
    print("\n=== SBA 7(a) Loan Data ===")
    t0 = time.time()

    csv_paths = []
    if not skip_download:
        for url in SBA7A_FILES:
            name = url.split("/")[-1]
            path = download_file(url, DATA_RAW / name)
            csv_paths.append(path)
    else:
        csv_paths = sorted(DATA_RAW.glob("FOIA_7a_*.csv"))
        if not csv_paths:
            print("  No 7(a) CSV files found. Run without --skip-download.")
            return

    conn = duckdb.connect()
    state_filter = ", ".join(f"'{s}'" for s in states)
    select_cols = ", ".join(SBA7A_KEEP_COLUMNS)

    total_rows = 0
    state_counts: dict[str, int] = {}

    for i, csv_path in enumerate(csv_paths):
        print(f"  Processing {csv_path.name} ({i+1}/{len(csv_paths)})...")
        conn.execute(f"""
            CREATE OR REPLACE TABLE sba_chunk AS
            SELECT {select_cols}
            FROM read_csv_auto('{csv_path}', header=true, ignore_errors=true, quote='"')
            WHERE BorrState IN ({state_filter})
        """)
        chunk_count = conn.execute("SELECT COUNT(*) FROM sba_chunk").fetchone()[0]
        if chunk_count == 0:
            continue

        add_normalized_name(conn, "sba_chunk", "BorrName")

        for state in states:
            out_dir = DATA_PROCESSED / "sba7a" / f"state={state}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"part_{i:02d}.parquet"

            conn.execute(f"""
                COPY (SELECT * FROM sba_chunk WHERE BorrState = '{state}')
                TO '{out_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)

            sc = conn.execute(f"SELECT COUNT(*) FROM sba_chunk WHERE BorrState = '{state}'").fetchone()[0]
            state_counts[state] = state_counts.get(state, 0) + sc
            total_rows += sc

    elapsed = time.time() - t0
    print(f"\n  7(a) Ingest Summary ({elapsed:.1f}s):")
    print(f"  {'State':<8} {'Rows':>12}")
    print(f"  {'-'*8} {'-'*12}")
    for state in sorted(state_counts):
        print(f"  {state:<8} {state_counts[state]:>12,}")
    print(f"  {'TOTAL':<8} {total_rows:>12,}")
    conn.close()


def ingest_sba504(states: list[str], skip_download: bool = False):
    print("\n=== SBA 504 Loan Data ===")
    t0 = time.time()

    csv_paths = []
    if not skip_download:
        for url in SBA504_FILES:
            name = url.split("/")[-1]
            path = download_file(url, DATA_RAW / name)
            csv_paths.append(path)
    else:
        csv_paths = sorted(DATA_RAW.glob("FOIA_504_*.csv"))
        if not csv_paths:
            print("  No 504 CSV files found. Run without --skip-download.")
            return

    conn = duckdb.connect()
    state_filter = ", ".join(f"'{s}'" for s in states)
    select_cols = ", ".join(SBA504_KEEP_COLUMNS)

    total_rows = 0
    state_counts: dict[str, int] = {}

    for i, csv_path in enumerate(csv_paths):
        print(f"  Processing {csv_path.name} ({i+1}/{len(csv_paths)})...")
        conn.execute(f"""
            CREATE OR REPLACE TABLE sba504_chunk AS
            SELECT {select_cols}
            FROM read_csv_auto('{csv_path}', header=true, ignore_errors=true, quote='"')
            WHERE BorrState IN ({state_filter})
        """)
        chunk_count = conn.execute("SELECT COUNT(*) FROM sba504_chunk").fetchone()[0]
        if chunk_count == 0:
            continue

        add_normalized_name(conn, "sba504_chunk", "BorrName")

        for state in states:
            out_dir = DATA_PROCESSED / "sba504" / f"state={state}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"part_{i:02d}.parquet"

            conn.execute(f"""
                COPY (SELECT * FROM sba504_chunk WHERE BorrState = '{state}')
                TO '{out_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)

            sc = conn.execute(f"SELECT COUNT(*) FROM sba504_chunk WHERE BorrState = '{state}'").fetchone()[0]
            state_counts[state] = state_counts.get(state, 0) + sc
            total_rows += sc

    elapsed = time.time() - t0
    print(f"\n  504 Ingest Summary ({elapsed:.1f}s):")
    print(f"  {'State':<8} {'Rows':>12}")
    print(f"  {'-'*8} {'-'*12}")
    for state in sorted(state_counts):
        print(f"  {state:<8} {state_counts[state]:>12,}")
    print(f"  {'TOTAL':<8} {total_rows:>12,}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest SBA loan data into Parquet")
    parser.add_argument(
        "--states",
        default=",".join(DEFAULT_STATES),
        help="Comma-separated state codes (default: CA,TX,FL,AZ)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading, process already-downloaded files",
    )
    parser.add_argument(
        "--ppp-only",
        action="store_true",
        help="Only ingest PPP data",
    )
    parser.add_argument(
        "--sba-only",
        action="store_true",
        help="Only ingest 7(a)/504 data",
    )
    args = parser.parse_args()
    states = [s.strip().upper() for s in args.states.split(",")]

    print(f"Ingesting data for states: {', '.join(states)}")
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    if not args.sba_only:
        ingest_ppp(states, args.skip_download)
    if not args.ppp_only:
        ingest_sba7a(states, args.skip_download)
        ingest_sba504(states, args.skip_download)

    print("\nDone.")


if __name__ == "__main__":
    main()
