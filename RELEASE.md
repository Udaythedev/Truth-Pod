# Release & publishing guide

This document describes how to build and publish the Device SDK and backend release artifacts.

Prerequisites
- Python 3.10+ and pip installed.
- gh CLI (GitHub CLI) configured and authenticated if you want to create GitHub Releases programmatically.
- PyPI token or GitHub Packages credentials if publishing to those registries.

Build the Device SDK wheel (locally)
1. Open PowerShell and change to the SDK folder:

```powershell
cd "d:\Code playground\Hackathons\Truth-Pod\backend\device_sdk"
```

2. Build wheel and sdist:

```powershell
.\.venv\Scripts\python -m pip install --upgrade pip build
python -m build
```

This will place artifacts in `dist/`.

Create a GitHub Release and attach artifacts (with gh)
1. Create a draft release from the repo root (replace tag):

```powershell
gh release create v0.1.0 dist/* --title "v0.1.0" --notes-file ../CHANGELOG.md --draft
```

Publish to PyPI (optional)
1. Make sure you have a `~/.pypirc` or `PYPI_API_TOKEN` available.
2. Upload with twine:

```powershell
.\.venv\Scripts\python -m pip install --upgrade pip twine
.\.venv\Scripts\python -m twine upload dist/*
```

Notes
- CI workflows include a job that builds the SDK and uploads artifacts for verification. Publishing to PyPI/GitHub Packages requires adding the appropriate secrets to the repository.
