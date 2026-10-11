#!/usr/bin/env bash
# Regenerate the project-structure tree in README.md between the markers:
#   <!-- STRUCTURE:START --> ... <!-- STRUCTURE:END -->
# Run it whenever you add/move folders:  ./scripts/update-structure.sh
set -euo pipefail

cd "$(dirname "$0")/.."
README="README.md"

TREE_FILE="$(mktemp)"
OUT_FILE="$(mktemp)"
trap 'rm -f "$TREE_FILE" "$OUT_FILE"' EXIT

# Build the tree from files git knows about (tracked + untracked, not ignored), so
# .venv/, caches and data never show up. Two levels deep, folders marked with "/".
git ls-files --cached --others --exclude-standard \
  | awk -F/ 'NF == 1 { print; next }
             { print $1 "/"; print $1 "/" $2 (NF > 2 ? "/" : "") }' \
  | LC_ALL=C sort -u \
  | sed -E 's|^[^/]+/(.+)$|    \1|' > "$TREE_FILE"

# Replace the block between the markers. awk reads the tree from a file
# (getline) so there are no multi-line-variable issues on macOS/BSD awk.
awk -v treefile="$TREE_FILE" '
  /<!-- STRUCTURE:START/ {
    print
    print "```"
    while ((getline line < treefile) > 0) print line
    close(treefile)
    print "```"
    skip = 1
    next
  }
  /<!-- STRUCTURE:END/ { skip = 0 }
  skip != 1 { print }
' "$README" > "$OUT_FILE"

mv "$OUT_FILE" "$README"
trap - EXIT
rm -f "$TREE_FILE"
echo "Updated project structure in $README"
