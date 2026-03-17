# Contributing to NEOSSat Astronomy Image Analysis

Thank you for your interest in contributing! This document explains how to report issues, propose features, and submit code changes so your contribution can be reviewed and merged quickly.


## What to Contribute

- Bug reports and reproducible test cases
- Small, focused pull requests that fix bugs or add features
- Tests and reproducible scripts for image-processing flows

## How to Contribute

- Use Issues to report bugs or request features. Provide steps to reproduce, expected vs actual behavior, and any logs or sample FITS files if possible.
- When you submit a PR, reference the Issue number in the PR description and keep the PR focused on that single issue.

## Tooling and CI

- This project uses `uv` for dependency and environment management; see the [README.md](./README.md) for setup instructions.
- The CI automatically runs formatting, linting, and tests.

## Code Style

Before pushing a branch or opening a PR, run the following check locally:
```bash
uv run black . && uv run isort . && uv run flake8 .
```

`black` and `isort` will modify files in place — commit those changes before pushing. `flake8` only reports issues and will not modify files. PRs that fail any of these checks will not be merged.

## Branching & Commit Guidelines

- Branch from `main`. Use descriptive branch names: `fix/<short-desc>`, `feat/<short-desc>`.
- Use clear, imperative commit messages, e.g., `Fix: crash when loading empty FITS header`.
- Squash work-in-progress commits locally before merging, unless the commit history is intentionally preserved.

## Reporting Security Issues

If you discover a security vulnerability, please do not open a public issue. Instead contact the repository owner directly so it can be handled privately.

## Code of Conduct

Be professional, constructive, and welcoming when interacting with maintainers and contributors.

---

Thanks again for helping improve `NEOSSat-Astronomy-Image-Analysis` — contributions of all sizes are welcome. 
