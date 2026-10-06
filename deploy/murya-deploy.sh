#!/usr/bin/env bash
# Deploys the backend on murya-vm: pull -> build (with the commit baked in
# for /health to report) -> restart -> wait -> verify.
#
# This is the ONLY thing the deploy SSH key's sudo access is scoped to (see
# deploy/README.md) -- deliberately not raw docker/systemctl commands,
# so a compromised deploy credential can run exactly this fixed sequence
# and nothing else.
#
# Run as: sudo /usr/local/bin/murya-deploy.sh
# (installed as a copy of this file -- see deploy/README.md)

set -euo pipefail

# Host-specific settings live in /etc/murya/deploy.env (root-owned) so this
# script is not tied to one machine, one user or one cloud -- moving hosts
# means writing that file, not editing code. The defaults below are the
# current production values, so an existing host with no file behaves exactly
# as before. The file is sourced as root, so it must stay root-owned.
CONFIG_FILE="${MURYA_DEPLOY_ENV:-/etc/murya/deploy.env}"
REPO_DIR="/home/adamu/hausa-ai"
SERVICE="murya.service"
HEALTH_URL="https://api.murya.ng/health"
BRANCH="main"
if [ -f "$CONFIG_FILE" ]; then
  if [ "$(stat -c %u "$CONFIG_FILE")" != "0" ]; then
    echo "::error:: $CONFIG_FILE must be owned by root (it is executed as root)."
    exit 1
  fi
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
fi

cd "$REPO_DIR"
# Pull as whoever owns the checkout rather than a hardcoded user name.
REPO_OWNER="$(stat -c %U "$REPO_DIR")"
echo "==> Pulling latest $BRANCH as $REPO_OWNER..."
sudo -u "$REPO_OWNER" git pull origin "$BRANCH"

SHA="$(git rev-parse HEAD)"
echo "==> Building image for commit $SHA..."
docker build -f backend/Dockerfile -t murya-backend:latest --build-arg "GIT_SHA=$SHA" .

echo "==> Restarting $SERVICE..."
systemctl restart "$SERVICE"

echo "==> Waiting for the service to come up..."
for i in $(seq 1 15); do
  sleep 2
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
    break
  fi
done

echo "==> Verifying the deployed commit matches..."
DEPLOYED_SHA="$(curl -sf "$HEALTH_URL" | grep -o '"commit":"[^"]*"' | cut -d'"' -f4 || echo "")"

if [ "$DEPLOYED_SHA" != "$SHA" ]; then
  echo "::error:: Deploy verification failed."
  echo "  expected commit: $SHA"
  echo "  live /health reports: ${DEPLOYED_SHA:-<no response>}"
  echo "This is exactly the failure mode from 2026-08-31: the restart"
  echo "didn't actually take effect and the old code kept serving traffic."
  exit 1
fi

echo "==> Deploy verified: $SERVICE is running $SHA"
