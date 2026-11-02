"""Build Overpass queries and extract public business facts."""
import json
from importlib.resources import files

import requests

TAGS = json.loads(files("leadlist").joinpath("tags.json").read_text(encoding="utf-8"))
ENDPOINT = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "demo-leadlist/0.1 (public business-list demo)"}


def build_query(city: str, category: str) -> str:
    if category not in TAGS:
        raise ValueError(f"Unknown business type {category!r}. Known types: {', '.join(sorted(TAGS))}")
    if not city.strip():
        raise ValueError("City must not be empty")
    key, value = TAGS[category]
    return (
        '[out:json][timeout:25];\n'
        f'area["boundary"="administrative"]["name"={json.dumps(city.strip(), ensure_ascii=False)}]->.city;\n'
        f'nwr["{key}"="{value}"]["name"](area.city);\n'
        "out tags;"
    )


def fetch_places(query: str) -> dict:
    """Make one request, with no retries or redirect requests."""
    try:
        response = requests.post(ENDPOINT, data={"data": query}, headers=HEADERS,
                                 timeout=35, allow_redirects=False)
        if response.status_code != 200:
            raise ValueError(f"Overpass HTTP {response.status_code}; try again later")
        payload = response.json()
    except requests.RequestException as error:
        raise ValueError(f"Overpass request failed: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise ValueError("Invalid Overpass response: expected an elements list")
    if payload.get("remark"):
        raise ValueError(f"Overpass could not complete the query: {payload['remark']}")
    return payload


def parse_elements(payload: dict, category: str, city: str) -> list[list[str]]:
    """Skip unnamed places, deduplicate by name and address, then sort."""
    rows = []
    seen = set()
    for element in payload["elements"]:
        tags = element.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue
        address = " ".join(filter(None, (tags.get("addr:street", "").strip(),
                                         tags.get("addr:housenumber", "").strip())))
        key = (name.casefold(), address.casefold())
        if key in seen:
            continue
        seen.add(key)
        rows.append([
            name, category, address, tags.get("addr:postcode", ""),
            tags.get("addr:city", city), tags.get("website", tags.get("contact:website", "")),
            f"https://www.openstreetmap.org/{element['type']}/{element['id']}"])
    return sorted(rows, key=lambda row: row[0].casefold())
