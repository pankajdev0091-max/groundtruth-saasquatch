"""Verify that SBA data source URLs still resolve."""
import sys
from pathlib import Path
from urllib.request import urlopen, Request

import yaml

CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"


def check():
    with open(CONFIG) as f:
        sources = yaml.safe_load(f)

    errors = []
    checked = 0

    for dataset_name, dataset in sources.items():
        files = dataset.get("files", [])
        for entry in files:
            url = entry["url"] if isinstance(entry, dict) else entry
            name = entry.get("name", url.split("/")[-1]) if isinstance(entry, dict) else url.split("/")[-1]
            try:
                req = Request(url, method="HEAD", headers={"User-Agent": "GroundTruth/1.0"})
                with urlopen(req, timeout=15) as resp:
                    status = resp.status
                    if status == 200:
                        print(f"  [OK]   {dataset_name}/{name}")
                    else:
                        print(f"  [WARN] {dataset_name}/{name} — HTTP {status}")
                        errors.append(f"{name}: HTTP {status}")
            except Exception as e:
                print(f"  [FAIL] {dataset_name}/{name} — {e}")
                errors.append(f"{name}: {e}")
            checked += 1

    print(f"\nChecked {checked} URLs, {len(errors)} errors")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    check()
