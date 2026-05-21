---
name: "install-pi-package-with-npm-fallback"
description: "Install a Pi package/extension and verify it when GitHub URL installation fails."
version: 1
created: "2026-05-15"
updated: "2026-05-15"
---
## When to Use
Use when installing a Pi package or extension, especially if direct installation from a GitHub URL fails because Pi cannot parse the git source correctly.

## Procedure
1. Try the documented install method first, if provided by the package.
2. If direct GitHub URL installation fails due source parsing or package resolution, try the package's npm name instead:
   - `pi install <npm-package-name>`
3. Verify installation:
   - `pi list`
   - Confirm the package appears under user packages and note its installed path.
4. Check Pi settings if needed:
   - inspect `/root/.pi/agent/settings.json` or the active Pi settings file to confirm the package was registered.
5. Tell the user to restart Pi if the package provides commands or tools that are loaded only at startup.
6. After restart, run or suggest the package-specific setup commands from its docs.

## Pitfalls
- Do not assume a GitHub repo URL is accepted by `pi install`; some packages install reliably only by npm package name.
- A successful install may not expose commands until Pi is restarted.
- Verify with `pi list` rather than relying only on command exit output.

## Verification
- `pi list` shows the installed package in user packages.
- The package entry is present in Pi settings.
- After restart, package commands are available and run successfully.