#!/usr/bin/env bash

set -uo pipefail

if (( $# != 3 )); then
  echo "Usage: $0 <skill-name> <queries.json> <train|validation>" >&2
  exit 2
fi

SKILL_NAME="$1"
QUERIES_FILE="$2"
QUERY_SET="$3"
EVAL_RUNS="${EVAL_RUNS:-1}"
CLAUDE_COMMAND="${CLAUDE_COMMAND:-claude}"

if [[ "$QUERY_SET" != "train" && "$QUERY_SET" != "validation" ]]; then
  echo "error: query set must be 'train' or 'validation'" >&2
  exit 2
fi

if [[ ! "$EVAL_RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: EVAL_RUNS must be a positive integer" >&2
  exit 2
fi

if ! command -v jq >/dev/null; then
  echo "error: jq is required" >&2
  exit 2
fi

if ! command -v "$CLAUDE_COMMAND" >/dev/null; then
  echo "error: Claude Code command not found: $CLAUDE_COMMAND" >&2
  exit 2
fi

if ! jq -e --arg query_set "$QUERY_SET" '
  .[$query_set] as $queries
  | ($queries | type == "array")
    and ($queries | length > 0)
    and ($queries | all(.[];
      (.query | type == "string")
      and (.should_trigger | type == "boolean")
    ))
' "$QUERIES_FILE" >/dev/null; then
  echo "error: $QUERIES_FILE needs a non-empty '$QUERY_SET' array of query labels" >&2
  exit 2
fi

check_triggered() {
  local query="$1"
  local output

  if ! output=$("$CLAUDE_COMMAND" -p "$query" \
    --model haiku \
    --output-format stream-json \
    --verbose \
    --disallowedTools "Bash,Edit,Write,NotebookEdit" \
    2>/dev/null); then
    echo "error: Claude Code failed while evaluating: $query" >&2
    return 2
  fi

  jq -e --arg skill "$SKILL_NAME" '
    select(.type == "assistant")
    | .message.content[]?
    | select(
        .type == "tool_use"
        and .name == "Skill"
        and .input.skill == $skill
      )
  ' <<<"$output" >/dev/null
}

query_count=$(jq -r --arg query_set "$QUERY_SET" '.[$query_set] | length' "$QUERIES_FILE")
failures=0

# Create temp directory for parallel results
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

total_checks=$((query_count * EVAL_RUNS))
echo "Running $query_count queries × $EVAL_RUNS run(s) = $total_checks checks in parallel..."

# Launch all checks in parallel
for ((index = 0; index < query_count; index++)); do
  query=$(jq -r --arg query_set "$QUERY_SET" --argjson index "$index" '.[$query_set][$index].query' "$QUERIES_FILE")

  for ((run = 1; run <= EVAL_RUNS; run++)); do
    (
      if check_triggered "$query"; then
        echo 1 > "$temp_dir/${index}_${run}"
      else
        status=$?
        if (( status == 2 )); then
          echo "ERROR" > "$temp_dir/${index}_${run}"
        else
          echo 0 > "$temp_dir/${index}_${run}"
        fi
      fi
    ) &
  done
done

# Wait for all background jobs
echo "Waiting for checks to complete..."
wait
echo "All checks complete. Processing results..."
echo

# Process results
for ((index = 0; index < query_count; index++)); do
  query=$(jq -r --arg query_set "$QUERY_SET" --argjson index "$index" '.[$query_set][$index].query' "$QUERIES_FILE")
  should_trigger=$(jq -r --arg query_set "$QUERY_SET" --argjson index "$index" '.[$query_set][$index].should_trigger' "$QUERIES_FILE")
  triggers=0

  for ((run = 1; run <= EVAL_RUNS; run++)); do
    result=$(cat "$temp_dir/${index}_${run}")
    if [[ "$result" == "ERROR" ]]; then
      echo "error: Claude Code failed while evaluating: $query" >&2
      exit 2
    fi
    triggers=$((triggers + result))
  done

  passed=false
  if [[ "$should_trigger" == "true" ]] && (( triggers * 2 > EVAL_RUNS )); then
    passed=true
  elif [[ "$should_trigger" == "false" ]] && (( triggers * 2 < EVAL_RUNS )); then
    passed=true
  fi

  if [[ "$passed" == "true" ]]; then
    result="PASS"
  else
    result="FAIL"
    failures=$((failures + 1))
  fi

  printf '%s [%d/%d triggers, expected %s] %s\n' \
    "$result" "$triggers" "$EVAL_RUNS" "$should_trigger" "$query"
done

echo
echo "$((query_count - failures))/$query_count $QUERY_SET queries passed"

if (( failures > 0 )); then
  exit 1
fi
