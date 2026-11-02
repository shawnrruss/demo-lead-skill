# Business list demo

Original demo, public data only, not client work. AI-assisted implementation and documentation.

A small Claude Agent Skill and Python 3.12+ helper export named OpenStreetMap businesses to CSV, ready to open in a spreadsheet. Supported types: bakery, cafe, dentist, hairdresser, bicycle shop, restaurant, florist. The JSON mapping is in `leadlist/tags.json`.

## Install and run

From this repository with Python 3.12+:

```sh
python -m pip install -e .
python -m leadlist --city "Tampere" --type bakery --out out/bakeries.csv --limit 50
```

The default limit is 50 sorted, deduplicated rows; use a positive integer to change it. Quote multiword types, for example `--type "bicycle shop"`.

## Offline demonstration and tests

The fixture contains six made-up elements, including a duplicate and an unnamed place. This command writes four business rows and a header without network access:

```sh
python -m leadlist --city X --type bakery --offline tests/fixtures/overpass_sample.json --out out/t.csv
python -m unittest tests.test_offline
```

Tests mock HTTP calls; no live API access is needed.

## Install the Claude skill

Copy `skills/business-list` into your Claude skills directory (for Claude Code, `~/.claude/skills/business-list`). Install the Python helper as above and run it from this repository. Ask Claude for a CSV of businesses by city and type; the skill asks for missing inputs, runs the helper, summarizes results, and offers the CSV.

## Data and limitations

Data (c) OpenStreetMap contributors, ODbL

Source: [OpenStreetMap](https://www.openstreetmap.org/copyright), queried through the public [Overpass API](https://overpass-api.de/). Preserve this attribution when sharing the data; ODbL terms apply to OSM-derived data.

Each live run sends one POST request with a demo User-Agent, a 35-second client timeout and a 25-second query timeout. There are no automatic retries or redirects. HTTP and service errors produce a clear error and nonzero exit status.

City lookup uses exact administrative-area names. Ambiguous names may combine multiple areas; names must match OSM spelling, and places without matching areas return no rows. Coverage may be incomplete or outdated. The limit applies after retrieval, sorting and deduplication, so it does not bound query size.

Columns: name, category, street address, postcode, city, website, osm_url. Unnamed places are skipped; name plus street address determines duplicates (case-insensitive). Missing address fields stay empty; city falls back to the requested city. Website URLs are copied from OSM tags without fetching them. The helper exports no email or phone fields and does not scrape websites. Review data before business use.

Generated `out/`, logs, virtual environments and build metadata are ignored by git.
