"""Validate and publish an agent-core release artifact bundle."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from github import GitHubError, release_exists, run_gh


class ArtifactError(RuntimeError):
    pass


class PublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseBundle:
    directory: Path
    archives: tuple[Path, ...]
    checksums: Path
    metadata: Path
    report: Path


def _load_bundle(directory: Path) -> ReleaseBundle:
    checksums = directory / "SHA256SUMS"
    metadata = directory / "build-metadata.json"
    report = directory / "build-report.md"
    archives = tuple(sorted(directory.glob("agent-core-*.tar.gz")))
    if len(archives) != 2:
        raise ArtifactError(
            f"Expected two agent-core archives in {directory}, found {len(archives)}"
        )
    for artifact in (checksums, metadata, report):
        if not artifact.is_file():
            raise ArtifactError(f"Missing release artifact: {artifact}")
    return ReleaseBundle(
        directory=directory,
        archives=archives,
        checksums=checksums,
        metadata=metadata,
        report=report,
    )


def _verify_checksums(bundle: ReleaseBundle) -> None:
    for line_number, line in enumerate(
        bundle.checksums.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        try:
            expected, filename = line.split(maxsplit=1)
        except ValueError as error:
            raise ArtifactError(f"Invalid SHA256SUMS line {line_number}") from error
        filename = filename.strip()
        relative = Path(filename)
        if len(expected) != 64 or any(
            character.lower() not in "0123456789abcdef" for character in expected
        ):
            raise ArtifactError(f"Invalid SHA-256 on line {line_number}")
        if relative.is_absolute() or ".." in relative.parts:
            raise ArtifactError(f"Unsafe SHA256SUMS path: {filename}")
        artifact = bundle.directory / relative
        if not artifact.is_file():
            raise ArtifactError(f"SHA256SUMS references missing file: {filename}")
        actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if actual != expected:
            raise ArtifactError(f"SHA-256 mismatch for {filename}")


def _require_commit() -> str:
    commit = os.environ.get("GITHUB_SHA")
    if not commit:
        raise PublishError("GITHUB_SHA is required to create a release")
    return commit


def _write_notes(bundle: ReleaseBundle, prerelease: bool) -> None:
    extra = (
        "\nThis is a prerelease build and has not been validated on Android devices.\n\n"
        if prerelease
        else "\n"
    )
    extra += (
        "\n## Installation\n\n"
        "The archives contain the Python agent core only. Install the matching\n"
        "MaaFramework Android native libraries from the official\n"
        "[MaaFramework release](https://github.com/MaaXYZ/MaaFramework/releases)\n"
        "in the Android host application.\n"
    )
    notes = bundle.directory / "release-notes.md"
    notes.write_text(
        bundle.report.read_text(encoding="utf-8") + extra,
        encoding="utf-8",
    )


def publish(release_tag: str, release_dir: Path, prerelease: bool) -> None:
    bundle = _load_bundle(release_dir)
    _verify_checksums(bundle)
    _write_notes(bundle, prerelease)
    files = [
        *bundle.archives,
        bundle.checksums,
        bundle.metadata,
        bundle.report,
    ]

    if release_exists(release_tag):
        run_gh(
            [
                "release",
                "upload",
                release_tag,
                *[str(path) for path in files],
                "--clobber",
            ],
            check=True,
        )
        return

    run_gh(
        [
            "release",
            "create",
            release_tag,
            *[str(path) for path in files],
            "--target",
            _require_commit(),
            "--title",
            release_tag,
            "--notes-file",
            str(bundle.directory / "release-notes.md"),
            *(["--prerelease"] if prerelease else []),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--prerelease", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    publish(args.release_tag, args.release_dir, args.prerelease)


if __name__ == "__main__":
    try:
        main()
    except (
        ArtifactError,
        PublishError,
        GitHubError,
        OSError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
