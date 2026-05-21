---
name: "publish-existing-project-to-github"
description: "Safely initialize and push an existing local project to a GitHub repository."
version: 1
created: "2026-05-15"
updated: "2026-05-15"
---
## When to Use
Use when the user asks to send/push an existing local project directory to a GitHub repository, especially when the repo may not yet be initialized or may be missing ignore rules.

## Procedure
1. Inspect the project root for Git state and ignore rules:
   - `git status` (or check for `.git/`)
   - verify `.gitignore` exists before staging.
2. If `.gitignore` is missing, create one before `git add`. Include common exclusions for the stack and generated artifacts, such as:
   - Python caches and virtualenvs
   - Node dependencies and frontend build outputs
   - local environment files, while allowing example env files
   - OS/editor logs and temp files.
3. Check for likely secrets before committing by searching for generic secret/token/password/key names and provider token prefixes. Distinguish documentation placeholders from real credentials.
4. Check repository size and generated files:
   - `find . -type d \( -name __pycache__ -o -name dist -o -name node_modules -o -name .pytest_cache \) -print`
   - `du -sh .`
5. Initialize if needed: `git init`.
6. Configure identity if Git refuses to commit. Prefer asking the user for identity if not already configured.
7. Stage and commit:
   - `git add .`
   - `git status --short`
   - `git commit -m "Initial commit"`
8. Add or update remote:
   - `git remote add origin <github-url>` if absent
   - `git remote set-url origin <github-url>` if present but wrong.
9. Push to the expected default branch:
   - `git branch -M main`
   - `git push -u origin main`
10. Report the final remote URL and branch.

## Pitfalls
- Do not run `git add .` before creating/checking `.gitignore`; generated files and secrets can be staged accidentally.
- A fresh repo can fail with `fatal: not in a git directory` if commands are run from the wrong directory after a failed initialization or path issue; verify `pwd` and `.git/` before continuing.
- GitHub push may require authentication; if it fails, surface the exact error and ask the user to authenticate or provide the preferred method.
- Treat placeholder keys in docs differently from actual local secret files, but still mention what was checked.

## Verification
- `git status` shows a clean tree after commit/push.
- `git remote -v` points to the requested GitHub repository.
- `git log --oneline -1` shows the commit intended for push.
- The push command succeeds and sets upstream for `main`.