# Deployment Readiness Checklist

Use this checklist before each production release.

## 1) Pre-deploy gates

- `main` branch is green in GitHub Actions.
- Backend checks pass: lint, format, type-check, tests.
- Frontend checks pass: type-check and build.
- No critical open incidents.

## 2) Required configuration

Set these before deploy:

- `APP_ENV=production`
- `ALLOWED_ORIGINS` set to explicit trusted origins (no `*` in production)
- `API_KEY` set for backend protection
- `OLLAMA_HOST` set to a valid `http(s)://host:port` URL
- `OLLAMA_MODEL` set to a deployed model name
- `IMAGE_MODEL`, `VIDEO_MODEL`, `WHISPER_MODEL`, `PIPER_MODEL` set as needed

Frontend:

- `VITE_BACKEND_URL` points to the live backend URL

## 3) Cloud deploy prerequisites

- GitHub repository secrets are configured:
  - `GCP_WIF_PROVIDER`
  - `GCP_SERVICE_ACCOUNT`
- Artifact Registry repository exists.
- Cloud Run service exists or can be created by workflow.

## 4) Deploy steps

1. Push changes to `main`.
2. Wait for `Deploy Cloud Run (adabtech)` workflow to complete.
3. Wait for `Post Deploy Smoke Test` workflow to complete.

## 5) Smoke validation (must pass)

- `GET /health` returns HTTP 200
- Response includes:
  - `status: sovereign`
  - `version` key present

## 6) Post-deploy checks

- Frontend can reach backend successfully.
- Chat endpoint responds for a basic request in staging/production env.
- Error rate and latency are within acceptable range.

## 7) Rollback plan

If smoke checks fail or error rate spikes:

1. Identify last known-good image tag.
2. Redeploy that image to Cloud Run.
3. Re-run smoke checks.
4. Open an incident note with root cause and fix owner.

## 8) Release notes

Track each deploy with:

- Commit SHA
- Deployed image tag
- Key config changes
- Any known limitations
