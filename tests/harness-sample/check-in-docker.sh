#!/usr/bin/env bash
# Runs check.sh in Linux, for machines where it can't run directly: on Windows, baseline.py calls mvnw.cmd, which
# check.sh doesn't create. Needs Docker. Same arguments as check.sh (all or marked; default all).
#
# The Maven cache stays in the harness-m2 volume between runs. The memory cap stops Docker Desktop killing the
# container halfway through the JDK builds.
set -euo pipefail
cd "$(dirname "$0")/../.."
repo=$(pwd -W 2> /dev/null || pwd)
# Git Bash rewrites /repo-style arguments to Windows paths unless told not to.
MSYS_NO_PATHCONV=1 exec docker run --rm --memory=4g \
  -v "$repo:/repo:ro" -v harness-m2:/root/.m2 \
  -e PYTHONDONTWRITEBYTECODE=1 -e MVN=mvn -e MAVEN_OPTS=-Xmx1g \
  maven:3.9-eclipse-temurin-25 bash -c '
    apt-get update -qq > /dev/null && apt-get install -y -qq git python3 perl > /dev/null 2>&1
    git config --global --add safe.directory "*"
    bash /repo/tests/harness-sample/check.sh "$@"' check "${1:-all}"
