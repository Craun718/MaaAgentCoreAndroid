"""Look up MaaFramework releases and select a build candidate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from github import (
    GitHubError,
    gh_json,
    gh_text,
    release_exists,
    write_job_output,
    write_step_summary,
)

UPSTREAM_REPOSITORY = "MaaXYZ/MaaFramework"


class MaafwVersionError(ValueError):
    pass


class MaafwReleaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpstreamRelease:
    tag: str
    version: str
    published_at: str
    prerelease: bool


def normalize_version(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(
        r"-(?:beta|b)\.(\d+)",
        lambda match: f"b{int(match.group(1))}",
        value,
    )
    if not re.fullmatch(r"\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?", value):
        raise MaafwVersionError(
            "MaaFramework version must be a release such as 5.12.3, "
            "or a beta such as 5.13.0b1 / 5.13.0-beta.1"
        )
    return value


def is_prerelease(version: str) -> bool:
    return re.search(r"(?:a|b|rc)\d+$", version) is not None


def upstream_tag(version: str) -> str:
    match = re.fullmatch(r"(.+?)(a|b|rc)(\d+)", version)
    if match:
        stage = {"a": "alpha", "b": "beta", "rc": "rc"}[match.group(2)]
        return f"v{match.group(1)}-{stage}.{match.group(3)}"
    return f"v{version}"


def _release(payload: dict[str, object]) -> UpstreamRelease:
    tag = payload.get("tag_name")
    published_at = payload.get("published_at")
    prerelease = payload.get("prerelease")
    if not isinstance(tag, str) or not tag:
        raise MaafwReleaseError("MaaFramework release has no tag name")
    if not isinstance(published_at, str) or not published_at:
        raise MaafwReleaseError(f"MaaFramework {tag} has no published_at")
    if not isinstance(prerelease, bool):
        raise MaafwReleaseError(f"MaaFramework {tag} has invalid prerelease metadata")
    try:
        version = normalize_version(tag.removeprefix("v"))
    except MaafwVersionError as error:
        raise MaafwReleaseError(str(error)) from error
    return UpstreamRelease(
        tag=tag,
        version=version,
        published_at=published_at,
        prerelease=prerelease,
    )


def latest_stable(repository: str = UPSTREAM_REPOSITORY) -> UpstreamRelease:
    return _release(gh_json(f"repos/{repository}/releases/latest"))


def latest_prerelease(repository: str = UPSTREAM_REPOSITORY) -> UpstreamRelease:
    tag = gh_text(
        [
            "api",
            "--paginate",
            f"repos/{repository}/releases?per_page=100",
            "--jq",
            "first(.[] | select(.draft == false and .prerelease == true) | .tag_name)",
        ]
    )
    if not tag:
        raise MaafwReleaseError("No upstream prerelease release was found")
    return _release(gh_json(f"repos/{repository}/releases/tags/{tag}"))


def release_for_version(
    version: str, repository: str = UPSTREAM_REPOSITORY
) -> UpstreamRelease:
    try:
        normalized = normalize_version(version)
    except MaafwVersionError as error:
        raise MaafwReleaseError(str(error)) from error
    tag = upstream_tag(normalized)
    try:
        return _release(gh_json(f"repos/{repository}/releases/tags/{tag}"))
    except GitHubError as error:
        raise MaafwReleaseError(
            f"Cannot resolve MaaFramework {tag}: {error}"
        ) from error


def aarch64_wheel_available(version: str) -> bool:
    url = f"https://pypi.org/pypi/maafw/{version}/json"
    try:
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return False
        raise
    files = payload.get("urls", [])
    return any(
        entry.get("filename", "").endswith("manylinux2014_aarch64.whl")
        for entry in files
    )


def select(kind: str, python_version: str, repository: str) -> None:
    release = (
        latest_prerelease(repository)
        if kind == "prerelease"
        else latest_stable(repository)
    )
    if release.prerelease != (kind == "prerelease"):
        state = "stable" if kind == "prerelease" else "a prerelease"
        raise MaafwReleaseError(f"The selected upstream release is not {state}")

    release_tag = f"agent-core-{python_version}-maafw{release.version}"
    should_build = not release_exists(release_tag)
    pypi_ready = "not-checked"
    if should_build:
        ready = aarch64_wheel_available(release.version)
        pypi_ready = str(ready).lower()
        if not ready:
            print(
                f"::notice::MaaFramework {release.version} is not yet available "
                "as a PyPI aarch64 wheel; skipping build."
            )
            should_build = False

    write_job_output(
        maafw_version=release.version,
        maafw_published_at=release.published_at,
        release_tag=release_tag,
        should_build=should_build,
        pypi_ready=pypi_ready,
    )
    label = "stable MaaFramework" if kind == "release" else "MaaFramework prerelease"
    write_step_summary(
        f"- Latest {label}: `{release.version}`\n"
        f"- Published at: `{release.published_at}`\n"
        f"- Expected release tag: `{release_tag}`\n"
        f"- Build needed: `{str(should_build).lower()}`\n"
        f"- PyPI aarch64 wheel available: `{pypi_ready}`\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="select the next release to build")
    check.add_argument("--kind", choices=("release", "prerelease"), required=True)
    check.add_argument("--python-version", required=True)
    check.add_argument("--repository", default=UPSTREAM_REPOSITORY)
    args = parser.parse_args()
    if args.command == "check":
        select(args.kind, args.python_version, args.repository)


if __name__ == "__main__":
    try:
        main()
    except (
        GitHubError,
        MaafwReleaseError,
        MaafwVersionError,
        OSError,
        URLError,
        json.JSONDecodeError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
