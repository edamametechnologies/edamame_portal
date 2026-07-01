# EDAMAME Portal

## Overview

EDAMAME Portal is the subscription and device management interface for EDAMAME Security and EDAMAME Posture. Manage your LLM subscription plans, API keys, connected devices, and account settings.

**Portal**: [portal.edamame.tech](https://portal.edamame.tech)

**Note: The portal application source lives in `edamame-core-services`. This repository is used for feature documentation, screenshots, and the wiki pipeline.**

## Key Features

- **Home** — Device overview, Cloud LLM usage metrics (tokens, threats, policies, network, traffic, identity), device registration
- **Plans** — Subscription tiers (Vip, Free, Pro, Max), monthly/yearly billing, upgrade/downgrade
- **API Keys** — Create, list, and revoke API keys for headless/CLI access
- **Notifications** — Device security notifications (action reports, escalations, vulnerabilities, divergences) with filters
- **Settings** — Change password, account preferences

## Feature Wiki

Full feature descriptions with screenshots: [github.com/edamametechnologies/edamame_portal/wiki](https://github.com/edamametechnologies/edamame_portal/wiki)

## Screenshot Generation

### Automatic (CI)

The **Generate Portal Screenshots** workflow (`.github/workflows/screenshots.yml`)
captures every page from production using the **demo account**, then rebuilds and
republishes the feature wiki. It runs on a weekly schedule and on demand
(Actions → *Generate Portal Screenshots* → *Run workflow*).

Required repository **secrets**:

| Secret | Purpose |
|--------|---------|
| `PORTAL_SCREENSHOT_EMAIL` | Demo account email (`demo@edamame.tech`) |
| `PORTAL_SCREENSHOT_PASSWORD` | Demo account password |
| `DEV_GITHUB_TOKEN` | PAT with repo + wiki write access (already used by the wiki workflow) |

Posture gating reuses the existing `EDAMAME_POSTURE_*` secrets/vars.

### Manual (local)

```bash
pip install -r requirements.txt
playwright install chromium

# Unattended — log in with the demo account (same path as CI)
PORTAL_SCREENSHOT_EMAIL=demo@edamame.tech \
PORTAL_SCREENSHOT_PASSWORD=... \
python src/generate_screenshots.py --headless

# Or interactively (saves the session in a persistent profile for reuse)
python src/generate_screenshots.py --login
python src/generate_screenshots.py

# Commit PNGs, then push — feature-wiki.yml updates the GitHub wiki
git add screenshots/ && git commit -m "docs: refresh Portal screenshots"
```

## Wiki Generation

```bash
python src/build_feature_wiki.py --screenshots-dir screenshots --output-dir wiki
```

## Repository Structure

```
├── features.json
├── screenshots/
├── src/
│   ├── generate_screenshots.py
│   └── build_feature_wiki.py
├── .github/workflows/
│   ├── feature-wiki.yml     # rebuilds wiki from committed PNGs (on push)
│   └── screenshots.yml      # captures screenshots (demo account) + republishes wiki
└── requirements.txt
```
