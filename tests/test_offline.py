import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class OfflineProof(unittest.TestCase):
    def test_cli_writes_sorted_unique_business_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "businesses.csv"
            result = subprocess.run(
                [sys.executable, "-m", "leadlist", "--city", "X", "--type", "bakery",
                 "--offline", "tests/fixtures/overpass_sample.json", "--out", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with output.open(encoding="utf-8", newline="") as stream:
                self.assertEqual(list(csv.reader(stream)), [
                    ["name", "category", "street address", "postcode", "city", "website", "osm_url"],
                    ["Amber Bakery", "bakery", "Main Street 1", "12345", "X", "", "https://www.openstreetmap.org/node/1"],
                    ["Birch Bakery", "bakery", "Oak Street 2", "", "X", "https://birch.example", "https://www.openstreetmap.org/way/4"],
                    ["Cedar Bakery", "bakery", "", "", "X", "", "https://www.openstreetmap.org/node/5"],
                    ["Dawn Bakery", "bakery", "", "", "X", "", "https://www.openstreetmap.org/node/6"],
                ])


class BusinessListTests(unittest.TestCase):
    def setUp(self):
        import json
        from unittest.mock import patch
        self.network = patch("leadlist.overpass.requests.post", side_effect=AssertionError("Unexpected network"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.payload = json.loads(Path("tests/fixtures/overpass_sample.json").read_text(encoding="utf-8"))

    def test_query_uses_city_and_mapped_tags(self):
        from leadlist.overpass import TAGS, build_query
        for category, (key, value) in TAGS.items():
            query = build_query("Tampere", category)
            self.assertIn('area["boundary"="administrative"]["name"="Tampere"]->.city;', query)
            self.assertIn(f'nwr["{key}"="{value}"]["name"](area.city);', query)
            self.assertTrue(query.endswith("out tags;"))

    def test_query_escapes_city(self):
        import json

        from leadlist.overpass import build_query
        city = 'X"\nY\\Z'
        self.assertIn(f'["name"={json.dumps(city)}]', build_query(city, "bakery"))

    def test_unknown_type_lists_known_types(self):
        from leadlist.overpass import TAGS, build_query
        with self.assertRaises(ValueError) as caught:
            build_query("X", "unknown")
        self.assertIn("Unknown business type 'unknown'. Known types:", str(caught.exception))
        for category in TAGS:
            self.assertIn(category, str(caught.exception))

    def test_empty_city_is_rejected(self):
        from leadlist.overpass import build_query
        with self.assertRaisesRegex(ValueError, "City must not be empty"):
            build_query("  ", "bakery")

    def test_deduplication_uses_name_and_address(self):
        from leadlist.overpass import parse_elements
        self.payload["elements"][2]["tags"].update(
            {"name": " amber bakery ", "addr:postcode": "99999", "addr:city": "Other"})
        rows = parse_elements(self.payload, "bakery", "X")
        self.assertEqual([row[0] for row in rows], ["Amber Bakery", "Birch Bakery", "Cedar Bakery", "Dawn Bakery"])
        self.assertEqual(rows[0][3:5], ["12345", "X"])

    def test_client_sends_one_polite_request(self):
        from unittest.mock import Mock, patch

        from leadlist.overpass import ENDPOINT, fetch_places
        response = Mock(status_code=200)
        response.json.return_value = self.payload
        with patch("leadlist.overpass.requests.post", return_value=response) as post:
            self.assertEqual(fetch_places("query"), self.payload)
        post.assert_called_once_with(
            ENDPOINT, data={"data": "query"},
            headers={"User-Agent": "demo-leadlist/0.1 (public business-list demo)"},
            timeout=35, allow_redirects=False,
        )

    def test_http_errors_and_redirects_are_clear(self):
        from unittest.mock import Mock, patch

        from leadlist.overpass import fetch_places
        for status in (302, 429, 500):
            with self.subTest(status=status):
                with patch("leadlist.overpass.requests.post", return_value=Mock(status_code=status)) as post:
                    with self.assertRaisesRegex(ValueError, f"Overpass HTTP {status}"):
                        fetch_places("query")
                    post.assert_called_once()

    def test_timeout_is_clear(self):
        from unittest.mock import patch

        import requests

        from leadlist.overpass import fetch_places
        with patch("leadlist.overpass.requests.post", side_effect=requests.Timeout("timed out")):
            with self.assertRaisesRegex(ValueError, "Overpass request failed: timed out"):
                fetch_places("query")

    def test_service_errors_and_invalid_responses_are_rejected(self):
        from unittest.mock import Mock, patch

        from leadlist.overpass import fetch_places
        for payload, message in (({}, "expected an elements list"),
                                 ({"elements": [], "remark": "query timed out"}, "query timed out")):
            response = Mock(status_code=200)
            response.json.return_value = payload
            with patch("leadlist.overpass.requests.post", return_value=response):
                with self.assertRaisesRegex(ValueError, message):
                    fetch_places("query")

    def test_live_cli_limits_sorted_rows(self):
        from unittest.mock import patch

        from leadlist.__main__ import main
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "live.csv"
            with patch.object(sys, "argv", ["leadlist", "--city", "X", "--type", "bakery",
                                          "--limit", "2", "--out", str(output)]):
                with patch("leadlist.__main__.fetch_places", return_value=self.payload) as fetch:
                    main()
                    fetch.assert_called_once()
            with output.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(len(rows), 3)
            self.assertEqual([row[0] for row in rows[1:]], ["Amber Bakery", "Birch Bakery"])

    def test_cli_rejects_unknown_type_and_invalid_limits(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from unittest.mock import patch

        from leadlist.__main__ import main
        for extra, message in ((["--type", "unknown"], "Known types:"),
                               (["--limit", "0"], "limit must be a positive integer"),
                               (["--limit", "bad"], "invalid positive_limit value")):
            with patch.object(sys, "argv", ["leadlist", "--city", "X", "--type", "bakery",
                                          "--out", "unused.csv", *extra]):
                errors = StringIO()
                with redirect_stderr(errors), self.assertRaises(SystemExit) as caught:
                    main()
                self.assertNotEqual(caught.exception.code, 0)
                self.assertIn(message, errors.getvalue())

    def test_skill_front_matter_and_cli(self):
        import json
        text = Path("skills/business-list/SKILL.md").read_text(encoding="utf-8")
        opening, frontmatter, body = text.split("---", 2)
        self.assertEqual(opening, "")
        # The skill uses only plain keys and plain/JSON-quoted YAML scalars.
        metadata = {}
        for line in frontmatter.strip().splitlines():
            key, value = line.split(":", 1)
            value = value.strip()
            metadata[key] = json.loads(value) if value.startswith('"') else value
        self.assertEqual(metadata["name"], "business-list")
        self.assertIn("Use when", metadata["description"])
        self.assertIn("python -m leadlist", body)
        for argument in ("--city", "--type", "--out", "--limit", "--offline"):
            self.assertIn(argument, body)
