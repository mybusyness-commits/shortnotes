#!/usr/bin/env python3
"""
shrtnotes - Core Static Site Generator (SSG)
=============================================
Compiles Markdown study notes, subject indices, legal pages,
sitemap.xml, and robots.txt into a high-performance static website.
"""

import os
import shutil
import json
import math
from datetime import datetime
from pathlib import Path
import yaml
import markdown
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content"
NOTES_DIR = CONTENT_DIR / "notes"
PAGES_DIR = CONTENT_DIR / "pages"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "site"
CONFIG_FILE = BASE_DIR / "config.json"


def load_config():
    """Load main site configuration."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config_data):
    """Save configuration to config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def parse_frontmatter(file_path):
    """Parse YAML frontmatter and Markdown body from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    metadata = {}
    content = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1]) or {}
            except Exception as e:
                print(f"Warning: Failed to parse frontmatter in {file_path}: {e}")
            content = parts[2].strip()

    return metadata, content


def calculate_reading_time(text):
    """Estimate reading time in minutes based on 200 wpm."""
    words = len(text.split())
    minutes = math.ceil(words / 200)
    return max(1, minutes)


def markdown_to_html(md_text):
    """
    Convert Markdown to clean HTML while preserving KaTeX math delimiters ($ and $$).
    """
    md = markdown.Markdown(
        extensions=[
            "extra",          # tables, attr_list, def_list, fenced_code
            "codehilite",     # code syntax styling
            "toc",            # table of contents
            "nl2br",          # newline to br
            "sane_lists"      # clean list nesting
        ]
    )
    return md.convert(md_text)


def build_site():
    """Main build process that compiles all pages, sitemap, and assets."""
    print("🚀 Starting shrtnotes static site build...")
    config = load_config()

    # Ensure output directories exist
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy static assets (CSS, JS, icons)
    site_static = OUTPUT_DIR / "static"
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, site_static)

    # Initialize Jinja2 environment
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    template_base = env.get_template("base.html")
    template_index = env.get_template("index.html")
    template_note = env.get_template("note.html")
    template_subject = env.get_template("subject.html")
    template_page = env.get_template("page.html")

    current_year = datetime.now().year
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Map subject metadata by id
    subjects_map = {s["id"]: s for s in config.get("subjects", [])}

    # 1. Load and parse all study notes
    notes_by_subject = {s["id"]: [] for s in config.get("subjects", [])}
    all_notes = []

    if NOTES_DIR.exists():
        for note_file in sorted(NOTES_DIR.glob("**/*.md")):
            meta, md_content = parse_frontmatter(note_file)
            if not meta.get("title"):
                continue

            sub_id = meta.get("subject", "").lower().strip()
            slug = meta.get("slug") or note_file.stem
            chapter = meta.get("chapter", "General Concepts")
            excerpt = meta.get("excerpt") or (md_content[:140].replace("\n", " ") + "...")
            date = meta.get("date", today_str)
            last_modified = meta.get("last_modified", date)
            order = meta.get("order", 100)

            sub_info = subjects_map.get(sub_id, {"name": sub_id.capitalize(), "id": sub_id})

            html_content = markdown_to_html(md_content)
            reading_time = calculate_reading_time(md_content)

            note_obj = {
                "file_path": str(note_file),
                "title": meta.get("title"),
                "slug": slug,
                "subject": sub_id,
                "subject_name": sub_info.get("name", sub_id.capitalize()),
                "chapter": chapter,
                "excerpt": excerpt,
                "date": date,
                "last_modified": last_modified,
                "order": order,
                "reading_time": reading_time,
                "raw_md": md_content,
                "html_content": html_content
            }

            if sub_id not in notes_by_subject:
                notes_by_subject[sub_id] = []
            notes_by_subject[sub_id].append(note_obj)
            all_notes.append(note_obj)

    # Sort notes within each subject by order and title
    for sub_id in notes_by_subject:
        notes_by_subject[sub_id].sort(key=lambda x: (x["chapter"], x["order"], x["title"]))

    # Sort all notes for homepage (newest first)
    all_notes.sort(key=lambda x: x["last_modified"], reverse=True)

    sitemap_entries = []

    # 2. Render Note Pages
    for sub_id, sub_notes in notes_by_subject.items():
        sub_dir = OUTPUT_DIR / sub_id
        sub_dir.mkdir(parents=True, exist_ok=True)

        # Prepare chapters dictionary for sidebar navigation
        sidebar_chapters = {}
        for n in sub_notes:
            ch = n["chapter"]
            if ch not in sidebar_chapters:
                sidebar_chapters[ch] = []
            sidebar_chapters[ch].append(n)

        for i, note in enumerate(sub_notes):
            prev_note = sub_notes[i - 1] if i > 0 else None
            next_note = sub_notes[i + 1] if i < len(sub_notes) - 1 else None

            note_url = f"{config.get('site_url', '')}/{sub_id}/{note['slug']}.html"
            rendered_html = template_note.render(
                config=config,
                note=note,
                content=note["html_content"],
                sidebar_chapters=sidebar_chapters,
                prev_note=prev_note,
                next_note=next_note,
                page_title=note["title"],
                page_description=note["excerpt"],
                current_url=note_url,
                base_url="",
                current_year=current_year
            )

            out_file = sub_dir / f"{note['slug']}.html"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            sitemap_entries.append({
                "loc": note_url,
                "lastmod": note["last_modified"],
                "changefreq": "weekly",
                "priority": "0.8"
            })

        # 3. Render Subject Overview Page
        sub_info = subjects_map.get(sub_id, {"name": sub_id.capitalize(), "id": sub_id, "description": ""})
        sub_page_url = f"{config.get('site_url', '')}/{sub_id}/"
        rendered_sub = template_subject.render(
            config=config,
            current_subject=sub_info,
            chapters=sidebar_chapters,
            page_title=f"{sub_info.get('name')} Notes",
            page_description=sub_info.get("description", ""),
            current_url=sub_page_url,
            base_url="",
            current_year=current_year
        )
        with open(sub_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(rendered_sub)

        sitemap_entries.append({
            "loc": sub_page_url,
            "lastmod": today_str,
            "changefreq": "daily",
            "priority": "0.9"
        })

    # 4. Render Home Page
    home_url = f"{config.get('site_url', '')}/"
    rendered_index = template_index.render(
        config=config,
        notes=all_notes,
        page_title="",
        page_description=config.get("description", ""),
        current_url=home_url,
        base_url="",
        current_year=current_year
    )
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(rendered_index)

    sitemap_entries.append({
        "loc": home_url,
        "lastmod": today_str,
        "changefreq": "daily",
        "priority": "1.0"
    })

    # 5. Render Standalone Compliance Pages (About, Privacy, Terms, Contact, Disclaimer)
    pages_out_dir = OUTPUT_DIR / "pages"
    pages_out_dir.mkdir(parents=True, exist_ok=True)

    if PAGES_DIR.exists():
        for page_file in PAGES_DIR.glob("*.md"):
            meta, md_content = parse_frontmatter(page_file)
            slug = meta.get("slug") or page_file.stem
            title = meta.get("title", slug.replace("-", " ").title())
            html_content = markdown_to_html(md_content)
            page_url = f"{config.get('site_url', '')}/pages/{slug}.html"

            page_obj = {
                "title": title,
                "slug": slug,
                "last_modified": meta.get("last_modified", today_str),
                "raw_md": md_content
            }

            rendered_page = template_page.render(
                config=config,
                page=page_obj,
                content=html_content,
                page_title=title,
                page_description=f"{title} - {config.get('site_name')}",
                current_url=page_url,
                base_url="",
                current_year=current_year
            )

            with open(pages_out_dir / f"{slug}.html", "w", encoding="utf-8") as f:
                f.write(rendered_page)

            sitemap_entries.append({
                "loc": page_url,
                "lastmod": meta.get("last_modified", today_str),
                "changefreq": "monthly",
                "priority": "0.5"
            })

    # 6. Generate Valid XML Sitemap
    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap_xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for entry in sitemap_entries:
        sitemap_xml.append('  <url>')
        sitemap_xml.append(f"    <loc>{entry['loc']}</loc>")
        sitemap_xml.append(f"    <lastmod>{entry['lastmod']}</lastmod>")
        sitemap_xml.append(f"    <changefreq>{entry['changefreq']}</changefreq>")
        sitemap_xml.append(f"    <priority>{entry['priority']}</priority>")
        sitemap_xml.append('  </url>')
    sitemap_xml.append('</urlset>')

    with open(OUTPUT_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_xml))

    # 7. Generate robots.txt
    robots_txt = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {config.get('site_url', '')}/sitemap.xml"
    ]
    with open(OUTPUT_DIR / "robots.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(robots_txt))

    print(f"✅ Build complete! Generated {len(all_notes)} notes, {len(config.get('subjects', []))} subjects, and {len(sitemap_entries)} URLs in sitemap.xml.")
    return len(all_notes)


if __name__ == "__main__":
    build_site()
