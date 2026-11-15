from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from maafw_release import (
    latest_prerelease,
    is_prerelease,
    normalize_version,
    upstream_tag,
)


class MaafwVersionTests(unittest.TestCase):
    def test_normalizes_supported_prerelease_names(self) -> None:
        cases = {
            "v6.0.0-alpha.1": "6.0.0a1",
            "6.0.0-alpha1": "6.0.0a1",
            "5.13.0-beta.1": "5.13.0b1",
            "5.13.0b6": "5.13.0b6",
            "5.14.0-rc.2": "5.14.0rc2",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_version(raw), expected)

    def test_preserves_stable_release(self) -> None:
        self.assertEqual(normalize_version("v5.12.3"), "5.12.3")
        self.assertFalse(is_prerelease("5.12.3"))

    def test_converts_normalized_version_back_to_upstream_tag(self) -> None:
        self.assertEqual(upstream_tag("6.0.0a1"), "v6.0.0-alpha.1")
        self.assertEqual(upstream_tag("5.13.0b1"), "v5.13.0-beta.1")
        self.assertEqual(upstream_tag("5.14.0rc2"), "v5.14.0-rc.2")

    @patch("maafw_release.gh_json")
    @patch("maafw_release.gh_text")
    def test_latest_prerelease_uses_first_paginated_result(
        self, gh_text, gh_json
    ) -> None:
        gh_text.return_value = "v6.0.0-alpha.1\nv5.3.0-beta.1\nv2.2.0-beta.2"
        gh_json.return_value = {
            "tag_name": "v6.0.0-alpha.1",
            "published_at": "2026-11-14T16:03:25Z",
            "prerelease": True,
        }

        release = latest_prerelease()

        self.assertEqual(release.version, "6.0.0a1")
        gh_json.assert_called_once_with(
            "repos/MaaXYZ/MaaFramework/releases/tags/v6.0.0-alpha.1"
        )


if __name__ == "__main__":
    unittest.main()
