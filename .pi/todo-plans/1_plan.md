# Intended Outcome
Restore functional Clanker Ops extension by decoupling it from external rpiv-todo packages.

# Step-by-Step
1. [ ] Audit .pi/extensions/clanker-ops for remaining references to rpiv-todo or @juicesharp.
2. [ ] Verify dependencies in .pi/extensions/clanker-ops/package.json.
3. [ ] If files are missing, copy from upstream rpiv-todo if possible or implement robust shims.
4. [ ] Ensure local i18n-bridge.ts handles missing SDK gracefully.
5. [ ] Register via pi -e if needed, then test loading.

# Verification
1. Load Clanker Ops UI (/todos).
2. Verify /todos slash command works.
3. Test a todo manipulation.

# Dependencies
None.

# Audit
- Tokens: ~500
