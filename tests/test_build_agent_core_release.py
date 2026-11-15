from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_agent_core import BuildError
from build_agent_core_release import SCRIPT_ROOT, build


class BuildAgentCoreReleaseTests(unittest.TestCase):
    @patch("build_agent_core_release.write_job_output")
    @patch("build_agent_core_release.subprocess.run")
    def test_build_normalizes_arguments_and_disables_shell(
        self, subprocess_run, write_job_output
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            dist = work_dir / "dist"
            dist.mkdir()
            (dist / "build-metadata.json").write_text(
                json.dumps(
                    {
                        "pythonVersion": "3.13.15",
                        "maafwVersion": "6.0.0a1",
                    }
                ),
                encoding="utf-8",
            )

            build(
                " 3.13.15 ",
                "v6.0.0-alpha.1",
                work_dir,
                "2026-11-14T16:03:25Z",
                "MaaXYZ/MaaFramework",
            )

        command = subprocess_run.call_args.args[0]
        self.assertEqual(
            command,
            [
                sys.executable,
                str(SCRIPT_ROOT / "build_agent_core.py"),
                "--python-version",
                "3.13.15",
                "--maafw-version",
                "6.0.0a1",
                "--maafw-published-at",
                "2026-11-14T16:03:25Z",
                "--work-dir",
                str(work_dir.resolve()),
            ],
        )
        self.assertFalse(subprocess_run.call_args.kwargs["shell"])
        write_job_output.assert_called_once()

    @patch("build_agent_core_release.subprocess.run")
    def test_build_rejects_invalid_python_version_before_spawning(
        self, subprocess_run
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(BuildError):
                build(
                    "3.13.15; touch /tmp/injected",
                    "6.0.0a1",
                    Path(temp_dir),
                    "2026-11-14T16:03:25Z",
                    "MaaXYZ/MaaFramework",
                )

        subprocess_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
