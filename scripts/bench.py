"""
Benchmark: measure matching speed against PPP data.
Target: 1000 rows matched in under 60 seconds against 4-state partition.
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from groundtruth.match import match_business
from groundtruth.signals import compute_signals

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "samples" / "saasquatch_export_sample.csv"


def run_benchmark(n_rows: int = 100) -> dict:
    with open(SAMPLE_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if n_rows > len(rows):
        rows = rows * (n_rows // len(rows) + 1)
    rows = rows[:n_rows]

    print(f"Benchmarking {n_rows} rows...")
    t0 = time.time()
    matched = 0
    for i, row in enumerate(rows):
        bm = match_business(
            name=row.get("Company", ""),
            city=row.get("City", ""),
            state=row.get("State", ""),
            zip_code=row.get("Zip", ""),
            address=row.get("Address", ""),
            industry=row.get("Industry"),
        )
        if bm.best_match:
            matched += 1
            compute_signals(
                match=bm.best_match,
                sba_loans=bm.sba_loans,
            )
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{n_rows} ({rate:.1f} rows/s, {matched} matched)")

    elapsed = time.time() - t0
    rate = n_rows / elapsed

    result = {
        "rows": n_rows,
        "elapsed_seconds": round(elapsed, 2),
        "rows_per_second": round(rate, 1),
        "matched": matched,
        "match_rate": round(matched / n_rows * 100, 1),
    }

    print(f"\n{'='*50}")
    print(f"  Rows:           {n_rows}")
    print(f"  Elapsed:        {elapsed:.2f}s")
    print(f"  Rate:           {rate:.1f} rows/s")
    print(f"  Matched:        {matched} ({matched/n_rows*100:.1f}%)")
    print(f"  1000-row est:   {1000/rate:.1f}s")
    target = "PASS" if 1000 / rate < 60 else "FAIL"
    print(f"  Target (<60s):  {target}")
    print(f"{'='*50}")

    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_benchmark(n)
