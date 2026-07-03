"""
Generate screenshots for EDAMAME Portal pages using Playwright.

Authentication (resolved in this order):
  1. Email/password login — for CI and unattended runs. Provide credentials with
     --email/--password or via the PORTAL_SCREENSHOT_EMAIL /
     PORTAL_SCREENSHOT_PASSWORD environment variables. Works headless from a
     clean profile (no saved session needed).
  2. Saved persistent profile — local convenience; an existing Cognito/Amplify
     session is reused so no login is required.
  3. Interactive login (--login) — opens a window for manual login.

Portal base URL: https://portal.edamame.tech

Usage:
    # CI / unattended (credentials from env vars):
    python src/generate_screenshots.py --headless

    # Local — reuse a saved session, or log in manually the first time:
    python src/generate_screenshots.py --login
    python src/generate_screenshots.py

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, sync_playwright

FEATURES_PATH = Path(__file__).parent.with_name("features.json")
PROFILE_DIR = Path(__file__).parent.with_name(".browser_profile")
DEFAULT_BASE_URL = "https://portal.edamame.tech"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.with_name("screenshots")
VIEWPORT = {"width": 1440, "height": 900}
NAV_WAIT_MS = 5000
LOGIN_POLL_MS = 2000
LOGIN_TIMEOUT_MS = 600_000
LOGIN_NAV_TIMEOUT_MS = 45_000

EMAIL_ENV = "PORTAL_SCREENSHOT_EMAIL"
PASSWORD_ENV = "PORTAL_SCREENSHOT_PASSWORD"


def load_features() -> dict:
    with FEATURES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def wait_for_page_ready(page: Page, extra_ms: int = NAV_WAIT_MS):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(extra_ms)


def is_logged_in(page: Page, base_url: str) -> bool:
    url = page.url
    return base_url in url and "/portal/" in url and "/auth/" not in url


def is_on_login_page(page: Page) -> bool:
    return "/auth/" in page.url or "login" in page.url


def programmatic_login(page: Page, base_url: str, email: str, password: str) -> bool:
    """Log in with email/password via the Portal login form (headless-friendly)."""
    print("Logging in with email/password...")
    try:
        page.goto(f"{base_url}/auth/login", wait_until="domcontentloaded")
        page.wait_for_selector('input[type="email"]', timeout=LOGIN_NAV_TIMEOUT_MS)
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(
            lambda url: "/portal/" in url and "/auth/" not in url,
            timeout=LOGIN_NAV_TIMEOUT_MS,
        )
    except Exception as exc:
        print(f"ERROR: Email/password login failed: {exc}")
        if "/auth/" in page.url:
            print(
                "Still on an auth page — check the credentials or for a "
                "verification/MFA step."
            )
        return False

    print("Logged in via email/password.")
    return True


def ensure_logged_in(
    page: Page,
    base_url: str,
    interactive: bool,
    email: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    if is_logged_in(page, base_url):
        return True

    if email and password:
        if programmatic_login(page, base_url, email, password):
            return True
        if not interactive:
            return False

    if not interactive:
        print("ERROR: Portal session expired or missing.")
        print(
            "Provide credentials via --email/--password or the "
            f"{EMAIL_ENV}/{PASSWORD_ENV} env vars, or run with --login."
        )
        return False

    print("=" * 60)
    print("Please log in to the portal in the browser window.")
    print("Complete the full login flow. Wait until you see the portal home.")
    print("=" * 60)

    deadline = time.time() + (LOGIN_TIMEOUT_MS / 1000)
    while not is_logged_in(page, base_url):
        if time.time() > deadline:
            print("ERROR: Timed out waiting for login.")
            return False
        page.wait_for_timeout(LOGIN_POLL_MS)

    print("Logged in! Starting capture...")
    return True


def dismiss_overlays(page: Page):
    """Close stray popups (toasts, welcome/tour modals) before capturing."""
    for selector in [
        "[aria-label='Close']",
        "button:has-text('Close')",
        "button:has-text('Dismiss')",
        ".chakra-modal__close-btn",
    ]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(500)
        except Exception:
            pass


def capture(page: Page, output_path: Path, dismiss: bool = True):
    if dismiss:
        dismiss_overlays(page)
    page.screenshot(path=str(output_path), full_page=True)
    print(f"    -> {output_path.name}")


HIGHLIGHT_JS = """el => {
  el.setAttribute('data-wf-highlight', '1');
  el.dataset.wfPrevOutline = el.style.outline || '';
  el.dataset.wfPrevOffset = el.style.outlineOffset || '';
  el.dataset.wfPrevShadow = el.style.boxShadow || '';
  el.style.outline = '4px solid #ff2d2d';
  el.style.outlineOffset = '3px';
  el.style.boxShadow = '0 0 0 6px rgba(255, 45, 45, 0.35)';
}"""

CLEAR_HIGHLIGHT_JS = """() => {
  const el = document.querySelector('[data-wf-highlight]');
  if (!el) return;
  el.style.outline = el.dataset.wfPrevOutline || '';
  el.style.outlineOffset = el.dataset.wfPrevOffset || '';
  el.style.boxShadow = el.dataset.wfPrevShadow || '';
  el.removeAttribute('data-wf-highlight');
}"""


def apply_highlight(page: Page, selector: str) -> bool:
    """Draw a red rectangle around the element to focus the reader's attention.

    Uses Playwright's selector engine so text selectors (e.g. has-text) work in
    addition to plain CSS.
    """
    try:
        el = page.query_selector(selector)
        if not el or not el.is_visible():
            return False
        el.scroll_into_view_if_needed()
        el.evaluate(HIGHLIGHT_JS)
        return True
    except Exception:
        return False


def clear_highlight(page: Page):
    try:
        page.evaluate(CLEAR_HIGHLIGHT_JS)
    except Exception:
        pass


def run_action(page: Page, base_url: str, action: dict):
    """Run a single non-destructive workflow action.

    Supported types: goto, click, fill, wait. There is deliberately no
    'submit' type so captured workflows never trigger destructive operations.
    """
    action_type = action.get("type")
    if action_type == "goto":
        path = action.get("path", "")
        page.goto(f"{base_url}/{path}", wait_until="domcontentloaded")
        wait_for_page_ready(page)
    elif action_type == "click":
        el = page.query_selector(action["selector"])
        if el and el.is_visible():
            el.click()
            page.wait_for_timeout(500)
    elif action_type == "fill":
        el = page.query_selector(action["selector"])
        if el and el.is_visible():
            el.fill(action.get("value", ""))
    elif action_type == "wait":
        page.wait_for_timeout(int(action.get("ms", 1000)))
    else:
        print(f"    WARN: unknown action type '{action_type}', skipping")


def capture_workflows(page: Page, base_url: str, workflows: list, output_dir: Path):
    """Capture one screenshot per workflow step, fully driven by features.json.

    Adding/editing/removing a workflow or step needs no code change here.
    Each step is isolated: a broken selector logs a WARN and never aborts the run.
    """
    if not workflows:
        return

    print(f"\nCapturing {len(workflows)} workflows...\n")
    for wf in workflows:
        wf_name = wf.get("name", "workflow")
        print(f"[workflow: {wf_name}] {wf.get('title', {}).get('en', '')}")

        for i, step in enumerate(wf.get("steps", []), 1):
            step_name = step.get("name", f"step{i}")
            path = step.get("path", "") or ""
            filename = f"wf_{wf_name}_{i:02d}_{step_name}.png"
            out = output_dir / filename

            # A dynamic path (contains {...}) can't be resolved statically.
            if path and "{" in path:
                print(f"  {step_name}: skipped (dynamic param: {path})")
                continue

            try:
                # An empty path means "stay on the current page" so multi-click
                # flows (e.g. open -> fill) keep their state.
                if path:
                    url = f"{base_url}/{path}"
                    print(f"  {step_name}: {url}")
                    page.goto(url, wait_until="domcontentloaded")
                    wait_for_page_ready(page)

                    if is_on_login_page(page):
                        print("    WARN: Redirected to login. Session may have expired.")
                        continue
                else:
                    print(f"  {step_name}: (continue on current page)")

                # Clear stray popups (welcome, toasts) BEFORE running actions so
                # an intentional modal opened by the actions survives the shot.
                dismiss_overlays(page)

                for action in step.get("actions", []):
                    run_action(page, base_url, action)

                highlighted = False
                highlight = step.get("highlight")
                if highlight:
                    highlighted = apply_highlight(page, highlight)
                    if not highlighted:
                        print(f"    WARN: highlight target not found: {highlight}")

                # dismiss=False: keep modals/popovers the step intentionally opened.
                capture(page, out, dismiss=False)

                if highlighted:
                    clear_highlight(page)
            except Exception as exc:
                print(f"    WARN: step '{step_name}' failed ({exc}); continuing.")


def main():
    parser = argparse.ArgumentParser(description="Generate EDAMAME Portal screenshots")
    parser.add_argument("--login", action="store_true", help="Pause for manual login")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--profile-dir", type=Path, default=PROFILE_DIR)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headless (CI, or when a saved session is valid)",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get(EMAIL_ENV),
        help=f"Login email for unattended runs (or set {EMAIL_ENV})",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get(PASSWORD_ENV),
        help=f"Login password for unattended runs (or set {PASSWORD_ENV})",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")

    data = load_features()
    features = data.get("features", [])
    mappings = data.get("screenshot_metadata", {}).get("sub_feature_mappings", {})

    print(f"Profile: {args.profile_dir}")
    print(f"Base:    {base}")
    print(f"Output:  {args.output_dir}")
    print(f"Headless: {args.headless}")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(args.profile_dir),
            headless=args.headless,
            viewport=VIEWPORT,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(f"{base}/portal/home", wait_until="domcontentloaded")
        wait_for_page_ready(page)

        if not ensure_logged_in(page, base, args.login, args.email, args.password):
            context.close()
            raise SystemExit(1)

        page.goto(f"{base}/portal/home", wait_until="domcontentloaded")
        wait_for_page_ready(page)

        if not is_logged_in(page, base):
            print("ERROR: Still on login page. Auth failed.")
            context.close()
            raise SystemExit(1)

        print(f"Authenticated. Capturing {len(features)} features...\n")

        for feature in features:
            fname = feature["title"]["en"]
            print(f"[{feature['name']}] {fname}")

            for sf in feature.get("sub_features", []):
                name = sf["name"]
                path = sf.get("path", "")
                mapping = mappings.get(name, {})
                prefix = mapping.get("prefix", "00")
                filename = f"{prefix}_{name}.png"
                out = args.output_dir / filename

                url = f"{base}/{path}"
                print(f"  {name}: {url}")
                page.goto(url, wait_until="domcontentloaded")
                wait_for_page_ready(page)

                if not is_logged_in(page, base):
                    print("    WARN: Redirected to login.")
                    continue

                capture(page, out)

        capture_workflows(page, base, data.get("workflows", []), args.output_dir)

        context.close()

    captured = list(args.output_dir.glob("*.png"))
    print(f"\nDone! {len(captured)} screenshots in {args.output_dir}")


if __name__ == "__main__":
    main()
