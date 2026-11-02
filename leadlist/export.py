import csv
from pathlib import Path


HEADER = ["name", "category", "street address", "postcode", "city", "website", "osm_url"]


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
