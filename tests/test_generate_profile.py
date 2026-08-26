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

    def test_snapshot_generation_writes_twelve_valid_svg_assets(self) -> None:
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

        self.assertEqual(len(assets), 12)

    def test_asset_build_is_deterministic_and_styles_are_family_scoped(self) -> None:
        config = generate_profile.load_config()
        data = generate_profile.collect_snapshot_data(config)
        generated_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

        first = generate_profile.build_assets(config, data, generated_at)
        second = generate_profile.build_assets(config, data, generated_at)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 12)
        for name, svg in first.items():
            if name.startswith("telemetry-"):
                self.assertIn("infinite", svg)
                self.assertNotIn("bar-scan", svg)
                self.assertNotIn("orbiter-", svg)
            else:
                self.assertNotIn("infinite", svg)
            if name.startswith("hero-"):
                self.assertNotIn("seconds-frame", svg)
                self.assertNotIn("bar-scan", svg)
            if name.startswith("signals-"):
                self.assertNotIn("seconds-frame", svg)
                self.assertNotIn("metric-runner", svg)


if __name__ == "__main__":
    unittest.main()
