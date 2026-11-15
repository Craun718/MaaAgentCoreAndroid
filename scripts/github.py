"""GitHub CLI and Actions output helpers."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


class GitHubError(RuntimeError):
    pass


def run_gh(
    arguments: list[str], *, capture: bool = False, check: bool = False
) -> subprocess.CompletedProcess[str]:
    command = ["gh", *arguments]
    # gh is fixed, and caller values remain separate argv entries with shell disabled.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
    result = subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
        shell=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() if capture else ""
        raise GitHubError(f"GitHub CLI request failed ({' '.join(command)}): {detail}")
    return result


def gh_json(endpoint: str) -> dict[str, object]:
    result = run_gh(["api", endpoint], capture=True)
    if result.returncode != 0:
        raise GitHubError(
            f"GitHub API request failed for {endpoint}: {result.stderr.strip()}"
        )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise GitHubError(f"GitHub API returned a non-object for {endpoint}")
    return value


def gh_text(arguments: list[str]) -> str:
    result = run_gh(arguments, capture=True)
    if result.returncode != 0:
        raise GitHubError(
            f"GitHub CLI request failed ({' '.join(arguments)}): "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def release_exists(tag: str) -> bool:
    result = run_gh(
        ["release", "view", tag, "--json", "tagName"],
        capture=True,
    )
    return result.returncode == 0


def write_job_output(**values: str | bool) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(
        f"{key}={str(value).lower() if isinstance(value, bool) else value}\n"
        for key, value in values.items()
    )
    if output is None:
        print(lines, end="")
        return
    with Path(output).open("a", encoding="utf-8") as handle:
        handle.write(lines)


def write_step_summary(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary is None:
        print(text, end="")
        return
    with Path(summary).open("a", encoding="utf-8") as handle:
        handle.write(text)
