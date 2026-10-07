"""
Create a small demo subset of processed data for git.
Samples rows from cities present in the sample CSV + random other rows.
Target: <5MB total across all states.
"""
import csv
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = PROJECT_ROOT / "data" / "samples" / "saasquatch_export_sample.csv"
PROCESSED = PROJECT_ROOT / "data" / "processed"
DEMO_DIR = PROJECT_ROOT / "data" / "demo"

STATES = ["CA", "TX", "FL", "AZ"]
PPP_PER_STATE = 5000
SBA_PER_STATE = 2000


def get_sample_cities() -> dict[str, set[str]]:
    cities_by_state: dict[str, set[str]] = {}
    with open(SAMPLE_CSV) as f:
        for row in csv.DictReader(f):
            st = row.get("State", "").strip().upper()
            city = row.get("City", "").strip().upper()
            if st and city:
                cities_by_state.setdefault(st, set()).add(city)
    return cities_by_state


def main():
    sample_cities = get_sample_cities()
    conn = duckdb.connect()

    for state in STATES:
        cities = sample_cities.get(state, set())
        city_list = ", ".join(f"'{c}'" for c in cities)

        # PPP
        ppp_dir = PROCESSED / "ppp" / f"state={state}"
        demo_ppp_dir = DEMO_DIR / "ppp" / f"state={state}"
        demo_ppp_dir.mkdir(parents=True, exist_ok=True)

        if ppp_dir.exists():
            parquet_glob = str(ppp_dir / "*.parquet")
            if cities:
                conn.execute(f"""
                    COPY (
                        (SELECT * FROM read_parquet('{parquet_glob}')
                         WHERE UPPER(BorrowerCity) IN ({city_list})
                         LIMIT {PPP_PER_STATE // 2})
                        UNION ALL
                        (SELECT * FROM read_parquet('{parquet_glob}')
                         WHERE UPPER(BorrowerCity) NOT IN ({city_list})
                         USING SAMPLE {PPP_PER_STATE // 2})
                    ) TO '{demo_ppp_dir}/data.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
                """)
            else:
                conn.execute(f"""
                    COPY (SELECT * FROM read_parquet('{parquet_glob}')
                          USING SAMPLE {PPP_PER_STATE})
                    TO '{demo_ppp_dir}/data.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
                """)
            count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{demo_ppp_dir}/data.parquet')").fetchone()[0]
            print(f"  PPP {state}: {count:,} rows")

        # SBA 7(a)
        for dataset in ["sba7a", "sba504"]:
            src_dir = PROCESSED / dataset / f"state={state}"
            demo_dir = DEMO_DIR / dataset / f"state={state}"
            demo_dir.mkdir(parents=True, exist_ok=True)

            if src_dir.exists():
                parquet_glob = str(src_dir / "*.parquet")
                limit = SBA_PER_STATE if dataset == "sba7a" else 500
                if cities:
                    conn.execute(f"""
                        COPY (
                            (SELECT * FROM read_parquet('{parquet_glob}')
                             WHERE UPPER(BorrCity) IN ({city_list})
                             LIMIT {limit // 2})
                            UNION ALL
                            (SELECT * FROM read_parquet('{parquet_glob}')
                             WHERE UPPER(BorrCity) NOT IN ({city_list})
                             USING SAMPLE {limit // 2})
                        ) TO '{demo_dir}/data.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
                    """)
                else:
                    conn.execute(f"""
                        COPY (SELECT * FROM read_parquet('{parquet_glob}')
                              USING SAMPLE {limit})
                        TO '{demo_dir}/data.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
                    """)
                count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{demo_dir}/data.parquet')").fetchone()[0]
                print(f"  {dataset} {state}: {count:,} rows")

    conn.close()
    print()
    import subprocess
    result = subprocess.run(["du", "-sh", str(DEMO_DIR)], capture_output=True, text=True)
    print(f"Total demo size: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
