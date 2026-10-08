from __future__ import annotations

import io
import sys
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_profile  # noqa: E402
import validate_profile  # noqa: E402


class GenerateProfileTests(unittest.TestCase):
    def test_public_api_request_omits_repository_token(self) -> None:
        response = io.BytesIO(b'{"ok": true}')
        with patch.object(generate_profile.urllib.request, "urlopen", return_value=response) as urlopen:
            self.assertEqual(generate_profile.api_get("/users/130U"), {"ok": True})

        request = urlopen.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.get_header("User-agent"), "130U-profile-generator")

    def test_api_get_all_paginates_direct_repository_listings(self) -> None:
        with patch.object(
            generate_profile,
            "api_get",
            side_effect=[[{"sha": "a"}, {"sha": "b"}], [{"sha": "c"}]],
        ) as api_get:
            items = generate_profile.api_get_all("/repos/130U/example/commits?author=130U", per_page=2)

        self.assertEqual([item["sha"] for item in items], ["a", "b", "c"])
        self.assertEqual(
            [call.args[0] for call in api_get.call_args_list],
            [
                "/repos/130U/example/commits?author=130U&per_page=2&page=1",
                "/repos/130U/example/commits?author=130U&per_page=2&page=2",
            ],
        )

    def test_live_collection_uses_repository_endpoints_not_search(self) -> None:
        config = {
            "username": "130U",
            "language_source_repositories": ["example"],
        }

        def fake_get(path: str) -> object:
            self.assertNotIn("/search/", path)
            if path == "/users/130U":
                return {"created_at": "2026-07-20T15:13:55Z", "public_repos": 6}
            if path == "/repos/130U/example/languages":
                return {"Python": 12}
            self.fail(f"Unexpected API path: {path}")

        def fake_get_all(path: str) -> list[dict]:
            self.assertNotIn("/search/", path)
            if "/commits?author=130U" in path:
                return [{"sha": "a"}, {"sha": "b"}]
            if "/pulls?state=all" in path:
                return [
                    {"user": {"login": "130U"}},
                    {"user": {"login": "someone-else"}},
                    {"user": None},
                ]
            self.fail(f"Unexpected listing path: {path}")

        with patch.object(generate_profile, "api_get", side_effect=fake_get), patch.object(
            generate_profile, "api_get_all", side_effect=fake_get_all
        ):
            data = generate_profile.collect_live_data(config)

        self.assertEqual(data["public_commits"], 2)
        self.assertEqual(data["pull_requests"], 1)
        self.assertEqual(data["languages"], {"Python": 12})

    def test_live_collection_falls_back_on_github_http_failure(self) -> None:
        config = {
            "account_created_at": "2026-07-20T15:13:55Z",
            "fallback_metrics": {
                "public_commits": 43,
                "pull_requests": 21,
                "public_repositories": 6,
            },
            "fallback_languages": {"Python": 12},
        }
        rate_limit = urllib.error.HTTPError(
            "https://api.github.com/users/130U",
            403,
            "rate limit exceeded",
            hdrs=None,
            fp=None,
        )

        with patch.object(generate_profile, "collect_live_data", side_effect=rate_limit):
            data = generate_profile.resolve_profile_data(config, live=True)

        self.assertEqual(data["source"], "verified local snapshot")
        self.assertEqual(data["public_commits"], 43)

    def test_snapshot_generation_writes_eight_static_safe_svg_assets(self) -> None:
        config = generate_profile.load_config()
        data = generate_profile.collect_snapshot_data(config)
        generated_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as directory, patch.object(
            generate_profile, "OUTPUT_DIR", Path(directory)
        ):
            generate_profile.write_assets(config, data, generated_at)
            assets = sorted(Path(directory).glob("*.svg"))
            for asset in assets:
                ET.parse(asset)
                validate_profile.validate_svg(asset)

        self.assertEqual({asset.name for asset in assets}, validate_profile.EXPECTED_ASSETS)

    def test_asset_build_is_deterministic_and_static(self) -> None:
        config = generate_profile.load_config()
        data = generate_profile.collect_snapshot_data(config)
        generated_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

        first = generate_profile.build_assets(config, data, generated_at)
        second = generate_profile.build_assets(config, data, generated_at)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 8)
        for name, svg in first.items():
            self.assertNotIn("infinite", svg)
            self.assertNotIn("@keyframes", svg)
            self.assertNotIn("animation:", svg)
            self.assertNotIn("seconds-frame", svg)
            self.assertNotIn("ACCOUNT AGE", svg)
            self.assertFalse(name.startswith("signals-"))

    def test_fallback_metrics_keep_their_collection_date_when_assets_are_regenerated(self) -> None:
        config = generate_profile.load_config()
        config["snapshot_updated_at"] = "2026-10-01T12:00:00Z"
        failure = urllib.error.URLError("offline")
        with patch.object(generate_profile, "collect_live_data", side_effect=failure):
            data = generate_profile.resolve_profile_data(config, live=True)

        self.assertEqual(data["source"], "verified local snapshot")
        self.assertEqual(data.get("snapshot_at"), config["snapshot_updated_at"])
        regenerated_at = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
        assets = generate_profile.build_assets(config, data, regenerated_at)
        old_date_patterns = (
            "01 OCT 2026", "OCT 01, 2026", "OCT 1, 2026", "2026-10-01", "1 OCT 2026",
        )
        generated_date_patterns = ("08 OCT 2026", "OCT 08, 2026", "OCT 8, 2026", "2026-10-08", "8 OCT 2026")
        for name, svg in assets.items():
            if not name.startswith("telemetry-"):
                continue
            visible_text = " ".join(ET.fromstring(svg).itertext()).upper()
            self.assertTrue(any(date in visible_text for date in old_date_patterns), name)
            self.assertFalse(any(date in visible_text for date in generated_date_patterns), name)
            self.assertIn("SNAPSHOT", visible_text)

    def test_profile_presents_both_mathematical_finance_projects_before_engineering(self) -> None:
        validate_profile.validate_readme()
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        first, second = validate_profile.EXPECTED_ACADEMIC_REPOSITORIES
        swapped = readme.replace(first, "TEMP_ACADEMIC_REPOSITORY").replace(second, first).replace(
            "TEMP_ACADEMIC_REPOSITORY", second
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text(swapped, encoding="utf-8")
            with patch.object(validate_profile, "README", path):
                with self.assertRaisesRegex(AssertionError, "project ordering"):
                    validate_profile.validate_readme()


if __name__ == "__main__":
    unittest.main()
