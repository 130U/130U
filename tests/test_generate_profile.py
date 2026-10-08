from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TEST_TMP = ROOT / "previews" / "test-tmp"
sys.path.insert(0, str(ROOT / "scripts"))

import generate_profile  # noqa: E402
import validate_profile  # noqa: E402


CALENDAR_HTML = """
<h2 id="js-contribution-activity-description">3 contributions in the last year</h2>
<table><tbody><tr>
<td id="contribution-day-component-0-0" data-date="2026-10-02" data-level="0"></td>
<td id="contribution-day-component-0-1" data-date="2026-10-01" data-level="2"></td>
<td id="contribution-day-component-0-2" data-date="2026-10-03" data-level="1"></td>
</tr></tbody></table>
<tool-tip for="contribution-day-component-0-0">No contributions on October 2, 2026.</tool-tip>
<tool-tip for="contribution-day-component-0-1">2 contributions on October 1, 2026.</tool-tip>
<tool-tip for="contribution-day-component-0-2">1 contribution on October 3, 2026.</tool-tip>
"""
EXPECTED_CONTRIBUTIONS = {
    "total": 3,
    "days": [
        {"date": "2026-10-01", "count": 2, "level": 2},
        {"date": "2026-10-02", "count": 0, "level": 0},
        {"date": "2026-10-03", "count": 1, "level": 1},
    ],
    "range_start": "2026-10-01",
    "range_end": "2026-10-03",
}
GENERATED_AT = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def snapshot_config() -> dict:
    return {
        "username": "130U",
        "fallback_contributions": EXPECTED_CONTRIBUTIONS,
        "snapshot_updated_at": "2026-10-01T12:00:00Z",
    }


def setUpModule() -> None:
    TEST_TMP.mkdir(parents=True, exist_ok=True)


class ContributionCalendarTests(unittest.TestCase):
    def test_official_total_and_unordered_daily_cells_are_reconciled(self) -> None:
        data = generate_profile.parse_contributions(CALENDAR_HTML)
        self.assertEqual(data, EXPECTED_CONTRIBUTIONS)
        self.assertEqual(data["total"], sum(day["count"] for day in data["days"]))
        self.assertEqual([day["date"] for day in data["days"]], sorted(day["date"] for day in data["days"]))

    def test_comma_formatted_official_counts_are_parsed(self) -> None:
        html = CALENDAR_HTML.replace("3 contributions in", "1,234 contributions in").replace(
            "2 contributions on", "1,233 contributions on"
        )
        data = generate_profile.parse_contributions(html)
        self.assertEqual(data["total"], 1234)
        self.assertEqual(data["days"][0]["count"], 1233)

    def test_total_must_match_daily_counts(self) -> None:
        html = CALENDAR_HTML.replace("3 contributions in", "4 contributions in")
        with self.assertRaisesRegex(ValueError, "total does not match"):
            generate_profile.parse_contributions(html)

    def test_duplicate_cells_tooltips_and_dates_are_rejected(self) -> None:
        cases = {
            "cell_id": CALENDAR_HTML + '<td id="contribution-day-component-0-0" data-date="2026-10-04" data-level="0"></td>',
            "tooltip": CALENDAR_HTML + '<tool-tip for="contribution-day-component-0-0">No contributions on October 2, 2026.</tool-tip>',
            "date": CALENDAR_HTML.replace('data-date="2026-10-02"', 'data-date="2026-10-01"'),
        }
        for label, html in cases.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                generate_profile.parse_contributions(html)

    def test_noncontinuous_daily_dates_are_rejected(self) -> None:
        html = CALENDAR_HTML.replace('data-date="2026-10-02"', 'data-date="2026-10-04"')
        with self.assertRaisesRegex(ValueError, "unique and continuous"):
            generate_profile.parse_contributions(html)

    def test_missing_or_unreadable_daily_counts_are_rejected(self) -> None:
        tooltip = '<tool-tip for="contribution-day-component-0-0">No contributions on October 2, 2026.</tool-tip>'
        cases = [CALENDAR_HTML.replace(tooltip, ""), CALENDAR_HTML.replace("No contributions on", "Contributions on")]
        for html in cases:
            with self.subTest(html=html), self.assertRaisesRegex(ValueError, "Missing contribution count"):
                generate_profile.parse_contributions(html)

    def test_missing_or_changed_official_heading_is_rejected(self) -> None:
        cases = [
            CALENDAR_HTML.replace('id="js-contribution-activity-description"', 'id="unrelated-heading"'),
            CALENDAR_HTML.replace("3 contributions in the last year", "3 contributions this year"),
        ]
        for html in cases:
            with self.subTest(html=html), self.assertRaisesRegex(ValueError, "incomplete"):
                generate_profile.parse_contributions(html)

    def test_invalid_calendar_dates_and_intensity_are_rejected(self) -> None:
        cases = [
            CALENDAR_HTML.replace('data-date="2026-10-02"', 'data-date="2026-02-30"'),
            CALENDAR_HTML.replace('data-date="2026-10-02"', 'data-date="20261002"'),
            CALENDAR_HTML.replace('data-level="2"', 'data-level="5"'),
        ]
        for html in cases:
            with self.subTest(html=html), self.assertRaises(ValueError):
                generate_profile.parse_contributions(html)


