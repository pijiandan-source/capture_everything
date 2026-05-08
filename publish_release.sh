#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository"
  exit 1
fi

REMOTE_NAME="${1:-origin}"
BRANCH_NAME="${2:-work}"
TAG_NAME="${3:-v0.1.0}"

if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  echo "Remote '$REMOTE_NAME' not found."
  echo "Please run: git remote add $REMOTE_NAME <your-github-repo-url>"
  exit 2
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "$BRANCH_NAME" ]]; then
  echo "Switching branch to $BRANCH_NAME"
  git checkout "$BRANCH_NAME"
fi

echo "Pushing branch $BRANCH_NAME to $REMOTE_NAME..."
git push -u "$REMOTE_NAME" "$BRANCH_NAME"

if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
  echo "Tag $TAG_NAME already exists locally."
else
  echo "Creating tag $TAG_NAME"
  git tag "$TAG_NAME"
fi

echo "Pushing tag $TAG_NAME to $REMOTE_NAME..."
git push "$REMOTE_NAME" "$TAG_NAME"

echo "Done."
echo "Now check GitHub Actions > Build Windows EXE and Releases page."
