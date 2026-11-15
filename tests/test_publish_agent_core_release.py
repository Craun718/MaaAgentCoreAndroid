from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from publish_agent_core_release import parse_args


class PublishReleaseArgumentsTests(unittest.TestCase):
    @patch.object(
        sys,
        "argv",
        [
            "publish_agent_core_release.py",
            "--release-tag",
            "agent-core-3.13.15-maafw6.0.0a1",
            "--release-dir",
            "release",
            "--prerelease",
        ],
    )
    def test_release_directory_is_parsed_as_path(self) -> None:
        args = parse_args()

        self.assertEqual(args.release_dir, Path("release"))
        self.assertTrue(args.prerelease)


if __name__ == "__main__":
    unittest.main()
