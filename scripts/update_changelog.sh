#!/usr/bin/env bash
# scripts/update_changelog.sh - Automates version header injection

VERSION_FILE="$(dirname "$0")/../VERSION"
CHANGELOG_FILE="$(dirname "$0")/../CHANGELOG.md"

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "Error: VERSION file not found at $VERSION_FILE"
  exit 1
fi

# Clean version string
VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
DATE=$(date +%Y-%m-%d)
NEW_HEADER="## [$VERSION] - $DATE"

# Ensure the changelog exists
touch "$CHANGELOG_FILE"

# Check if this specific version header already exists
if grep -q "## \[$VERSION\]" "$CHANGELOG_FILE"; then
  echo "Header for version $VERSION already exists. No changes made."
else
  # Insert the new version header right after the "## [Unreleased]" line
  # This follows the Keep a Changelog standard
  if grep -q "## \[Unreleased\]" "$CHANGELOG_FILE"; then
    # Use temporary file for compatibility across different sed versions
    sed "/## \[Unreleased\]/a \\
\\
$NEW_HEADER\\
" "$CHANGELOG_FILE" > "${CHANGELOG_FILE}.tmp" && mv "${CHANGELOG_FILE}.tmp" "$CHANGELOG_FILE"
    echo "Injected $NEW_HEADER into $CHANGELOG_FILE"
  else
    # Fallback if [Unreleased] is missing: prepend to top after main header
    echo -e "## [Unreleased]\n\n$NEW_HEADER\n$(cat "$CHANGELOG_FILE")" > "$CHANGELOG_FILE"
    echo "Warning: [Unreleased] header was missing. Re-initialized changelog structure."
  fi
fi
