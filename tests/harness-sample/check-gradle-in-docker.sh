#!/usr/bin/env bash
# Runs check-gradle.sh in Linux, for machines where it can't run directly (on Windows, baseline.py calls gradlew.bat,
# which check-gradle.sh doesn't create). Needs Docker. Same argument as check-gradle.sh (groovy or kotlin).
#
# The Gradle cache stays in the harness-gradle volume between runs.
set -euo pipefail
cd "$(dirname "$0")/../.."
repo=$(pwd -W 2> /dev/null || pwd)
# Git Bash rewrites /repo-style arguments to Windows paths unless told not to.
MSYS_NO_PATHCONV=1 exec docker run --rm --memory=4g \
  -v "$repo:/repo:ro" -v harness-gradle:/root/.gradle \
  -e PYTHONDONTWRITEBYTECODE=1 -e GRADLE_USER_HOME=/root/.gradle \
  gradle:9.8.2-jdk25 bash -c '
    apt-get update -qq > /dev/null && apt-get install -y -qq git python3 perl > /dev/null 2>&1
    git config --global --add safe.directory "*"
    bash /repo/tests/harness-sample/check-gradle.sh "$@"' check "${1:-groovy}"
