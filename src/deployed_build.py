"""
Identify the build a site serves, to tell when it was deployed.

EDAMAME Hub and EDAMAME Portal are static single-page apps. Every build gives
its entry script and stylesheet content-hashed names (assets/index-<hash>.js),
and index.html links them, so the sorted list of those names identifies the
deployed build: a new list means a new deploy, the same list means the UI in
production is the one the committed screenshots show.

The repository records the build its committed screenshots were captured from
(screenshots/hub_build.txt in edamame_hub, screenshots/portal_build.txt in
edamame_portal). The screenshot workflow compares it with the live build every
hour and captures again when they differ.

This file is identical in edamame_hub and edamame_portal: change both together.

Usage:
    python src/deployed_build.py --base-url https://portal.edamame.tech
        print the live build
    python src/deployed_build.py --base-url https://portal.edamame.tech \\
        --compare screenshots/portal_build.txt
        exit 0: same build; exit 3: different build or no record yet.

Any other failure (network, HTTP error, a page without hashed assets) exits 1:
a build that could not be read is never reported as "unchanged" or "changed".
Standard library only, so the deploy check needs no pip install.
"""

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EXIT_CHANGED = 3

# <script ... src="..."> and <link ... href="...">, in either attribute order.
ASSET_RE = re.compile(
    r"""<(?:script|link)\b[^>]*?\b(?:src|href)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
# A Vite build output: assets/<name>-<hash>.<ext>, on the site or on its CDN.
HASHED_ASSET_RE = re.compile(r"/assets/([A-Za-z0-9_.-]+-[A-Za-z0-9_-]{8,}\.(?:js|css))$")


def fetch_index(base_url: str, attempts: int = 3) -> str:
    # The query string keeps intermediate caches from answering with an index
    # that predates the deploy; the deploy invalidates the CDN itself.
    url = f"{base_url.rstrip('/')}/?build-check={int(time.time())}"
    request = urllib.request.Request(
        url,
        headers={"Cache-Control": "no-cache", "User-Agent": "edamame-docs-build-check"},
    )
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(10 * attempt)
    raise RuntimeError(f"could not fetch {url}: {last_error}")


def build_fingerprint(html: str) -> str:
    names = set()
    for ref in ASSET_RE.findall(html):
        match = HASHED_ASSET_RE.search(ref.split("?", 1)[0])
        if match:
            names.add(match.group(1))
    if not names:
        raise RuntimeError("no content-hashed assets in index.html: the page layout changed")
    return " ".join(sorted(names))


def read_record(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print the build a site serves, or compare it with a recorded one"
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="origin to read, e.g. https://hub.edamame.tech or https://portal.edamame.tech",
    )
    parser.add_argument("--compare", type=Path, help="record file to compare with")
    args = parser.parse_args()

    try:
        live = build_fingerprint(fetch_index(args.base_url))
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(live)
    if args.compare is None:
        return 0
    recorded = read_record(args.compare)
    if recorded == live:
        print(f"unchanged: {args.compare} records this build", file=sys.stderr)
        return 0
    print(f"changed: {args.compare} records '{recorded or 'nothing'}'", file=sys.stderr)
    return EXIT_CHANGED


if __name__ == "__main__":
    sys.exit(main())
