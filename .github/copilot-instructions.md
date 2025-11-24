<!--
  This file is generated/updated by an AI assistant for repository-specific
  guidance to GitHub Copilot / coding agents. Keep this concise and focused
  on discoverable facts in the repo so an agent can be immediately productive.
-->

# Copilot instructions for ESTER-Grid

This repository is currently minimal. The guidance below is based only on
files and folders present in the workspace (checked on 2025-11-24).

- **Project layout (discoverable)**:
  - `README.md` — repository README (currently only a title).
  - `MVP_terminal/` — a top-level folder that is currently empty.

- **High-level summary**:
  - There is no build system, tests, or source code present yet. Treat this
    repo as a scaffold for a future project (likely an MVP terminal tool
    based on the folder name). Do not assume languages, frameworks, or
    CI configuration unless you find them in new commits.

- **When you (the agent) are asked to make changes**:
  - Prefer small, explicit changes and explain assumptions in the PR body.
  - Before implementing features, add or request a short design note in
    `MVP_terminal/README.md` explaining language/runtime choice (e.g., Python,
    Node, Rust) so reviewers understand the intent.
  - If adding new tooling, include minimal run instructions in the root
    `README.md` and a `README.md` under the affected package directory.

- **Conventions to follow (repo-specific and discoverable)**:
  - Keep commits small and focused; this is an early-stage repo.
  - Name new top-level folders with clear purpose (e.g., `cli/`, `server/`,
    `web/`) and add a `README.md` inside each explaining how to build/run.
  - Add a simple `LICENSE` file if license is known — do not assume one.

- **Examples from this repo**:
  - `MVP_terminal/` is the logical place to add an MVP implementation. Place
    source files under a language-named subfolder (e.g., `MVP_terminal/python/`)
    and provide `README.md` and quick run commands.

- **Developer workflows (what an agent should suggest or add when relevant)**:
  - Add a `Makefile` or `README.md` containing development commands when a
    language or framework is chosen. Keep commands explicit (example:
    `pwsh -c "python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"`).
  - If adding tests, include a short example test and a command to run it.

- **Integration points & external dependencies**:
  - No integrations are present. When introducing external services (APIs,
    cloud providers, or packages), add a short `INTEGRATIONS.md` describing
    required environment variables and local emulation options.

- **What not to do (based on current state)**:
  - Do not remove or rewrite the root `README.md` without adding useful
    content in its place. If you update it, keep the change focused and add
    usage/run instructions for any new code.

If anything here is unclear or you'd like the file to adopt a different
structure (for example, more prescriptive language rules or CI templates),
tell me what to include and I will update this file.
