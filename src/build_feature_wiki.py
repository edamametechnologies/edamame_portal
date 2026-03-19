"""
Generate Markdown wiki pages for each feature defined in features.json.

Usage:
    python src/build_feature_wiki.py --screenshots-dir screenshots --output-dir wiki

Requirements:
    pip install mdutils
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from mdutils.mdutils import MdUtils
from shutil import copy2

FEATURES_PATH = Path(__file__).parent.with_name("features.json")
WIKI_BASE_URL = "https://github.com/edamametechnologies/edamame_portal/wiki"

PREFIX_RE = re.compile(r"^\d+_+")


def load_features() -> Dict:
    with FEATURES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", name.lower())


def wiki_page_url(page_slug: Optional[str] = None) -> str:
    if not page_slug:
        return WIKI_BASE_URL
    return f"{WIKI_BASE_URL}/{page_slug}"


def wiki_image_url(image_name: str) -> str:
    return f"{WIKI_BASE_URL}/images/{image_name}"


def find_screenshot(base_dir: Path, needle: str) -> Optional[Path]:
    needle = needle.lower()
    for p in base_dir.rglob("*.png"):
        stem = PREFIX_RE.sub("", p.stem.lower())
        if stem == needle:
            return p
    return None


def add_feature_badge(md: MdUtils, feature_name: str):
    badge_text = f"Feature: {feature_name}"
    badge_url = f"https://img.shields.io/badge/{badge_text.replace(' ', '%20').replace(':', '%3A')}-blue"
    md.new_line(f"![{badge_text}]({badge_url})")
    md.new_line()


def add_screenshot_with_caption(md: MdUtils, screenshot_path: Path, title: str, caption: str = None):
    if not caption:
        caption = title
    md.new_line()
    md.new_line("---")
    md.new_line()
    md.new_line('<div align="center">')
    md.new_line()
    md.new_line(f"![{title}]({wiki_image_url(screenshot_path.name)})")
    md.new_line()
    md.new_line(f"*{caption}*")
    md.new_line()
    md.new_line("</div>")
    md.new_line()
    md.new_line("---")
    md.new_line()


def write_feature_page(
    feature: Dict,
    screenshots_dir: Path,
    output_dir: Path,
    images_dir: Path,
    used_images: Set[Path],
):
    slug = sanitize_filename(feature["name"])
    title_en = feature["title"]["en"]
    md = MdUtils(file_name=str(output_dir / f"feature-{slug}"), title=title_en)

    md.new_line("---")
    md.new_line()
    add_feature_badge(md, feature["name"])
    md.new_header(level=1, title=f"🔐 {title_en}")
    md.new_line()
    md.new_line("> **Overview**")
    md.new_line(f"> {feature['description']['en']}")
    md.new_line()

    screenshot = find_screenshot(screenshots_dir, feature["name"])
    if screenshot:
        dest = images_dir / screenshot.name
        if dest not in used_images:
            copy2(screenshot, dest)
            used_images.add(dest)
        md.new_header(level=2, title="🖼️ Feature Overview")
        add_screenshot_with_caption(md, dest, title_en, f"Main interface for {title_en}")

    sub_features = feature.get("sub_features", [])
    if sub_features:
        md.new_header(level=2, title="⚙️ Sub-Features")
        md.new_line()

        for i, sub in enumerate(sub_features, 1):
            sub_title = sub["title"]["en"]
            md.new_header(level=3, title=f"{i}. 🔧 {sub_title}")
            md.new_line()
            md.new_line("**Description:**")
            md.new_line(f"{sub['description']['en']}")
            md.new_line()

            sub_shot = find_screenshot(screenshots_dir, sub["name"])
            if sub_shot:
                dest_sub = images_dir / sub_shot.name
                if dest_sub not in used_images:
                    copy2(sub_shot, dest_sub)
                    used_images.add(dest_sub)
                add_screenshot_with_caption(md, dest_sub, sub_title, f"Screenshot of {sub_title}")

            items: List[Dict] = sub.get("items", [])
            if items:
                md.new_header(level=4, title="📝 UI Elements & Data")
                md.new_line()
                for item in items:
                    md.new_line(f"- **{item['title']['en']}**")
                    md.new_line(f"  - {item['description']['en']}")
                    md.new_line()

            if i < len(sub_features):
                md.new_line()
                md.new_line("---")
                md.new_line()

    md.new_header(level=2, title="📋 Contents")
    md.new_table_of_contents(table_title="", depth=3)
    md.new_line()
    md.new_line("---")
    md.new_header(level=2, title="🏠 Navigation")
    md.new_line(f"- [← Back to Feature Overview]({wiki_page_url()})")
    md.new_line(f"- [📖 Full Documentation]({wiki_page_url()})")
    md.new_line()
    md.new_line("---")
    md.new_line("*This page was automatically generated from feature definitions.*")
    md.new_line()

    md.create_md_file()
    print(f"✅ Generated {md.file_name}.md")
    return screenshot


def build_index(pages: List[Dict], output_dir: Path):
    index = MdUtils(file_name=str(output_dir / "Home"), title="EDAMAME Portal - Feature Documentation")
    index.new_line("---")
    index.new_line()
    index.new_line('<div align="center">')
    index.new_line()
    index.new_line("# 🔐 EDAMAME Portal")
    index.new_line("## Feature Documentation")
    index.new_line()
    index.new_line("![EDAMAME](https://img.shields.io/badge/EDAMAME-Portal-blue?style=for-the-badge)")
    index.new_line("![Features](https://img.shields.io/badge/Features-" + str(len(pages)) + "-green?style=for-the-badge)")
    index.new_line()
    index.new_line("</div>")
    index.new_line()
    index.new_line("---")
    index.new_line()
    index.new_line("## 📖 Overview")
    index.new_line()
    index.new_line("> This wiki documents every major feature of EDAMAME Portal with detailed screenshots")
    index.new_line("> and comprehensive descriptions.")
    index.new_line()
    index.new_line("## 🚀 Quick Navigation")
    index.new_line()
    for i, pg in enumerate(pages, 1):
        feature_link = index.new_inline_link(link=wiki_page_url(f"feature-{pg['slug']}"), text=pg["title"])
        index.new_line(f"{i}. {feature_link}")
    index.new_line()
    index.new_line("---")
    index.new_line()
    index.new_line("## 📋 Feature Details")
    index.new_line()
    for pg in pages:
        index.new_line("### " + pg["title"])
        index.new_line()
        if pg["thumb_md"]:
            index.new_line('<div align="center">')
            index.new_line()
            index.new_line(pg["thumb_md"])
            index.new_line()
            index.new_line("</div>")
            index.new_line()
        index.new_line(f"**Description:** {pg['desc']}")
        index.new_line()
        feature_link = index.new_inline_link(link=wiki_page_url(f"feature-{pg['slug']}"), text="📖 View Details")
        index.new_line(f"**Action:** {feature_link}")
        index.new_line()
        index.new_line("---")
        index.new_line()
    index.new_line()
    index.new_line("---")
    index.new_line()
    index.new_line("## ℹ️ About")
    index.new_line()
    index.new_line("- **Repository:** [EDAMAME Portal](https://github.com/edamametechnologies/edamame_portal)")
    index.new_line("- **Documentation:** Auto-generated from feature definitions")
    index.new_line("- **Last Updated:** " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    index.new_line()
    index.new_line("---")
    index.new_line()
    index.new_line('<div align="center">')
    index.new_line()
    index.new_line("*Made with ❤️ by the EDAMAME Team*")
    index.new_line()
    index.new_line("</div>")
    index.new_line()
    index.create_md_file()
    print("✅ Generated Home.md")


def main():
    parser = argparse.ArgumentParser(description="Generate EDAMAME Portal feature wiki pages.")
    parser.add_argument("--screenshots-dir", required=True, type=Path, help="Directory containing PNG screenshots")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd(), help="Where to write markdown files")
    args = parser.parse_args()

    screenshots_dir = args.screenshots_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    used_images: Set[Path] = set()
    index_pages: List[Dict] = []

    print("🚀 Starting wiki generation...")
    print(f"📁 Screenshots: {screenshots_dir}")
    print(f"📁 Output: {output_dir}")
    print()

    data = load_features()
    features = data.get("features", [])
    print(f"📊 Processing {len(features)} features...")
    print()

    for feature in features:
        slug = sanitize_filename(feature["name"])
        thumb = write_feature_page(feature, screenshots_dir, output_dir, images_dir, used_images)
        thumb_md = f"![{feature['title']['en']}]({wiki_image_url(thumb.name)})" if thumb else ""
        index_pages.append(
            {"slug": slug, "title": feature["title"]["en"], "thumb_md": thumb_md, "desc": feature["description"]["en"]}
        )

    print()
    build_index(index_pages, output_dir)
    print()
    print("🎉 Wiki generation complete!")
    print(f"📄 Generated {len(features)} feature pages + 1 index")
    print(f"🖼️ Processed {len(used_images)} screenshots")


if __name__ == "__main__":
    main()
