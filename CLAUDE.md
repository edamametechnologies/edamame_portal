# CLAUDE.md — edamame_portal

> **Feature documentation, screenshots, and wiki generation for EDAMAME Portal.**
> This repo is documentation-only: it defines Portal features (`features.json`),
> captures screenshots against the live Portal (portal.edamame.tech), and
> rebuilds the GitHub wiki. The Portal frontend source lives in
> `edamame-core-services`.

Cursor also loads the scoped rule at `.cursor/rules/feature-wiki.mdc` (same
pipeline, glob-scoped). Keep this file and that `.mdc` in sync via the central
`edamame_rules` repo.

## Overview

```
features.json → generate_screenshots.py (local Playwright) → screenshots/*.png
             → commit + push → feature-wiki.yml (CI) → GitHub wiki
```

| Step | Where | What |
|------|-------|------|
| 1. Define routes | `features.json` | Feature/sub-feature paths + i18n copy |
| 2. Capture PNGs | **Local** `src/generate_screenshots.py` | Playwright vs live Portal |
| 3. Commit | `edamame_portal/screenshots/` | PNGs are source of truth |
| 4. Wiki | CI `feature-wiki.yml` | `build_feature_wiki.py` → `edamame_portal.wiki` |

**Screenshots are captured manually on a developer machine** (Playwright against
production). CI only rebuilds the GitHub wiki from committed PNGs — unlike
`edamame_security`, which captures via Flutter golden tests in `edamame_app` CI.

## Prerequisites

```bash
cd edamame_portal
pip install -r requirements.txt
playwright install chromium
```

## Screenshot capture (manual, local)

### First run — save Cognito session

```bash
python src/generate_screenshots.py --login
```

1. Chromium opens (headed).
2. Complete Cognito login.
3. Wait until `portal/home` loads — the script auto-continues.
4. Auth is stored in `.browser_profile/` (gitignored).

### Subsequent runs — reuse session

```bash
python src/generate_screenshots.py
```

Re-run after Portal UI changes. If you see `session expired`, use `--login` again.

**Headless** (only when session is still valid):

```bash
python src/generate_screenshots.py --headless
```

### What gets captured

- Viewport: 1440×900, full-page PNG
- Filename: `{prefix}_{subfeature_name}.png` (e.g. `01_home_main.png`)
- Routes: `portal/home`, `portal/subscribe`, `portal/settings`, `portal/api-keys`

### After capture

```bash
# Preview wiki locally (optional)
python src/build_feature_wiki.py --screenshots-dir screenshots --output-dir wiki

# Commit screenshots, then push — CI updates the wiki
git add screenshots/ features.json
git commit -m "docs: refresh Portal feature screenshots"
git push origin main
```

## features.json structure

```json
{
  "screenshot_metadata": {
    "sub_feature_mappings": {
      "home_main": { "prefix": "01" },
      "subscribe_main": { "prefix": "02" }
    }
  },
  "features": [
    {
      "name": "home",
      "sub_features": [
        { "name": "home_main", "path": "portal/home" }
      ]
    }
  ]
}
```

## CI workflow (wiki only)

- **Trigger:** push to `main` or `workflow_dispatch`
- **Does NOT** run Playwright or re-capture screenshots
- Reads committed `screenshots/`, runs `build_feature_wiki.py`, pushes to `edamametechnologies/edamame_portal.wiki`

## Adding a new feature

1. Ship the Portal UI in `edamame-core-services`
2. Add feature + `sub_feature_mappings` + `path` in `features.json`
3. Run `generate_screenshots.py` locally (`--login` if needed)
4. Commit PNGs + `features.json`, push — wiki updates on `main`

## Comparison with edamame_security

| | Portal | Security app |
|---|--------|----------------|
| Capture | Manual Playwright vs production | Automated Flutter goldens in `edamame_app` CI |
| Auth | Interactive Cognito (`.browser_profile/`) | Demo mode, no login |
| CI | Wiki build only | Screenshot commit + wiki build |
