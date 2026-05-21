# DEPLOYMENT.md — T1D Companion Production Deployment Guide

*Last updated: 2026-05-20*

---

## Overview

This document describes how to deploy the T1D Companion to production. The application is a Python FastAPI backend with a React/TypeScript frontend, using PostgreSQL as the database and Redis for task queuing.

---

## Architecture

```
                    ┌─────────────┐
                    │   Nginx /   │
                    │  Cloudflare │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │  FastAPI   │ │React  │ │  Celery   │
        │  Backend   │ │Frontend│ │  Workers  │
        │  (uvicorn) │ │(static)│ │           │
        └─────┬──────┘ └───────┘ └─────┬─────┘
              │                        │
        ┌─────▼────────────────────────▼─────┐
        │           PostgreSQL               │
        └────────────────────────────────────┘
              │
        ┌─────▼─────┐
        │   Redis   │
        └───────────┘
```

---

## Prerequisites

- Ubuntu 22.04+ (or compatible Linux)
- Python 3.12+
- Node.js 20+ (for frontend build)
- PostgreSQL 16+
- Redis 7+
- Nginx (or equivalent reverse proxy)
- Domain name with SSL certificate

---

## Environment Variables

Create `/opt/t1d/.env`:

```bash
# Application
ENVIRONMENT=production
SECRET_KEY=<generate-with-openssl-rand-hex-32>
APP_TITLE=T1D Companion

# Database
DATABASE_URL=postgresql+asyncpg://t1d_user:<password>@localhost:5432/t1d_production

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM (at least one required)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...          # optional fallback
ANTHROPIC_API_KEY=sk-ant-...   # optional fallback

# External APIs (optional)
DEXCOM_CLIENT_ID=...
DEXCOM_CLIENT_SECRET=...
NIGHTSCOUT_URL=...
NIGHTSCOUT_API_TOKEN=...
USDA_API_KEY=...

# CORS
CORS_ORIGINS=https://your-domain.com
```

---

## Deployment Steps

### 1. Server Setup

```bash
# Create application user
sudo useradd -r -s /bin/false t1d
sudo mkdir -p /opt/t1d
sudo chown t1d:t1d /opt/t1d

# Install system dependencies
sudo apt update
sudo apt install -y python3.12 python3.12-venv nodejs npm postgresql-16 redis nginx

# Configure PostgreSQL
sudo -u postgres psql -c "CREATE USER t1d_user WITH PASSWORD '<password>';"
sudo -u postgres psql -c "CREATE DATABASE t1d_production OWNER t1d_user;"
```

### 2. Application Setup

```bash
cd /opt/t1d
git clone https://github.com/russell-taylor/T1D-Companion.git .
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Apply database migrations
alembic upgrade head

# Build frontend
cd frontend
npm ci
npm run build
cd ..
```

### 3. Systemd Services

Create `/etc/systemd/system/t1d-backend.service`:

```ini
[Unit]
Description=T1D Companion Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=t1d
WorkingDirectory=/opt/t1d
EnvironmentFile=/opt/t1d/.env
ExecStart=/opt/t1d/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/t1d-celery.service`:

```ini
[Unit]
Description=T1D Companion Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=t1d
WorkingDirectory=/opt/t1d
EnvironmentFile=/opt/t1d/.env
ExecStart=/opt/t1d/venv/bin/celery -A app.celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable t1d-backend t1d-celery
sudo systemctl start t1d-backend t1d-celery
```

### 4. Nginx Configuration

Create `/etc/nginx/sites-available/t1d`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend (static build)
    location / {
        root /opt/t1d/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket (for chat streaming)
    location /api/v1/chat/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/t1d /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Health Check

```bash
curl https://your-domain.com/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "T1D Companion",
  "version": "0.1.0",
  "environment": "production",
  "timestamp": "2026-05-20T12:00:00+00:00",
  "checks": {
    "database": "connected",
    "llm": "configured (openrouter)"
  }
}
```

---

## Database Backup

```bash
# Manual backup
./scripts/backup_db.sh --output /opt/t1d/backups --compress --retain 30

# Automated daily backup (crontab)
0 2 * * * cd /opt/t1d && ./scripts/backup_db.sh --output /opt/t1d/backups --compress --retain 30
```

---

## Monitoring

### Service Status

```bash
sudo systemctl status t1d-backend
sudo systemctl status t1d-celery
```

### Logs

```bash
# Backend logs
journalctl -u t1d-backend -f

# Celery logs
journalctl -u t1d-celery -f

# Nginx access log
tail -f /var/log/nginx/access.log
```

### Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| API response time | > 500ms | > 2000ms |
| Error rate | > 1% | > 5% |
| DB connection pool | > 80% used | > 95% used |
| Disk usage | > 70% | > 90% |
| Memory usage | > 80% | > 95% |

---

## Updating

```bash
cd /opt/t1d
git pull origin main
source venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# Rebuild frontend if changed
cd frontend && npm ci && npm run build && cd ..

sudo systemctl restart t1d-backend t1d-celery
```

---

## Rollback

```bash
cd /opt/t1d
git revert HEAD
alembic downgrade -1
sudo systemctl restart t1d-backend t1d-celery
```

---

## Security Checklist

- [ ] `SECRET_KEY` is a cryptographically random 32+ byte hex string
- [ ] `DATABASE_URL` uses a dedicated application user with minimal privileges
- [ ] `CORS_ORIGINS` is set to the production domain only (not `*`)
- [ ] SSL/TLS is configured and HTTP redirects to HTTPS
- [ ] Rate limiting is enabled (`rate_limit_requests: 100`, `rate_limit_window: 60`)
- [ ] File upload size is limited (`max_upload_size: 10MB`)
- [ ] Database backups are encrypted at rest
- [ ] API keys are stored in environment variables, not in code
- [ ] `/health` endpoint does not expose sensitive configuration

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 502 Bad Gateway | Backend not running | `sudo systemctl restart t1d-backend` |
| DB connection errors | Pool exhausted or DB down | Check `postgresql.service`, increase `pool_size` |
| LLM timeout | Provider API slow/down | Check provider status, verify API key |
| Static files 404 | Frontend not built | Run `npm run build` in `frontend/` |
| Migration failure | Schema conflict | Run `alembic downgrade -1` then `alembic upgrade head` |
