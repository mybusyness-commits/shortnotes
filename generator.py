#!/usr/bin/env python3
"""
shrtnotes - Core Static Site Generator (SSG)
=============================================
Compiles Markdown study notes, subject indices, legal pages,
sitemap.xml, and robots.txt into a high-performance static website
with 100% relative linking (zero 404s on LAN or web) and custom SVG icon support.
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

DEFAULT_ICONS = {
    "calculator": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><line x1="16" x2="16" y1="14" y2="18"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/></svg>',
    "atom": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><path d="M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z"/><path d="M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z"/></svg>',
    "flask-conical": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v7.31L4.1 20.3A2 2 0 0 0 5.8 23h12.4a2 2 0 0 0 1.7-2.7L14 9.31V2"/><path d="M8.5 2h7"/><path d="M14 9.3 8.5 19"/></svg>',
    "dna": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 15c6.667-6 13.333 0 20-6"/><path d="M9 22c1.798-1.998 2.518-3.995 2.807-5.993"/><path d="M15 2c-1.798 1.998-2.518 3.995-2.807 5.993"/><path d="m17 6-2.5-2.5"/><path d="m14 8-1-1"/><path d="m7 18 2.5 2.5"/><path d="m3.5 14.5.5.5"/><path d="m20 9 .5.5"/><path d="m6.5 12.5 1 1"/><path d="m16.5 10.5 1 1"/><path d="m10 16 1 1"/></svg>',
    "book": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    "code": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "cpu": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/></svg>',
    "globe": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
    "compass": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
    "heart": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>',
    "scale": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>',
    "brain": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>',
    "sparkles": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>',
    "terminal": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>',
    "database": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>',
    "palette": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>'
}

def get_icon(icon_name):
    """Return inline SVG markup for a given icon name or raw SVG."""
    if not icon_name:
        return DEFAULT_ICONS["book"]
    s = icon_name.strip()
    if s.startswith("<svg"):
        return s
    return DEFAULT_ICONS.get(s, DEFAULT_ICONS["book"])


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
    """Main build process that compiles all pages, sitemap, and assets with relative links."""
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

    # Initialize Jinja2 environment and register get_icon helper
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.globals["get_icon"] = get_icon

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

            sub_info = subjects_map.get(sub_id, {"name": sub_id.capitalize(), "id": sub_id, "icon": "book"})

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

    # 2. Render Note Pages (Root depth: 1 level down -> root_path is "../")
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

            note_canonical = f"{config.get('site_url', '')}/{sub_id}/{note['slug']}.html"
            rendered_html = template_note.render(
                config=config,
                note=note,
                content=note["html_content"],
                sidebar_chapters=sidebar_chapters,
                prev_note=prev_note,
                next_note=next_note,
                page_title=note["title"],
                page_description=note["excerpt"],
                current_url=note_canonical,
                root_path="../",
                current_year=current_year
            )

            out_file = sub_dir / f"{note['slug']}.html"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            sitemap_entries.append({
                "loc": note_canonical,
                "lastmod": note["last_modified"],
                "changefreq": "weekly",
                "priority": "0.8"
            })

        # 3. Render Subject Overview Page (Root depth: 1 level down -> root_path is "../")
        sub_info = subjects_map.get(sub_id, {"name": sub_id.capitalize(), "id": sub_id, "description": "", "icon": "book"})
        sub_canonical = f"{config.get('site_url', '')}/{sub_id}/index.html"
        rendered_sub = template_subject.render(
            config=config,
            current_subject=sub_info,
            chapters=sidebar_chapters,
            page_title=f"{sub_info.get('name')} Notes",
            page_description=sub_info.get("description", ""),
            current_url=sub_canonical,
            root_path="../",
            current_year=current_year
        )
        with open(sub_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(rendered_sub)

        sitemap_entries.append({
            "loc": sub_canonical,
            "lastmod": today_str,
            "changefreq": "daily",
            "priority": "0.9"
        })

    # 4. Render Home Page (Root depth: 0 -> root_path is "")
    home_canonical = f"{config.get('site_url', '')}/index.html"
    rendered_index = template_index.render(
        config=config,
        notes=all_notes,
        page_title="",
        page_description=config.get("description", ""),
        current_url=home_canonical,
        root_path="",
        current_year=current_year
    )
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(rendered_index)

    sitemap_entries.append({
        "loc": home_canonical,
        "lastmod": today_str,
        "changefreq": "daily",
        "priority": "1.0"
    })

    # 5. Render Standalone Compliance Pages (Root depth: 1 level down -> root_path is "../")
    pages_out_dir = OUTPUT_DIR / "pages"
    pages_out_dir.mkdir(parents=True, exist_ok=True)

    if PAGES_DIR.exists():
        for page_file in PAGES_DIR.glob("*.md"):
            meta, md_content = parse_frontmatter(page_file)
            slug = meta.get("slug") or page_file.stem
            title = meta.get("title", slug.replace("-", " ").title())
            html_content = markdown_to_html(md_content)
            page_canonical = f"{config.get('site_url', '')}/pages/{slug}.html"

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
                current_url=page_canonical,
                root_path="../",
                current_year=current_year
            )

            with open(pages_out_dir / f"{slug}.html", "w", encoding="utf-8") as f:
                f.write(rendered_page)

            sitemap_entries.append({
                "loc": page_canonical,
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
