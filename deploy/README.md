# Automated backend deploy

Replaces the manual SSH → `git pull` → `docker build` → `systemctl restart`
sequence with a GitHub Actions workflow (`.github/workflows/deploy-backend.yml`)
that runs the same steps and then *verifies* them — the exact gap that let a
2026-08-31 deploy silently not restart while `/health` kept reporting
"sovereign" from the stale, un-restarted container the whole time.

## How it authenticates

A dedicated, deploy-only SSH keypair — not the admin's own key. The private
half lives only in this repo's `MURYA_DEPLOY_SSH_KEY` GitHub secret. The
public half is installed on the VM, scoped so it can run exactly one thing:
`deploy/murya-deploy.sh`, via a single-purpose sudoers rule — not raw
`docker`/`systemctl` access. If this key ever leaks, the blast radius is
"can redeploy the current `main`," not "can run arbitrary root commands."

## One-time VM setup

Run these on `murya-vm` (as `adamu`):

```bash
# 1. Allow the deploy key to log in as adamu, restricted to running one
#    forced command (can't be used for anything else even if someone tries
#    to pass a different command over that SSH session).
mkdir -p ~/.ssh
echo 'command="sudo /usr/local/bin/murya-deploy.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPg/VSak2Z7DgN4YgnVG/BZmkt6gWeu8/2VffgsQN6Hv github-actions-deploy@murya' >> ~/.ssh/authorized_keys

# 2. Install the deploy script (pulls from the repo you already have checked out).
sudo cp /home/adamu/hausa-ai/deploy/murya-deploy.sh /usr/local/bin/murya-deploy.sh
sudo chmod 755 /usr/local/bin/murya-deploy.sh

# 3. Scope sudo to exactly that script, nothing else -- validate before installing.
echo 'adamu ALL=(root) NOPASSWD: /usr/local/bin/murya-deploy.sh' | sudo tee /etc/sudoers.d/murya-deploy
sudo visudo -c
```

`sudo visudo -c` must print `parsed OK` — if it doesn't, delete
`/etc/sudoers.d/murya-deploy` and stop; the rest of `sudo` still works
regardless (a syntax error only breaks that one file, but check anyway).

## What the workflow does

1. Triggers on push to `main` touching `backend/**`, `data/processed/**`
   (the dictionary sources are baked into the image too), or the workflow/
   deploy script files themselves — plus `workflow_dispatch` for a manual run.
2. SSHs in with the deploy key and runs `murya-deploy.sh`, which pulls,
   builds with the commit SHA baked in, restarts, and polls `/health`.
3. The script itself fails loudly (non-zero exit, clear message) if the
   live `/health` commit doesn't match what was just built -- the CI job
   then fails too, instead of quietly reporting green on a stale deploy.

## Updating the script

Edit `deploy/murya-deploy.sh` in the repo and redeploy as normal -- but the
version actually enforced by `sudo` is the copy at
`/usr/local/bin/murya-deploy.sh` on the VM, which does NOT auto-update.
Re-run step 2 above after any change to keep them in sync.

## Moving to a different host

`murya-deploy.sh` is not tied to one machine or cloud. Host-specific values
come from `/etc/murya/deploy.env` (must be **root-owned** -- the script
refuses to source it otherwise, since it runs as root). Defaults match the
current production VM, so a host without this file behaves as before.

```bash
sudo mkdir -p /etc/murya
sudo tee /etc/murya/deploy.env >/dev/null <<'EOF2'
REPO_DIR="/srv/hausa-ai"
SERVICE="murya.service"
HEALTH_URL="https://api.example.org/health"
BRANCH="main"
EOF2
sudo chown root:root /etc/murya/deploy.env && sudo chmod 644 /etc/murya/deploy.env
```

The checkout is pulled as whoever owns `REPO_DIR`. Also update the
`HEALTH_URL`/hostname in `deploy/Caddyfile` and the workflow's SSH host secret.
See `docs/sovereignty_plan.md` for the full hosting-independence plan.
