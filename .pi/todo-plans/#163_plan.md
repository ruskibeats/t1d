# Clanker Ops #163: [OPS] Nightscout Configuration

Status: pending
Owner: @tom_웃
Tags: #ops #nightscout #infrastructure #configuration
Branch: `nightscout-config`

## Intended Outcome

A fully configured Nightscout (cgm-remote-monitor) instance serving CGM data to the T1D Companion app, with the following in place:
- Nightscout server running locally (or reachable from this server)
- `NIGHTSCOUT_URL` and `NIGHTSCOUT_API_TOKEN` set in `.env` to real values (not placeholders)
- Per-user `nightscout_url` / `nightscout_connected` fields in the DB model wired for multi-user support
- `scripts/test_nightscout.py` passes end-to-end
- Sync service (`app/services/sync_service.py`) can pull glucose data successfully
- Documentation written for future DevOps reference

## Step-by-Step

### Phase 1: Discovery & Assessment

1. **Verify existing Nightscout instances**:
   - Check if anything is listening on port 4000, 1337, or 3000: `ss -tlnp | grep -E '4000|1337|3000'`
   - Check if Docker daemon is running: `systemctl status docker` — if stopped, try `systemctl start docker`
   - Check if any Nightscout containers exist: `docker ps -a --filter name=nightscout`
   - Check if there's a Nightscout install elsewhere on the machine: `find /opt /usr/local /home -name "cgm-remote-monitor" -type d 2>/dev/null`

2. **Assess network access to existing remote instance**:
   - The original plan mentions `195.168.0.150:1337` — verify if it's reachable: `curl -s http://195.168.0.150:1337/api/v1/status`
   - If reachable, update `.env` with remote URL (simpler than local install)

3. **Determine approach**:
   - If a local Docker/metal instance exists but is stopped → start it
   - If remote instance is reachable → configure `.env` to use it
   - If nothing exists → **Phase 2: Local installation**

### Phase 2: Local Nightscout Installation (if needed)

4. **Set up MongoDB**:
   ```bash
   docker pull mongo:7
   docker run -d --name nightscout-mongo \
     -p 27017:27017 \
     -v nightscout_data:/data/db \
     -e MONGO_INITDB_ROOT_USERNAME=admin \
     -e MONGO_INITDB_ROOT_PASSWORD=<generate-password> \
     mongo:7
   ```
   - Create a dedicated Nightscout database + user

5. **Install cgm-remote-monitor**:
   ```bash
   cd /opt
   git clone https://github.com/nightscout/cgm-remote-monitor.git
   cd cgm-remote-monitor
   git checkout master
   npm install
   ```
   - Note: Node.js v22 is installed — Nightscout may need older Node. Use `nvm` or `n` to switch to Node 16/18 if needed.

6. **Configure Nightscout** (`/opt/cgm-remote-monitor/.env`):
   ```
   MONGO_CONNECTION=mongodb://<user>:<pass>@localhost:27017/nightscout
   API_SECRET=<sha1-hashed-secret>
   BASE_URL=http://<hostname>:4000
   DISPLAY_UNITS=mg/dL
   TIME_FORMAT=24
   ```
   - `API_SECRET` must be SHA1-hashed: `echo -n "your-secret" | sha1sum`

7. **Start Nightscout**:
   - Docker option: create Dockerfile or use existing `nightscout/cgm-remote-monitor` image
   - Systemd option: create systemd service for auto-restart
   - Verify: `curl http://localhost:4000/api/v1/status`

### Phase 3: Configuration & Wiring

8. **Connect Nightscout to a CGM data source**:
   - **Dexcom Share**: Configure `DEXCOM_*` env vars in Nightscout env
   - **LibreLinkUp**: Configure `LIBRE_*` env vars if the LibreLinkUp bridge plugin is enabled in Nightscout
   - **Manual upload**: Verify the /api/v1/entries endpoint accepts POST data

9. **Update T1D Companion `.env`**:
   ```bash
   # /root/t1d/.env
   NIGHTSCOUT_URL=http://localhost:4000
   NIGHTSCOUT_API_TOKEN=<nightscout-api-secret>
   ```

10. **Test end-to-end connectivity**:
    ```bash
    cd /root/t1d
    python scripts/test_nightscout.py
    ```

11. **Wire per-user Nightscout configuration** in the DB if multi-user support is needed:
    - The `User` model has `nightscout_url` and `nightscout_connected` fields (`app/models/user.py`)
    - The `sync_service.py` (lines 68-80) checks per-user URL first, then falls back to global `.env`
    - Verify the per-user flow works by creating/updating a user's Nightscout URL via the API
    - Test with: `GET /api/v1/cgm/glucose?source=nightscout`

### Phase 4: Documentation & Handoff

12. **Document the setup**:
    - Write `docs/NIGHTSCOUT_SETUP.md` covering:
      - Installation steps taken
      - Configuration values (redacted)
      - How to restart / monitor
      - How to add new users with Nightscout URLs
      - Troubleshooting common issues

13. **Verify all integration points**:
    - `app/services/nightscout_service.py` — service layer
    - `app/services/sync_service.py` — sync with per-user fallback
    - `app/api/cgm.py` — glucose endpoint
    - `app/api/glucose_ext.py` — extended glucose endpoint
    - Unit tests: `python -m pytest tests/test_nightscout_service.py -v`

## Verification

- [ ] `curl http://localhost:4000/api/v1/status` returns 200 with JSON status
- [ ] `curl http://localhost:4000/api/v1/entries.json?count=1` returns glucose readings (or empty array if none yet)
- [ ] MongoDB container is running: `docker ps | grep nightscout-mongo`
- [ ] `python /root/t1d/scripts/test_nightscout.py` passes with "✓ Connection successful" and reading count
- [ ] `.env` has real `NIGHTSCOUT_URL` and `NIGHTSCOUT_API_TOKEN` (not placeholders)
- [ ] `python -m pytest /root/t1d/tests/test_nightscout_service.py -v` passes
- [ ] `docs/NIGHTSCOUT_SETUP.md` exists and is substantive
- [ ] Per-user Nightscout URL flow works (test via API with a test user)

## Dependencies

- Docker daemon running (if local install) → need to verify/start
- Port 4000 or 1337 available on server
- Node.js (NVM for version switching if needed)
- MongoDB Docker image pulled (for local install)
- Dexcom/LibreLinkUp credentials if connecting to live CGM data
- `#164 [OPS] LibreLinkUp direct API integration` — completed separately, but affected by Nightscout data source choice
- Root/sudo access for Docker and port binding

## Audit (EOD Report-Back)

*To be filled by @tom_웃 at completion:*
- **Tokens consumed**:
- **Files changed**:
- **Stages completed**:
- **Stages deferred**:
- **Unexpected issues**:
- **Artifacts left behind**:
