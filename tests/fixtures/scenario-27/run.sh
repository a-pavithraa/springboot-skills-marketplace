#!/usr/bin/env bash
# Scenario 27: does telemetry.py help an agent find server failures behind healthy responses?
#   run.sh <work-dir> [runs-per-arm]     needs Docker, Python 3 and the claude CLI
# Each session is capped by BUDGET dollars (default 0.40). Scores are printed; answers.json is never copied to the agent.
set -uo pipefail
WORK=$1
RUNS=${2:-2}
BUDGET=${BUDGET:-0.40}
MODEL=${MODEL:-sonnet}
PORT=18080
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=maven:3.9-eclipse-temurin-25
mkdir -p "$WORK"
WORK=$(cd "$WORK" && pwd)

native() { if command -v cygpath > /dev/null; then cygpath -w "$1"; else echo "$1"; fi; }

BUILD=$WORK/build
rm -rf "$BUILD" && cp -r "$HERE/shop" "$BUILD"
mkdir -p "$BUILD/src/main/resources"
cp "$HERE/application-verify.properties" "$BUILD/src/main/resources/"
MSYS_NO_PATHCONV=1 docker run --rm -v "$(native "$BUILD"):/work" -v scenario27-m2:/root/.m2 -w /work "$IMAGE" \
  mvn -q -B -DskipTests package || exit 1

session() {  # arm, run
  local arm=$1 run=$2 dir=$WORK/$1-$2
  rm -rf "$dir" && mkdir -p "$dir/logs" "$dir/target/verify"
  cp -r "$HERE/shop/src" "$dir/src"
  cp "$BUILD/target/shop-0.0.1.jar" "$dir/logs/.app.jar"
  local prompt
  prompt=$(cat "$HERE/task.md")
  if [ "$arm" = telemetry ]; then
    mkdir "$dir/scripts" && cp "$HERE/telemetry.py" "$dir/scripts/"
    prompt+=$'\n\n'"Run \`python scripts/telemetry.py --app http://localhost:$PORT --help\` first: it shows what the server did for a request. The app log it reads is at its default path."
  fi
  MSYS_NO_PATHCONV=1 docker run -d --name scenario27 -p $PORT:8080 -v "$(native "$dir"):/work" -w /work "$IMAGE" \
    sh -c 'java -jar logs/.app.jar --spring.profiles.active=verify > logs/console.log 2>&1' > /dev/null
  for _ in $(seq 1 40); do curl -sf "localhost:$PORT/actuator/health" > /dev/null && break; sleep 1; done
  (cd "$dir" && claude -p "$prompt" --model "$MODEL" --max-budget-usd "$BUDGET" --output-format json \
     --setting-sources project --strict-mcp-config --tools Bash,Read,Grep \
     --allowedTools Bash Read Grep > "$WORK/$arm-$run.json" 2> "$WORK/$arm-$run.err")
  docker rm -f scenario27 > /dev/null
  python3 "$HERE/score.py" "$HERE/answers.json" "$arm-$run" "$WORK/$arm-$run.json"
}

for run in $(seq 1 "$RUNS"); do
  session baseline "$run"
  session telemetry "$run"
done
