# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| latest `main` | ✅ |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Send a detailed report to the maintainers by emailing **security@adab.tech** (or open a [GitHub private security advisory](../../security/advisories/new)).

Include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

We aim to acknowledge reports within **48 hours** and provide a resolution timeline within **7 days**.

## Scope

| Area | Notes |
|------|-------|
| FastAPI backend (`backend/`) | In scope |
| React frontend (`src/`) | In scope |
| Docker Compose / Dockerfile | In scope |
| GitHub Actions workflows | In scope |
| Third-party ML models (Ollama, HuggingFace) | Out of scope — report upstream |

## Security considerations for self-hosted deployments

- Set the `API_KEY` environment variable to protect backend endpoints when exposed to a network.
- Set `ALLOWED_ORIGINS` to your frontend origin rather than `*` in production.
- Run Ollama and the backend on a private network; do not expose port `11434` publicly.
- Keep Python and Node.js dependencies up to date (Dependabot PRs are enabled).
