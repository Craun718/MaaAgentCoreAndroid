#!/usr/bin/env bash
set -euo pipefail

android_home="${ANDROID_HOME:?ANDROID_HOME must be set}"
tools_url="${ANDROID_COMMAND_LINE_TOOLS_URL:-https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip}"
runner_temp="${RUNNER_TEMP:-/tmp}"
tools_zip="$runner_temp/android-command-line-tools.zip"
license_answers="$runner_temp/android-license-answers.txt"
trap 'rm -f "$license_answers"' EXIT
mkdir -p "$android_home" "$runner_temp"

if [[ ! -x "$android_home/cmdline-tools/latest/bin/sdkmanager" ]]; then
    mkdir -p "$android_home/cmdline-tools"
    curl -fL --retry 5 --retry-all-errors -o "$tools_zip" "$tools_url"
    unzip -q "$tools_zip" -d "$android_home/cmdline-tools"
    mv "$android_home/cmdline-tools/cmdline-tools" "$android_home/cmdline-tools/latest"
fi

printf 'y\n%.0s' {1..100} >"$license_answers"
"$android_home/cmdline-tools/latest/bin/sdkmanager" --licenses <"$license_answers" >/dev/null
"$android_home/cmdline-tools/latest/bin/sdkmanager" --install platform-tools

if [[ -n "${GITHUB_ENV:-}" ]]; then
    printf 'ANDROID_HOME=%s\n' "$android_home" >>"$GITHUB_ENV"
fi
