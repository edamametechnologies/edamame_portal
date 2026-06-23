"""
Generate screenshots for EDAMAME Portal pages using Playwright.

Uses a persistent browser profile so Cognito/Amplify auth tokens survive.
Portal base URL: https://portal.edamame.tech

Usage:
    python src/generate_screenshots.py --login
    python src/generate_screenshots.py

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

FEATURES_PATH = Path(__file__).parent.with_name("features.json")
PROFILE_DIR = Path(__file__).parent.with_name(".browser_profile")
DEFAULT_BASE_URL = "https://portal.edamame.tech"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.with_name("screenshots")
VIEWPORT = {"width": 1440, "height": 900}
NAV_WAIT_MS = 5000
LOGIN_POLL_MS = 2000
LOGIN_TIMEOUT_MS = 600_000


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


def ensure_logged_in(page: Page, base_url: str, interactive: bool) -> bool:
    if is_logged_in(page, base_url):
        return True

    if not interactive:
        print("ERROR: Portal session expired or missing.")
        print("Run: python src/generate_screenshots.py --login")
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


def capture(page: Page, output_path: Path):
    page.screenshot(path=str(output_path), full_page=True)
    print(f"    -> {output_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Generate EDAMAME Portal screenshots")
    parser.add_argument("--login", action="store_true", help="Pause for manual login")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--profile-dir", type=Path, default=PROFILE_DIR)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium headless (only when saved session is valid)",
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

        if not ensure_logged_in(page, base, args.login):
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

        context.close()

    captured = list(args.output_dir.glob("*.png"))
    print(f"\nDone! {len(captured)} screenshots in {args.output_dir}")


if __name__ == "__main__":
    main()
