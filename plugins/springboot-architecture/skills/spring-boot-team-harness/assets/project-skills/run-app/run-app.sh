#!/usr/bin/env bash
# Starts this Spring Boot service in the background, calls its endpoints, and stops it, so an agent can check
# behaviour on the running app. It lives in <Maven project>/.claude/skills/run-app/ and works in that project.
set -u
cd "$(dirname "$0")/../../.." || exit 1

DIR=target/run-app
LOG=$DIR/app.log
PORT=${RUN_APP_PORT:-18080}
TIMEOUT=${RUN_APP_TIMEOUT:-240}
BASE=http://localhost:$PORT

usage() {
  cat >&2 <<'EOF'
Usage: run-app.sh start | status | call METHOD PATH [JSON_BODY] | logs [LINES] | stop
  RUN_APP_PORT      port to start on (default 18080)
  RUN_APP_PROFILES  Spring profiles to activate
  RUN_APP_TOKEN     bearer token to send with each call
  RUN_APP_COOKIE    Cookie header to send with each call; an XSRF-TOKEN in it is also sent as X-XSRF-TOKEN
EOF
  exit 2
}

is_windows() { [ "${OS:-}" = Windows_NT ]; }

listener() {
  if is_windows; then
    netstat -ano -p tcp | awk -v port=":$PORT" '$2 ~ port"$" && $4 == "LISTENING" { print $5; exit }'
  elif command -v lsof > /dev/null; then
    lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2> /dev/null | head -1
  else
    ss -ltnp 2> /dev/null | awk -v port=":$PORT" '$4 ~ port"$" { match($0, /pid=[0-9]+/); print substr($0, RSTART + 4, RLENGTH - 4); exit }'
  fi
}

end_process() {
  if is_windows; then
    taskkill //PID "$1" //T //F > /dev/null 2>&1
  else
    kill "$1" 2> /dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$1" 2> /dev/null || return 0; sleep 1; done
    kill -9 "$1" 2> /dev/null
  fi
}

started() { [ -f "$DIR/port" ] && [ "$(cat "$DIR/port")" = "$PORT" ] && [ -n "$(listener)" ]; }

stop() {
  if [ -f "$DIR/port" ]; then
    pid=$(listener)
    [ -n "$pid" ] && end_process "$pid"
  fi
  [ -f "$DIR/maven.pid" ] && kill "$(cat "$DIR/maven.pid")" 2> /dev/null
  rm -f "$DIR/port" "$DIR/maven.pid"
  echo "stopped"
}

start() {
  if started; then
    echo "already running at $BASE"
    return 0
  fi
  if [ -n "$(listener)" ]; then
    echo "port $PORT is taken by another process; set RUN_APP_PORT to a free port" >&2
    return 1
  fi
  mkdir -p "$DIR"
  arguments="--server.port=$PORT"
  [ -n "${RUN_APP_PROFILES:-}" ] && arguments="$arguments --spring.profiles.active=$RUN_APP_PROFILES"
  nohup ./mvnw -q spring-boot:run "-Dspring-boot.run.arguments=$arguments" > "$LOG" 2>&1 &
  echo $! > "$DIR/maven.pid"
  echo "$PORT" > "$DIR/port"

  waited=0
  while [ "$waited" -lt "$TIMEOUT" ]; do
    if grep -qE 'Started [A-Za-z0-9_$]+ in [0-9.]+ seconds' "$LOG"; then
      echo "running at $BASE (log: $LOG)"
      return 0
    fi
    if grep -qE 'APPLICATION FAILED TO START|BUILD FAILURE' "$LOG" || ! kill -0 "$(cat "$DIR/maven.pid")" 2> /dev/null; then
      echo "the app did not start. End of $LOG:" >&2
      tail -n 40 "$LOG" >&2
      stop > /dev/null
      return 1
    fi
    sleep 2
    waited=$((waited + 2))
  done
  echo "the app did not start within $TIMEOUT s (RUN_APP_TIMEOUT). End of $LOG:" >&2
  tail -n 40 "$LOG" >&2
  stop > /dev/null
  return 1
}

call() {
  [ $# -ge 2 ] || usage
  if ! started; then
    echo "the app isn't running; run start first" >&2
    return 1
  fi
  options=(-s -o "$DIR/response" -w '%{http_code}' -X "$1" -H 'Accept: application/json')
  [ -n "${RUN_APP_TOKEN:-}" ] && options+=(-H "Authorization: Bearer $RUN_APP_TOKEN")
  if [ -n "${RUN_APP_COOKIE:-}" ]; then
    options+=(-H "Cookie: $RUN_APP_COOKIE")
    xsrf=$(printf '%s' "$RUN_APP_COOKIE" | tr ';' '\n' | sed -n 's/^ *XSRF-TOKEN=//p' | head -1)
    [ -n "$xsrf" ] && options+=(-H "X-XSRF-TOKEN: $xsrf")
  fi
  [ $# -ge 3 ] && options+=(-H 'Content-Type: application/json' --data "$3")
  status=$(curl "${options[@]}" "$BASE$2") || { echo "the request failed: is the app still running?" >&2; return 1; }
  echo "HTTP $status"
  head -c 4000 "$DIR/response"
  echo
}

case "${1:-}" in
  start) start ;;
  status) if started; then echo "running at $BASE"; else echo "not running"; fi ;;
  call) shift; call "$@" ;;
  logs) tail -n "${2:-60}" "$LOG" ;;
  stop) stop ;;
  *) usage ;;
esac
