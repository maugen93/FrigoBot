#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

SERVICE=frigobot
BRANCH="${1:-master}"

echo "==> Checking working tree is clean"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Working tree has uncommitted changes to tracked files, aborting:" >&2
  git status --short >&2
  exit 1
fi

echo "==> Stopping $SERVICE"
sudo systemctl stop "$SERVICE"

echo "==> Fetching $BRANCH"
git fetch origin "$BRANCH"

echo "==> Checking out $BRANCH"
git checkout "$BRANCH"
git merge --ff-only "origin/$BRANCH"

echo "==> Syncing dependencies"
uv sync

echo "==> Starting $SERVICE"
sudo systemctl start "$SERVICE"

sleep 3
if ! systemctl is-active --quiet "$SERVICE"; then
  echo "==> $SERVICE failed to start, recent logs:" >&2
  journalctl -u "$SERVICE" -n 50 --no-pager >&2
  exit 1
fi

echo "==> Deploy OK, $SERVICE is active on branch $BRANCH"
systemctl status "$SERVICE" --no-pager -l | head -5