class GenerateProfileTests(unittest.TestCase):
    def test_public_calendar_request_omits_token_and_requests_english(self) -> None:
        response = io.BytesIO(CALENDAR_HTML.encode("utf-8"))
        with patch.dict(os.environ, {"GITHUB_TOKEN": "not-a-real-token"}), patch.object(
            generate_profile.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            data = generate_profile.collect_live_data({"username": "130U"})

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://github.com/users/130U/contributions")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.get_header("User-agent"), "130U-profile-generator")
        self.assertEqual(request.get_header("Accept-language"), "en-US")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 30)
        self.assertEqual(data["source"], generate_profile.LIVE_SOURCE)
        self.assertEqual({key: data[key] for key in EXPECTED_CONTRIBUTIONS}, EXPECTED_CONTRIBUTIONS)

    def test_unavailable_calendar_falls_back_without_changing_collection_time(self) -> None:
        config = snapshot_config()
        errors = [
            urllib.error.HTTPError("https://github.com/users/130U/contributions", 403, "unavailable", None, None),
            urllib.error.URLError("offline"),
            TimeoutError("timed out"),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__), patch.object(
                generate_profile, "collect_live_data", side_effect=error
            ), patch("sys.stderr", new_callable=io.StringIO):
                data = generate_profile.resolve_profile_data(config, live=True)
            self.assertEqual(data["source"], "verified local snapshot")
            self.assertEqual(data["snapshot_at"], config["snapshot_updated_at"])
            self.assertEqual(data["total"], EXPECTED_CONTRIBUTIONS["total"])

    def test_malformed_public_calendar_falls_back_to_verified_saved_data(self) -> None:
        response = io.BytesIO(CALENDAR_HTML.replace("3 contributions in", "4 contributions in").encode("utf-8"))
        config = snapshot_config()
        with patch.object(generate_profile.urllib.request, "urlopen", return_value=response), patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            data = generate_profile.resolve_profile_data(config, live=True)
        self.assertEqual(data["source"], "verified local snapshot")
        self.assertEqual(data["snapshot_at"], config["snapshot_updated_at"])
        self.assertEqual(data["days"], EXPECTED_CONTRIBUTIONS["days"])

    def test_main_saves_successfully_verified_live_snapshot(self) -> None:
        config = snapshot_config()
        live = {**EXPECTED_CONTRIBUTIONS, "source": generate_profile.LIVE_SOURCE}
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            path = Path(directory) / "profile.config.json"
            path.write_text(json.dumps(config) + "\n", encoding="utf-8")
            with patch.object(generate_profile, "CONFIG_PATH", path), patch.object(
                generate_profile, "collect_live_data", return_value=live
            ), patch.object(generate_profile, "write_assets") as write_assets, patch.object(
                generate_profile, "datetime"
            ) as clock, patch.object(sys, "argv", ["generate_profile.py", "--live"]), patch(
                "sys.stdout", new_callable=io.StringIO
            ):
                clock.now.return_value = GENERATED_AT
                generate_profile.main()
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["fallback_contributions"], EXPECTED_CONTRIBUTIONS)
        self.assertEqual(saved["snapshot_updated_at"], "2026-10-08T12:00:00Z")
        write_assets.assert_called_once()
        self.assertEqual(write_assets.call_args.args[1], live)

    def test_main_does_not_overwrite_snapshot_after_public_calendar_failure(self) -> None:
        config = snapshot_config()
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            path = Path(directory) / "profile.config.json"
            original = json.dumps(config, indent=2) + "\n"
            path.write_text(original, encoding="utf-8", newline="\n")
            original_bytes = path.read_bytes()
            with patch.object(generate_profile, "CONFIG_PATH", path), patch.object(
                generate_profile, "collect_live_data", side_effect=urllib.error.URLError("offline")
            ), patch.object(generate_profile, "write_assets") as write_assets, patch.object(
                generate_profile, "datetime"
            ) as clock, patch.object(sys, "argv", ["generate_profile.py", "--live"]), patch(
                "sys.stdout", new_callable=io.StringIO
            ), patch("sys.stderr", new_callable=io.StringIO):
                clock.now.return_value = GENERATED_AT
                generate_profile.main()
            self.assertEqual(path.read_bytes(), original_bytes)
        data = write_assets.call_args.args[1]
        self.assertEqual(data["source"], "verified local snapshot")
        self.assertEqual(data["snapshot_at"], config["snapshot_updated_at"])

    def test_snapshot_generation_writes_eight_deterministic_static_safe_assets(self) -> None:
        config = generate_profile.load_config()
        data = generate_profile.collect_snapshot_data(config)
        first = generate_profile.build_assets(config, data, GENERATED_AT)
        self.assertEqual(first, generate_profile.build_assets(config, data, GENERATED_AT))
        self.assertEqual(set(first), validate_profile.EXPECTED_ASSETS)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory, patch.object(
            generate_profile, "OUTPUT_DIR", Path(directory)
        ):
            generate_profile.write_assets(config, data, GENERATED_AT)
            assets = sorted(Path(directory).glob("*.svg"))
            self.assertEqual({asset.name for asset in assets}, validate_profile.EXPECTED_ASSETS)
            for asset in assets:
                validate_profile.validate_svg(asset)
                svg = asset.read_text(encoding="utf-8")
                self.assertNotIn("@keyframes", svg)
                self.assertNotIn("animation:", svg)
                self.assertNotIn("ACCOUNT AGE", svg)
                self.assertFalse(asset.name.startswith("signals-"))

    def test_fallback_date_is_not_replaced_by_asset_regeneration_date(self) -> None:
        config = generate_profile.load_config()
        config["snapshot_updated_at"] = "2026-10-01T12:00:00Z"
        data = generate_profile.collect_snapshot_data(config)
        assets = generate_profile.build_assets(config, data, GENERATED_AT)
        for name, svg in assets.items():
            if name.startswith("telemetry-"):
                visible = " ".join(ET.fromstring(svg).itertext()).upper()
                self.assertIn("SAVED SNAPSHOT", visible)
                self.assertIn("01 OCT 2026 UTC", visible)
                self.assertNotIn("08 OCT 2026 UTC", visible)

    def test_profile_leads_with_ai_and_retains_both_mathematical_finance_projects(self) -> None:
        validate_profile.validate_readme()
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        headings = ("Artificial Intelligence and Engineering", "Mathematical Finance", "GitHub Contributions")
        positions = [readme.index("## " + heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        first, second = validate_profile.EXPECTED_ACADEMIC_REPOSITORIES
        swapped = readme.replace(first, "TEMP_ACADEMIC_REPOSITORY").replace(second, first).replace(
            "TEMP_ACADEMIC_REPOSITORY", second
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            path = Path(directory) / "README.md"
            path.write_text(swapped, encoding="utf-8")
            with patch.object(validate_profile, "README", path), self.assertRaisesRegex(AssertionError, "project ordering"):
                validate_profile.validate_readme()


if __name__ == "__main__":
    unittest.main()
