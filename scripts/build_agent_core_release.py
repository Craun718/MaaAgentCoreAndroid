"""Prepare for and run agent-core release builds."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import maafw_release
from build_agent_core import (
    BuildError,
    archive_mtime,
    format_archive_mtime,
    normalize_maafw_version,
    normalize_python_version,
)
from github import write_job_output

SCRIPT_ROOT = Path(__file__).resolve().parent


PACKAGES = (
    "build-essential",
    "pkg-config",
    "curl",
    "unzip",
    "libssl-dev",
    "zlib1g-dev",
    "libbz2-dev",
    "libreadline-dev",
    "libsqlite3-dev",
    "libffi-dev",
    "liblzma-dev",
)


def install_dependencies() -> None:
    subprocess.run(["sudo", "apt-get", "update"], check=True)
    subprocess.run(
        ["sudo", "apt-get", "install", "-y", "--no-install-recommends", *PACKAGES],
        check=True,
    )


def build(
    python_version: str,
    maafw_version: str,
    work_dir: Path,
    maafw_published_at: str | None,
    repository: str,
) -> None:
    python_version = normalize_python_version(python_version)[0]
    maafw_version = normalize_maafw_version(maafw_version)

    if maafw_published_at is None:
        release = maafw_release.release_for_version(maafw_version, repository)
        published_at = release.published_at
    else:
        published_at = maafw_published_at

    resolved_work_dir = work_dir.resolve()
    published_at = format_archive_mtime(archive_mtime(published_at))
    # Build inputs are normalized, and the interpreter/script paths are fixed.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_ROOT / "build_agent_core.py"),
            "--python-version",
            python_version,
            "--maafw-version",
            maafw_version,
            "--maafw-published-at",
            published_at,
            "--work-dir",
            str(resolved_work_dir),
        ],
        check=True,
        shell=False,
    )

    metadata_path = resolved_work_dir / "dist" / "build-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    write_job_output(
        python_version=metadata["pythonVersion"],
        maafw_version=metadata["maafwVersion"],
        artifact_name=(
            f"agent-core-{metadata['pythonVersion']}-maafw{metadata['maafwVersion']}"
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install-dependencies", help="install required host packages")

    build_parser = subparsers.add_parser(
        "build", help="build and validate release archives"
    )
    build_parser.add_argument("--python-version", required=True)
    build_parser.add_argument("--maafw-version", required=True)
    build_parser.add_argument("--work-dir", type=Path, required=True)
    build_parser.add_argument("--maafw-published-at")
    build_parser.add_argument("--repository", default=maafw_release.UPSTREAM_REPOSITORY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "install-dependencies":
        install_dependencies()
        return
    build(
        args.python_version,
        args.maafw_version,
        args.work_dir,
        args.maafw_published_at,
        args.repository,
    )


if __name__ == "__main__":
    try:
        main()
    except (
        BuildError,
        OSError,
        subprocess.CalledProcessError,
        KeyError,
        maafw_release.MaafwReleaseError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
