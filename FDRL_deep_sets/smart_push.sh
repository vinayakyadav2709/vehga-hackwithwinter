#!/bin/bash

# ---------------- Configuration ----------------
BATCH_SIZE=2
DELAYS=(120 300 420 600) # seconds
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------- Safety checks ----------------
cd "$SCRIPT_DIR" || exit 1

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Not a git repository."
  exit 1
fi

# ---------------- Helpers ----------------
get_random_delay() {
  echo "${DELAYS[RANDOM % ${#DELAYS[@]}]}"
}

# ---------------- File selection ----------------
# List files in this directory only:
# - not ignored by .gitignore
# - not the script itself
# - not already committed cleanly
FILES=()
while IFS= read -r f; do
  base="$(basename "$f")"
  if [[ "$base" != "$SCRIPT_NAME" ]]; then
    FILES+=("$f")
  fi
done < <(
  git ls-files --others --modified --exclude-standard -- "$SCRIPT_DIR"
)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "No files to commit."
  exit 0
fi

echo "Found ${#FILES[@]} files to push."

# ---------------- Batch commit & push ----------------
IDX=0
TOTAL=${#FILES[@]}

while [ $IDX -lt $TOTAL ]; do
  COUNT=0
  MSG_PARTS=()

  while [ $COUNT -lt $BATCH_SIZE ] && [ $IDX -lt $TOTAL ]; do
    FILE="${FILES[$IDX]}"
    git add "$FILE"
    MSG_PARTS+=("$(basename "$FILE")")
    IDX=$((IDX + 1))
    COUNT=$((COUNT + 1))
  done

  COMMIT_MSG="Update: $(
    IFS=', '
    echo "${MSG_PARTS[*]}"
  )"
  echo "Committing: $COMMIT_MSG"
  git commit -m "$COMMIT_MSG"

  echo "Pushing..."
  git push

  if [ $IDX -lt $TOTAL ]; then
    DELAY=$(get_random_delay)
    echo "Sleeping for $DELAY seconds."
    sleep "$DELAY"
  fi
done

echo "All files pushed."
