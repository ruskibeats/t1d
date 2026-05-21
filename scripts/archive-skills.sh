#!/usr/bin/env bash
# scripts/archive-skills.sh — Archive all pi skills to .pi/skills-archive/
#
# Moves skills out of the active skill system so they stop loading into
# context, but keeps them available in .pi/skills-archive/ for later
# restoration. Safe to run periodically — it's idempotent.
#
# Scans these locations:
#   /root/.pi/agent/skills/                     — system agent skills
#   .agents/skills/                             — project skills (SKILL.md + standalone .md)
#   /root/.pi/agent/pi-hermes-memory/skills/    — (deprecated, may be empty)
#   /root/.pi/agent/projects-memory/t1d/skills/ — (deprecated, may be empty)
#   .pi/skills/                                 — (deprecated, may be empty)
#
# Packaged skills (pi-intercom, pi-subagents) are NOT archived since they
# come from npm and will re-load on every session.
#
# Usage:
#   ./scripts/archive-skills.sh              # archive everything
#   ./scripts/archive-skills.sh --dry-run    # preview only
#   ./scripts/archive-skills.sh --restore    # restore from archive

set -euo pipefail

ARCHIVE_DIR=".pi/skills-archive"
DRY_RUN=false
RESTORE=false

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --restore) RESTORE=true; shift ;;
    -h|--help)
      head -18 "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Source directories to scan for skills
SRC_DIRS=(
  "/root/.pi/agent/skills"
  ".agents/skills"
  "/root/.pi/agent/pi-hermes-memory/skills"
  "/root/.pi/agent/projects-memory/t1d/skills"
  ".pi/skills"
)

archive_skills() {
  mkdir -p "$ARCHIVE_DIR"
  total=0

  for src_dir in "${SRC_DIRS[@]}"; do
    if [ ! -d "$src_dir" ]; then
      echo "  SKIP  $src_dir (not found)"
      continue
    fi

    # Find SKILL.md in subdirs AND standalone .md files directly in the dir
    files=$(find "$src_dir" \( -name "SKILL.md" -o -name "*.md" \) -maxdepth 2 2>/dev/null | sort -u || true)

    if [ -z "$files" ]; then
      echo "  EMPTY $src_dir"
      continue
    fi

    count=0
    while IFS= read -r file; do
      [ -z "$file" ] && continue
      name=$(basename "$(dirname "$file")")
      # If dirname is the src_dir itself, use the filename without extension
      if [ "$(dirname "$file")" = "$src_dir" ]; then
        name=$(basename "$file" .md)
      fi
      dest="$ARCHIVE_DIR/$name"
      dir=$(dirname "$file")

      if [ "$DRY_RUN" = true ]; then
        echo "  MOVE  $file -> $dest/"
      else
        mkdir -p "$dest"
        cp "$file" "$dest/" 2>/dev/null || true
        # Copy any companion files too
        for ext in json yaml yml toml txt; do
          for f in "$dir/$name.$ext" "$dir/$name/index.$ext"; do
            [ -f "$f" ] && cp "$f" "$dest/" 2>/dev/null || true
          done
        done
        echo "  ARCHIVED $name"
      fi
      count=$((count + 1))
      total=$((total + 1))
    done < <(echo "$files")

    # Remove source files after archiving
    if [ "$DRY_RUN" = false ] && [ "$count" -gt 0 ]; then
      while IFS= read -r file; do
        [ -z "$file" ] && continue
        parent="$(dirname "$file")"
        # Remove the entire skill directory (SKILL.md + any companions)
        rm -rf "$parent" 2>/dev/null || true
      done < <(echo "$files")
      # Also remove standalone .md files in the source dir itself
      find "$src_dir" -maxdepth 1 -name "*.md" -exec rm -f {} + 2>/dev/null || true
      # Clean up empty dirs in source
      find "$src_dir" -type d -empty -delete 2>/dev/null || true
    fi
  done

  echo "---"
  if [ "$DRY_RUN" = true ]; then
    echo "  Dry run: $total skills would be archived"
  else
    echo "  Done: $total skills archived to $ARCHIVE_DIR/"
    echo "  Run with --restore to restore."
  fi
}

restore_skills() {
  if [ ! -d "$ARCHIVE_DIR" ]; then
    echo "  No archive found at $ARCHIVE_DIR/"
    exit 1
  fi

  total=0
  for skill_dir in "$ARCHIVE_DIR"/*/; do
    [ -d "$skill_dir" ] || continue
    name=$(basename "$skill_dir")

    # Pick a target: project skills dir if it exists, else system agent skills
    if [ -d ".agents/skills" ]; then
      dest_dir=".agents/skills/$name"
    elif [ -d "/root/.pi/agent/skills" ]; then
      dest_dir="/root/.pi/agent/skills/$name"
    else
      dest_dir="/root/.pi/agent/projects-memory/t1d/skills/$name"
    fi
    mkdir -p "$dest_dir"
    cp -r "$skill_dir"* "$dest_dir/"
    echo "  RESTORED $name -> $dest_dir"
    total=$((total + 1))
  done

  echo "---"
  echo "  Done: $total skills restored from $ARCHIVE_DIR/"
}

echo "== Pi Skills Archiver =="

if [ "$RESTORE" = true ]; then
  restore_skills
else
  archive_skills
fi
