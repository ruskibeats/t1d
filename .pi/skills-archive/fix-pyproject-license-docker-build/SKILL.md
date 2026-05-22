---
name: "fix-pyproject-license-docker-build"
description: "Fix Docker build failure when pyproject.toml with hatchling references a LICENSE file that doesn't exist in the build context, causing OSError from pip install."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix Docker Build Failure — pyproject.toml LICENSE Missing

## When to Use

- Docker build fails with `OSError: [Errno 2] No such file or directory: '/some/path/LICENSE'` during `pip install .` or `pip install --no-cache-dir .`
- `pyproject.toml` uses hatchling or a build backend that reads `[project] license-files = ["LICENSE"]` or similar
- The `LICENSE` file is referenced in `pyproject.toml` but doesn't exist in the Docker build context or wasn't copied in the builder stage

Use this when the build backend (hatchling, setuptools, pdm-backend, etc.) tries to locate a file declared in `pyproject.toml` and fails because that file isn't in the Docker image's build stage.

## Procedure

1. **Confirm the error signature**
   ```
   OSError: [Errno 2] No such file or directory: '/path/LICENSE'
   ```
   Usually appears after `pip install` in the Docker build output.

2. **Check pyproject.toml for the file reference**
   ```bash
   grep -n 'license-files\|license_file\|license' pyproject.toml
   ```
   Look for entries like:
   ```toml
   license-files = ["LICENSE"]
   # or
   license = {file = "LICENSE"}
   ```

3. **Create a LICENSE file in the project root** (if missing)
   ```bash
   # Minimal MIT placeholder — adjust as needed
   cat > LICENSE << 'EOF'
   MIT License

   Copyright (c) $(date +%Y) <your-organization>

   Permission is hereby granted, free of charge...
   EOF
   ```
   Or copy a real license file from another source.

4. **Add `COPY LICENSE ./` to the Dockerfile builder stage**
   ```dockerfile
   # Place BEFORE the pip install step, after copying pyproject.toml
   COPY pyproject.toml ./
   COPY LICENSE ./           # <-- add this line
   RUN pip install --no-cache-dir .
   ```
   If your Dockerfile uses a multi-stage build, add it to the builder stage where `pip install` runs.

5. **Rebuild and verify**
   ```bash
   docker build --no-cache -t your-image .
   ```

## Pitfalls

- **Not just Docker**: This error can also occur in CI/CD pipelines or fresh clones where LICENSE was intentionally omitted. The same fix applies — ensure LICENSE exists before pip install.
- **`.dockerignore` interference**: If `.dockerignore` excludes `LICENSE`, the COPY directive won't help. Check `.dockerignore` for `LICENSE` or `*.md` patterns that might exclude it.
- **License location mismatch**: If pyproject.toml references `"LICENSE.txt"` or `"LICENSE.md"`, create that exact filename.
- **Build backend differences**: hatchling uses `license-files`; older setuptools uses `license_file`. Check the actual publish / build backend guide.
- **Not just Python**: Any build system that validates declared files before building can hit similar errors.

## Verification

- `docker build` completes successfully with exit code 0.
- `pip install` step no longer fails with OSError.
- The LICENSE file is present in the final image: `docker run --rm your-image cat LICENSE` works.