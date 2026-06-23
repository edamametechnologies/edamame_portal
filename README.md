# EDAMAME Portal

## Overview

EDAMAME Portal is the subscription and device management interface for EDAMAME Security and EDAMAME Posture. Manage your LLM subscription plans, API keys, connected devices, and account settings.

**Portal**: [portal.edamame.tech](https://portal.edamame.tech)

**Note: The portal application source lives in `edamame-core-services`. This repository is used for feature documentation, screenshots, and the wiki pipeline.**

## Key Features

- **Home** — Device overview, usage metrics (tokens, threats, policies, network, traffic, identity), device registration
- **Plans** — Subscription tiers (Free, Pro, Enterprise), monthly/yearly billing, upgrade/downgrade
- **API Keys** — Create, list, and revoke API keys for headless/CLI access
- **Settings** — Change password, account preferences

## Feature Wiki

Full feature descriptions with screenshots: [github.com/edamametechnologies/edamame_portal/wiki](https://github.com/edamametechnologies/edamame_portal/wiki)

## Screenshot Generation

Screenshots are captured **manually on your machine** (Playwright against
production). CI only rebuilds the wiki from committed PNGs.

```bash
pip install -r requirements.txt
playwright install chromium

# First run: log in interactively to save auth state
python src/generate_screenshots.py --login

# Subsequent runs: reuse saved auth
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
│   └── feature-wiki.yml
└── requirements.txt
```
