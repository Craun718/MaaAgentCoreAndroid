from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from github import run_gh


class GitHubCommandTests(unittest.TestCase):
    @patch("github.subprocess.run")
    def test_run_gh_keeps_arguments_separate_and_disables_shell(
        self, subprocess_run
    ) -> None:
        run_gh(["release", "view", "tag; echo injected"])

        subprocess_run.assert_called_once_with(
            ["gh", "release", "view", "tag; echo injected"],
            check=False,
            capture_output=False,
            text=True,
            shell=False,
        )


if __name__ == "__main__":
    unittest.main()
