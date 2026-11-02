"""Business lists from public OpenStreetMap data or a local fixture."""
import argparse
import json
from pathlib import Path

from .export import write_csv
from .overpass import build_query, fetch_places, parse_elements


def positive_limit(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=positive_limit, default=50)
    parser.add_argument("--offline", type=Path, help="Read an Overpass JSON fixture without network")
    args = parser.parse_args()
    try:
        query = build_query(args.city, args.type)
        payload = (json.loads(args.offline.read_text(encoding="utf-8"))
                   if args.offline else fetch_places(query))
        rows = parse_elements(payload, args.type, args.city)[:args.limit]
        write_csv(args.out, rows)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(1, f"leadlist: {error}\n")
    print(f"Wrote {len(rows)} businesses to {args.out}")


if __name__ == "__main__":
    main()
