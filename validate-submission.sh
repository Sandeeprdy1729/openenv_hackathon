#!/usr/bin/env bash
# validate-submission.sh — OpenEnv Submission Validator

set -uo pipefail

DOCKER_BUILD_TIMEOUT=600

# Set up colors for output
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BOLD='' NC=''
fi

log() { printf "%b\n" "$*"; }
pass() { log "${GREEN}✅ $1${NC}"; }
fail() { log "${RED}❌ $1${NC}"; }
hint() { log "${YELLOW}💡 $1${NC}"; }
stop_at() { fail "Validation stopped at $1."; exit 1; }

# Timeout function for Docker build
run_with_timeout() {
  local secs="$1"; shift
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@"
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$secs" "$@"
  else
    "$@" &
    local pid=$!
    ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
    local watcher=$!
    wait "$pid" 2>/dev/null
    local rc=$?
    kill "$watcher" 2>/dev/null
    wait "$watcher" 2>/dev/null
    return $rc
  fi
}

if [ $# -lt 1 ]; then
  fail "Usage: $0 <ping_url> [repo_dir]"
  exit 1
fi

PING_URL="$1"
REPO_DIR="${2:-.}"

echo ""
log "${BOLD}========================================${NC}"
log "${BOLD}OpenEnv Pre-Submission Validator${NC}"
log "${BOLD}========================================${NC}"
echo ""

# --- Step 1: Ping HF Space ---
log "${BOLD}Step 1/3: Pinging Hugging Face Space URL${NC} ..."
HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}\n" "$PING_URL")

if [ "$HTTP_STATUS" -eq 200 ]; then
  pass "HF Space is live (HTTP 200)"
else
  fail "HF Space returned HTTP $HTTP_STATUS instead of 200"
  hint "Make sure your @app.get('/') root endpoint is deployed."
  stop_at "Step 1"
fi
echo ""

# --- Step 2: Docker Build ---
log "${BOLD}Step 2/3: Checking Docker build${NC} ..."

if [ -f "$REPO_DIR/Dockerfile" ]; then
  DOCKER_CONTEXT="$REPO_DIR"
elif [ -f "$REPO_DIR/server/Dockerfile" ]; then
  DOCKER_CONTEXT="$REPO_DIR/server"
else
  fail "No Dockerfile found in repo root or server/ directory"
  stop_at "Step 2"
fi

log "  Found Dockerfile in $DOCKER_CONTEXT. Building..."

BUILD_OK=false
BUILD_OUTPUT=$(run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build "$DOCKER_CONTEXT" 2>&1) && BUILD_OK=true

if [ "$BUILD_OK" = true ]; then
  pass "Docker build succeeded"
else
  fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"
  printf "%s\n" "$BUILD_OUTPUT" | tail -20
  stop_at "Step 2"
fi
echo ""

# --- Step 3: OpenEnv Validate ---
log "${BOLD}Step 3/3: Running openenv validate${NC} ..."

if ! command -v openenv &>/dev/null; then
  fail "openenv command not found"
  hint "Install it by running: pip install openenv-core"
  stop_at "Step 3"
fi

VALIDATE_OK=false
VALIDATE_OUTPUT=$(cd "$REPO_DIR" && openenv validate 2>&1) && VALIDATE_OK=true

if [ "$VALIDATE_OK" = true ]; then
  pass "openenv validate passed"
  [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"
else
  fail "openenv validate failed"
  printf "%s\n" "$VALIDATE_OUTPUT"
  stop_at "Step 3"
fi

echo ""
log "${BOLD}========================================${NC}"
log "${GREEN}${BOLD}  All 3/3 checks passed!${NC}"
log "${GREEN}${BOLD}  Your submission is ready to submit.${NC}"
log "${BOLD}========================================${NC}"
echo ""
exit 0