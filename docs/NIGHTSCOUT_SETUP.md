# Nightscout Setup Guide

Connect your CGM to the T1D Companion in under 10 minutes using Nightscout — the open-source, self-hosted CGM data platform.

**Why Nightscout?**
- ✅ **No legal risk** — open source, user-controlled
- ✅ **CGM agnostic** — works with Dexcom, Libre, and others
- ✅ **Most reliable** — proven platform, large community
- ✅ **Full data history** — not limited by vendor APIs
- ✅ **Free** — or ~$5/month if you use a cloud host

---

## Option 1: Deploy Nightscout (5 minutes)

### Using Fly.io (easiest — free tier available)

```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh

# 2. Clone the Nightscout template
git clone https://github.com/nightscout/cgm-remote-monitor.git
cd cgm-remote-monitor

# 3. Deploy
fly launch
```

When prompted, set these environment variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `API_SECRET` | `your-secure-password` | You'll use this as your API token |
| `MONGODB_URI` | *(create free MongoDB Atlas)* | [Atlas free tier](https://www.mongodb.com/atlas) |
| `DISPLAY_UNITS` | `mg/dL` or `mmol/L` | Match your CGM |
| `ENABLE` | `careportal` | Optional features |

### Using Railway (zero config)

1. Go to [railway.app](https://railway.app)
2. Click **New Project** → **Deploy from template** → **Nightscout**
3. Set the same environment variables
4. Railway provides a URL like `https://yourapp.up.railway.app`

### Using Heroku (free tier no longer available — ~$5/month)

[Heroku Nightscout guide](https://nightscout.github.io/nightscout/new_user/)

---

## Option 2: Use an Existing Nightscout Instance

If you already run Nightscout, you just need:

| Field | How to find it |
|-------|---------------|
| **Nightscout URL** | Your deployed URL (e.g. `https://my-nightscout.herokuapp.com`) |
| **API Token** | Your `API_SECRET` — or create a [role-based token](https://nightscout.github.io/nightscout/security/) |

---

## Connecting to T1D Companion

Once your Nightscout instance is running:

1. Open T1D Companion → **Settings** → **CGM Connection**
2. Select **Nightscout**
3. Enter your Nightscout URL (e.g. `https://my-site.up.railway.app`)
4. Enter your API token
5. Click **Connect**

Your glucose data will start syncing immediately.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Connection refused" | Make sure your Nightscout URL is HTTPS, not HTTP |
| "Authentication failed" | Check your API token — it's your `API_SECRET` env var value |
| No data showing | Verify your CGM is uploading to Nightscout (check NS directly first) |
| Readings are delayed | Nightscout polls every ~5 minutes by default |

---

## Which Integration Should I Use?

| Your Setup | Recommended Path | Why |
|-----------|-----------------|-----|
| **Any CGM** | **Nightscout** ✅ | Works with everything, zero legal risk, full data history |
| **Dexcom** (US only) | Dexcom OAuth | Official API, no setup needed, low risk |
| **Libre** (EU/UK) | Nightscout (recommended) or LibreLinkUp | LibreLinkUp is a convenience fallback (reverse-engineered API) |

### Dexcom Users

If you use Dexcom, you have two good options:

1. **Nightscout** — Recommended if you want vendor independence, data history, or use multiple CGM sources
2. **Dexcom OAuth** — Fastest setup, official API, works if you're in the US

Both are low-risk. Nightscout gives you more flexibility and works with future CGM changes.

### Libre Users

Nightscout is the best path. LibreLinkUp works as a quick start but uses a reverse-engineered API — Abbott doesn't officially support it. If you use LibreLinkUp, please consider setting up Nightscout when you have 10 minutes.

---

## Going Further

### Shared Nightscout (Future Feature)

For users who don't want to manage their own server, we plan to offer a shared Nightscout instance at **~$0.50-1/user/month**. This handles hosting, backups, and uptime so you don't have to.

[Learn more about hosted Nightscout](link-to-future-feature)