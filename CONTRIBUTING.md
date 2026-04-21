# Contributing to Hausa-AI

First off, thank you for taking the time to contribute! 🎉  
Hausa-AI is an open-source project dedicated to building high-quality AI tooling for the Hausa language and Arewa culture.

---

## How to contribute

### 1. Report a bug

Open an issue using the **Bug report** template and include:
- Steps to reproduce
- Expected vs. actual behaviour
- Environment (OS, browser / Node / Python versions)

### 2. Request a feature

Open an issue using the **Feature request** template.  
Describe your use-case before proposing a solution — it helps the community discuss it.

### 3. Submit a pull request

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes following the code style guidelines below.
3. Write or update tests as needed (`backend/tests/`).
4. Run pre-commit hooks before pushing:
   ```bash
   pip install pre-commit
   pre-commit install
   pre-commit run --all-files
   ```
5. Open a pull request against `main` using the **PR template**.

---

## Development setup

See [`backend/README.md`](backend/README.md) for the full backend setup, or use the one-command Docker Compose stack:

```bash
docker compose up --build
```

### Frontend

```bash
npm install
npm run dev       # dev server
npm run typecheck # TypeScript check
npm run build     # production build
```

### Backend tests

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

---

## Code style

| Layer    | Tool   | Command                |
|----------|--------|------------------------|
| Python   | ruff   | `ruff check --fix .`   |
| Python   | mypy   | `mypy .`               |
| Frontend | tsc    | `npm run typecheck`    |

Pre-commit hooks enforce these automatically on every commit.

---

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Hausa dialect selector
fix: correct Piper WAV header offset
docs: update deployment guide
chore: pin GitHub Actions to SHA
```

---

## Code of Conduct

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).  
We are committed to providing a welcoming and inclusive environment.
