#!/usr/bin/env python3
"""
shrtnotes - Core Static Site Generator (SSG)
=============================================
Compiles study notes with Chapter-Wise hierarchy (Subject -> Chapter -> Topic),
clean URLs (NO .html visible anywhere), and a universal multi-network ad engine.
"""

import os
import shutil
import json
import math
import re
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
    s = str(icon_name).strip()
    if s.startswith("<svg"):
        return s
    return DEFAULT_ICONS.get(s, DEFAULT_ICONS["book"])


def get_ad_markup(slot_type, config):
    """Generate universal ad container markup with responsive mobile and desktop adaptation."""
    ads = config.get("ads", {})
    if not ads.get("enabled", False):
        return ""

    label_text = "Recommended Resources" if slot_type == "native" else "Advertisement"

    # 1. Check custom HTML/JS code for this slot
    custom_code = ads.get(f"{slot_type}_ad", "").strip()
    mobile_code = ads.get(f"{slot_type}_ad_mobile", "").strip() if slot_type in ("header", "footer") else ""

    if custom_code and mobile_code:
        # Dual-zone setup: Desktop code served to screens >= 768px, Mobile code to screens < 768px
        return f'''
        <div class="ad-slot-wrapper ad-desktop-only">
          <span class="ad-label">{label_text}</span>
          <div class="ad-container ad-{slot_type}">
            {custom_code}
          </div>
        </div>
        <div class="ad-slot-wrapper ad-mobile-only">
          <span class="ad-label">{label_text}</span>
          <div class="ad-container ad-{slot_type}-mobile">
            {mobile_code}
          </div>
        </div>
        '''

    if custom_code:
        return f'''
        <div class="ad-slot-wrapper ad-responsive">
          <span class="ad-label">{label_text}</span>
          <div class="ad-container ad-{slot_type}">
            {custom_code}
          </div>
        </div>
        '''

    if mobile_code:
        return f'''
        <div class="ad-slot-wrapper ad-mobile-only">
          <span class="ad-label">{label_text}</span>
          <div class="ad-container ad-{slot_type}-mobile">
            {mobile_code}
          </div>
        </div>
        '''

    # 2. Check AdSense fallback parameters
    adsense = ads.get("adsense", {})
    client_id = adsense.get("client_id", "").strip()
    slot_id = adsense.get(f"{slot_type}_slot", "").strip()

    if client_id and slot_id and client_id != "ca-pub-XXXXXXXXXXXXXXXX":
        return f'''
        <div class="ad-slot-wrapper ad-responsive">
          <span class="ad-label">{label_text}</span>
          <div class="ad-container ad-{slot_type}">
            <ins class="adsbygoogle"
                 style="display:block"
                 data-ad-client="{client_id}"
                 data-ad-slot="{slot_id}"
                 data-ad-format="auto"
                 data-full-width-responsive="true"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
          </div>
        </div>
        '''
    return ""


def load_config():
    """Load main site configuration and merge local secrets if present."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Merge private secrets from secrets.json if present (never tracked in git)
    secrets_file = BASE_DIR / "secrets.json"
    if secrets_file.exists():
        try:
            with open(secrets_file, "r", encoding="utf-8") as sf:
                secrets = json.load(sf)
                if "ai_api_key" in secrets and secrets["ai_api_key"]:
                    if "ai" not in data:
                        data["ai"] = {}
                    data["ai"]["api_key"] = secrets["ai_api_key"]
        except Exception:
            pass

    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        if "ai" not in data:
            data["ai"] = {}
        data["ai"]["api_key"] = env_key

    return data


def save_config(config_data):
    """Save configuration to config.json, isolating sensitive API keys to secrets.json."""
    data_to_save = json.loads(json.dumps(config_data))

    # Keep API key isolated in gitignored secrets.json so GitHub Push Protection never triggers
    if "ai" in data_to_save and "api_key" in data_to_save["ai"]:
        api_key = data_to_save["ai"]["api_key"]
        if api_key:
            secrets_file = BASE_DIR / "secrets.json"
            try:
                secrets = {}
                if secrets_file.exists():
                    with open(secrets_file, "r", encoding="utf-8") as sf:
                        secrets = json.load(sf)
                secrets["ai_api_key"] = api_key
                with open(secrets_file, "w", encoding="utf-8") as sf:
                    json.dump(secrets, sf, indent=2)
            except Exception:
                pass
        data_to_save["ai"]["api_key"] = ""

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2)


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
    """Convert Markdown to clean HTML with KaTeX formulas preserved, chemical structures rendered, and responsive scrollable tables."""
    # Pre-process chemical molecule blocks (```chem or ```smiles)
    def _replace_chem_block(match):
        title = (match.group(1) or "").strip()
        smiles_raw = match.group(2).strip()
        clean_lines = [l.strip() for l in smiles_raw.splitlines() if l.strip() and not l.strip().startswith("#")]
        smiles = clean_lines[0] if clean_lines else ""
        if not smiles:
            return ""

        caption_html = (
            f'<div class="molecule-caption">'
            f'<span class="molecule-title">{title}</span>'
            f'<code class="molecule-smiles">{smiles}</code>'
            f'</div>'
        ) if title else (
            f'<div class="molecule-caption">'
            f'<code class="molecule-smiles">{smiles}</code>'
            f'</div>'
        )

        return (
            f'\n\n<div class="molecule-card">'
            f'<div class="molecule-render" data-smiles="{smiles}"></div>'
            f'{caption_html}'
            f'</div>\n\n'
        )

    md_text = re.sub(r'```(?:chem|smiles)(?:[ \t]+([^\n]*))?\n([\s\S]*?)```', _replace_chem_block, md_text)

    md = markdown.Markdown(
        extensions=[
            "extra",
            "codehilite",
            "toc",
            "nl2br",
            "sane_lists"
        ]
    )
    raw_html = md.convert(md_text)

    def _wrap_table(match):
        table_html = match.group(0)
        return (
            '<div class="table-responsive-wrapper">'
            '<div class="table-scroll-hint">'
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8L22 12L18 16"/><path d="M6 8L2 12L6 16"/><path d="M2 12H22"/></svg>'
            '<span>Scroll table horizontally</span>'
            '</div>'
            f'{table_html}'
            '</div>'
        )

    wrapped_html = re.sub(r'<table\b[^>]*>[\s\S]*?</table>', _wrap_table, raw_html)
    return wrapped_html


def write_clean_page(rel_path_dir, html_content):
    """
    Writes index.html inside rel_path_dir to ensure Clean URLs (no .html extension).
    Example: rel_path_dir='about' writes to site/about/index.html (accessed as /about/).
    """
    if rel_path_dir:
        out_dir = OUTPUT_DIR / rel_path_dir
    else:
        out_dir = OUTPUT_DIR

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)


def build_site():
    """
    Main static site generator with:
    - Chapter-Wise hierarchy (Subject -> Chapter -> Topic)
    - Clean URLs (NO .html visible)
    - Universal Ad Engine (Any network or AdSense)
    """
    print("🚀 Starting shrtnotes static site build with Clean URLs & Chapter hierarchy...")
    config = load_config()

    # Recreate output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy static assets (CSS, JS, icons)
    site_static = OUTPUT_DIR / "static"
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, site_static)

    # Initialize Jinja2 environment and helpers
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.globals["get_icon"] = get_icon

    template_index = env.get_template("index.html")
    template_note = env.get_template("note.html")
    template_subject = env.get_template("subject.html")
    template_branch = env.get_template("branch.html")
    template_chapter = env.get_template("chapter.html")
    template_page = env.get_template("page.html")

    current_year = datetime.now().year
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Generate ad slot HTML snippets with multi-zone & native support
    ad_slots = {
        "header": get_ad_markup("header", config),
        "in_article": get_ad_markup("in_article", config),
        "in_article_2": get_ad_markup("in_article_2", config),
        "sidebar": get_ad_markup("sidebar", config),
        "native": get_ad_markup("native", config),
        "footer": get_ad_markup("footer", config)
    }

    # Prepare subjects and chapters dictionary from config
    subjects = config.get("subjects", [])
    subjects_dict = {}
    for sub in subjects:
        sub_id = sub["id"]
        has_branches = bool(sub.get("branches"))
        if has_branches:
            branches_dict = {}
            for b in sub.get("branches", []):
                b_id = b["id"]
                chapters_dict = {ch["id"]: ch for ch in b.get("chapters", [])}
                branches_dict[b_id] = {
                    "info": b,
                    "chapters": chapters_dict,
                    "notes": []
                }
            subjects_dict[sub_id] = {
                "info": sub,
                "has_branches": True,
                "branches": branches_dict,
                "chapters": {},
                "notes": []
            }
        else:
            chapters_list = sub.get("chapters", [])
            chapters_dict = {ch["id"]: ch for ch in chapters_list}
            subjects_dict[sub_id] = {
                "info": sub,
                "has_branches": False,
                "branches": {},
                "chapters": chapters_dict,
                "notes": []
            }

    # 1. Discover all notes/topics in content/notes/
    all_notes = []
    if NOTES_DIR.exists():
        for note_file in sorted(NOTES_DIR.glob("**/*.md")):
            meta, md_content = parse_frontmatter(note_file)
            if not meta.get("title"):
                continue

            rel_parts = note_file.relative_to(NOTES_DIR).parts
            sub_id = str(meta.get("subject", "")).lower().strip()
            # If not in frontmatter, infer from directory
            if not sub_id and len(rel_parts) >= 2:
                sub_id = rel_parts[0].lower().strip()

            if sub_id not in subjects_dict:
                # Dynamically register unknown subject
                subjects_dict[sub_id] = {
                    "info": {"id": sub_id, "name": sub_id.capitalize(), "description": "", "icon": "book", "chapters": []},
                    "has_branches": False,
                    "branches": {},
                    "chapters": {},
                    "notes": []
                }

            is_branched = subjects_dict[sub_id]["has_branches"] or bool(meta.get("branch")) or len(rel_parts) >= 4

            branch_id = ""
            branch_name = ""
            branch_info = None

            if is_branched:
                branch_raw = str(meta.get("branch", "")).strip().lower()
                if not branch_raw and len(rel_parts) >= 4:
                    branch_raw = rel_parts[1].lower().strip()
                if not branch_raw:
                    branch_raw = "general"
                branch_id = branch_raw

                # Lookup branch in subjects_dict[sub_id]["branches"]
                if branch_id not in subjects_dict[sub_id]["branches"]:
                    found_b = False
                    for b_key, b_val in subjects_dict[sub_id]["branches"].items():
                        if b_val["info"].get("name", "").lower() == branch_id.lower():
                            branch_id = b_key
                            branch_info = b_val["info"]
                            found_b = True
                            break
                    if not found_b:
                        branch_info = {"id": branch_id, "name": branch_id.replace("-", " ").title(), "description": "", "chapters": []}
                        subjects_dict[sub_id]["branches"][branch_id] = {
                            "info": branch_info,
                            "chapters": {},
                            "notes": []
                        }
                else:
                    branch_info = subjects_dict[sub_id]["branches"][branch_id]["info"]

                branch_name = branch_info.get("name", branch_id.replace("-", " ").title())

                # Chapter handling under branch
                chapter_raw = str(meta.get("chapter", "")).strip()
                if not chapter_raw and len(rel_parts) >= 4:
                    chapter_raw = rel_parts[2]
                elif not chapter_raw and len(rel_parts) >= 3:
                    chapter_raw = rel_parts[1]
                if not chapter_raw:
                    chapter_raw = "general"

                chapter_id = chapter_raw.lower().replace(" ", "-")
                branch_chapters = subjects_dict[sub_id]["branches"][branch_id]["chapters"]
                ch_info = branch_chapters.get(chapter_id)
                if not ch_info:
                    for c in branch_chapters.values():
                        if c.get("name", "").lower() == chapter_raw.lower():
                            ch_info = c
                            chapter_id = c["id"]
                            break
                if not ch_info:
                    ch_name = chapter_raw.replace("-", " ").title()
                    ch_info = {"id": chapter_id, "name": ch_name, "description": ""}
                    branch_chapters[chapter_id] = ch_info

            else:
                # Chapter handling directly under subject
                chapter_raw = str(meta.get("chapter", "")).strip()
                if not chapter_raw and len(rel_parts) >= 3:
                    chapter_raw = rel_parts[1]
                if not chapter_raw:
                    chapter_raw = "general"

                chapter_id = chapter_raw.lower().replace(" ", "-")
                sub_chapters = subjects_dict[sub_id]["chapters"]
                ch_info = sub_chapters.get(chapter_id)
                if not ch_info:
                    for c in sub_chapters.values():
                        if c.get("name", "").lower() == chapter_raw.lower():
                            ch_info = c
                            chapter_id = c["id"]
                            break
                if not ch_info:
                    ch_name = chapter_raw.replace("-", " ").title()
                    ch_info = {"id": chapter_id, "name": ch_name, "description": ""}
                    sub_chapters[chapter_id] = ch_info

            slug = meta.get("slug") or note_file.stem
            excerpt = meta.get("excerpt") or (md_content[:140].replace("\n", " ") + "...")
            date = meta.get("date", today_str)
            last_modified = meta.get("last_modified", date)
            order = int(meta.get("order", 100))

            html_content = markdown_to_html(md_content)
            reading_time = calculate_reading_time(md_content)

            sub_name = subjects_dict[sub_id]["info"].get("name", sub_id.capitalize())
            chapter_name = ch_info.get("name", chapter_id.title())

            if branch_id:
                url_path = f"{sub_id}/{branch_id}/{chapter_id}/{slug}"
            else:
                url_path = f"{sub_id}/{chapter_id}/{slug}"

            raw_tags = meta.get("tags", [])
            if isinstance(raw_tags, str):
                tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
            else:
                tags = []

            note_obj = {
                "file_path": str(note_file.relative_to(NOTES_DIR)),
                "title": meta.get("title"),
                "slug": slug,
                "subject": sub_id,
                "subject_name": sub_name,
                "branch": branch_id,
                "branch_name": branch_name,
                "chapter": chapter_id,
                "chapter_name": chapter_name,
                "url_path": url_path,
                "excerpt": excerpt,
                "tags": tags,
                "tags_str": ", ".join(tags),
                "date": date,
                "last_modified": last_modified,
                "order": order,
                "reading_time": reading_time,
                "raw_md": md_content,
                "html_content": html_content
            }

            subjects_dict[sub_id]["notes"].append(note_obj)
            if branch_id:
                subjects_dict[sub_id]["branches"][branch_id]["notes"].append(note_obj)
            all_notes.append(note_obj)

    # Sort all notes strictly newest to oldest (recent first)
    all_notes.sort(key=lambda x: (x.get("last_modified") or x.get("date") or ""), reverse=True)

    # Sort each subject's notes strictly newest to oldest and store top 2 recent updates
    for sub_id in subjects_dict:
        subjects_dict[sub_id]["notes"].sort(key=lambda x: (x.get("last_modified") or x.get("date") or ""), reverse=True)
        subjects_dict[sub_id]["recent_2"] = subjects_dict[sub_id]["notes"][:2]
        subjects_dict[sub_id]["recent_3"] = subjects_dict[sub_id]["notes"][:3]
        if subjects_dict[sub_id]["has_branches"]:
            for b_id in subjects_dict[sub_id]["branches"]:
                subjects_dict[sub_id]["branches"][b_id]["notes"].sort(key=lambda x: (x.get("last_modified") or x.get("date") or ""), reverse=True)

    sitemap_entries = []

    # 2. Render Topics, Chapters, and Subject Pages with Clean URLs
    for sub_id, sub_data in subjects_dict.items():
        sub_info = sub_data["info"]
        sub_notes = sub_data["notes"]

        if sub_data["has_branches"]:
            # ---- BRANCHED SUBJECT HIERARCHY (e.g. Chemistry) ----
            # Subject -> Branch -> Chapter -> Topic
            branches_summary = []

            for b_id, b_data in sub_data["branches"].items():
                b_info = b_data["info"]
                b_notes = b_data["notes"]

                # Group notes by chapter within this branch
                grouped_by_chapter = {}
                for ch_id, ch_obj in b_data["chapters"].items():
                    grouped_by_chapter[ch_id] = {
                        "info": ch_obj,
                        "notes": []
                    }

                for n in b_notes:
                    ch_id = n["chapter"]
                    if ch_id not in grouped_by_chapter:
                        grouped_by_chapter[ch_id] = {
                            "info": {"id": ch_id, "name": n["chapter_name"], "description": ""},
                            "notes": []
                        }
                    grouped_by_chapter[ch_id]["notes"].append(n)

                # Sort notes within each chapter
                for ch_id in grouped_by_chapter:
                    grouped_by_chapter[ch_id]["notes"].sort(key=lambda x: (x["order"], x["title"]))

                # Sequential list of notes in branch for Prev / Next links
                flattened_branch_notes = []
                for ch_id in sorted(grouped_by_chapter.keys()):
                    flattened_branch_notes.extend(grouped_by_chapter[ch_id]["notes"])

                # Render Topic Pages: Clean URL /<subject>/<branch>/<chapter>/<topic-slug>/
                for i, note in enumerate(flattened_branch_notes):
                    prev_note = flattened_branch_notes[i - 1] if i > 0 else None
                    next_note = flattened_branch_notes[i + 1] if i < len(flattened_branch_notes) - 1 else None

                    clean_rel_dir = note["url_path"]
                    note_canonical = f"{config.get('site_url', '').rstrip('/')}/{clean_rel_dir}/"

                    # Depth 4: ../../../../
                    rendered_topic = template_note.render(
                        config=config,
                        note=note,
                        content=note["html_content"],
                        grouped_chapters=grouped_by_chapter,
                        prev_note=prev_note,
                        next_note=next_note,
                        page_title=note["title"],
                        page_description=note["excerpt"],
                        current_url=note_canonical,
                        root_path="../../../../",
                        ad_slots=ad_slots,
                        current_year=current_year
                    )
                    write_clean_page(clean_rel_dir, rendered_topic)

                    sitemap_entries.append({
                        "loc": note_canonical,
                        "lastmod": note["last_modified"],
                        "changefreq": "weekly",
                        "priority": "0.8"
                    })

                # Render Chapter Pages: Clean URL /<subject>/<branch>/<chapter>/
                for ch_id, ch_data in grouped_by_chapter.items():
                    clean_ch_dir = f"{sub_id}/{b_id}/{ch_id}"
                    ch_canonical = f"{config.get('site_url', '').rstrip('/')}/{clean_ch_dir}/"

                    rendered_ch = template_chapter.render(
                        config=config,
                        subject=sub_info,
                        branch=b_info,
                        chapter=ch_data["info"],
                        notes=ch_data["notes"],
                        page_title=f"{ch_data['info']['name']} Notes | {b_info['name']} | {sub_info['name']}",
                        page_description=ch_data["info"].get("description") or f"High yield study notes for {ch_data['info']['name']} under {b_info['name']}.",
                        current_url=ch_canonical,
                        root_path="../../../",
                        ad_slots=ad_slots,
                        current_year=current_year
                    )
                    write_clean_page(clean_ch_dir, rendered_ch)

                    sitemap_entries.append({
                        "loc": ch_canonical,
                        "lastmod": today_str,
                        "changefreq": "daily",
                        "priority": "0.85"
                    })

                # Render Branch Page: Clean URL /<subject>/<branch>/
                clean_branch_dir = f"{sub_id}/{b_id}"
                branch_canonical = f"{config.get('site_url', '').rstrip('/')}/{clean_branch_dir}/"

                rendered_branch = template_branch.render(
                    config=config,
                    subject=sub_info,
                    branch=b_info,
                    grouped_chapters=grouped_by_chapter,
                    total_notes_count=len(b_notes),
                    page_title=f"{b_info['name']} Chapters | {sub_info['name']}",
                    page_description=b_info.get("description", ""),
                    current_url=branch_canonical,
                    root_path="../../",
                    ad_slots=ad_slots,
                    current_year=current_year
                )
                write_clean_page(clean_branch_dir, rendered_branch)

                sitemap_entries.append({
                    "loc": branch_canonical,
                    "lastmod": today_str,
                    "changefreq": "daily",
                    "priority": "0.88"
                })

                branches_summary.append({
                    "info": b_info,
                    "chapters_count": len(grouped_by_chapter),
                    "notes_count": len(b_notes)
                })

            # Render Subject Page: Clean URL /<subject>/ (Branch Grid)
            sub_canonical = f"{config.get('site_url', '').rstrip('/')}/{sub_id}/"
            rendered_sub = template_subject.render(
                config=config,
                current_subject=sub_info,
                branches_summary=branches_summary,
                grouped_chapters={},
                total_notes_count=len(sub_notes),
                page_title=f"{sub_info['name']} Branches & Chapters",
                page_description=sub_info.get("description", ""),
                current_url=sub_canonical,
                root_path="../",
                ad_slots=ad_slots,
                current_year=current_year
            )
            write_clean_page(sub_id, rendered_sub)

            sitemap_entries.append({
                "loc": sub_canonical,
                "lastmod": today_str,
                "changefreq": "daily",
                "priority": "0.9"
            })

        else:
            # ---- STANDARD SUBJECT HIERARCHY (Direct Chapters: Mathematics, Physics, Biology) ----
            # Subject -> Chapter -> Topic
            grouped_by_chapter = {}
            for ch_id, ch_obj in sub_data["chapters"].items():
                grouped_by_chapter[ch_id] = {
                    "info": ch_obj,
                    "notes": []
                }

            for n in sub_notes:
                ch_id = n["chapter"]
                if ch_id not in grouped_by_chapter:
                    grouped_by_chapter[ch_id] = {
                        "info": {"id": ch_id, "name": n["chapter_name"], "description": ""},
                        "notes": []
                    }
                grouped_by_chapter[ch_id]["notes"].append(n)

            # Sort notes within each chapter
            for ch_id in grouped_by_chapter:
                grouped_by_chapter[ch_id]["notes"].sort(key=lambda x: (x["order"], x["title"]))

            # Sequential list of notes in subject for Prev / Next links
            flattened_notes = []
            for ch_id in sorted(grouped_by_chapter.keys()):
                flattened_notes.extend(grouped_by_chapter[ch_id]["notes"])

            # Render Topic Pages: Clean URL /<subject>/<chapter>/<topic-slug>/
            for i, note in enumerate(flattened_notes):
                prev_note = flattened_notes[i - 1] if i > 0 else None
                next_note = flattened_notes[i + 1] if i < len(flattened_notes) - 1 else None

                clean_rel_dir = note["url_path"]
                note_canonical = f"{config.get('site_url', '').rstrip('/')}/{clean_rel_dir}/"

                # Root path depth for 3 levels: ../../../
                rendered_topic = template_note.render(
                    config=config,
                    note=note,
                    content=note["html_content"],
                    grouped_chapters=grouped_by_chapter,
                    prev_note=prev_note,
                    next_note=next_note,
                    page_title=note["title"],
                    page_description=note["excerpt"],
                    current_url=note_canonical,
                    root_path="../../../",
                    ad_slots=ad_slots,
                    current_year=current_year
                )

                write_clean_page(clean_rel_dir, rendered_topic)

                sitemap_entries.append({
                    "loc": note_canonical,
                    "lastmod": note["last_modified"],
                    "changefreq": "weekly",
                    "priority": "0.8"
                })

            # Render Chapter Pages: Clean URL /<subject>/<chapter>/
            for ch_id, ch_data in grouped_by_chapter.items():
                clean_ch_dir = f"{sub_id}/{ch_id}"
                ch_canonical = f"{config.get('site_url', '').rstrip('/')}/{clean_ch_dir}/"

                rendered_ch = template_chapter.render(
                    config=config,
                    subject=sub_info,
                    chapter=ch_data["info"],
                    notes=ch_data["notes"],
                    page_title=f"{ch_data['info']['name']} Notes | {sub_info['name']}",
                    page_description=ch_data["info"].get("description") or f"High yield study notes for {ch_data['info']['name']}.",
                    current_url=ch_canonical,
                    root_path="../../",
                    ad_slots=ad_slots,
                    current_year=current_year
                )

                write_clean_page(clean_ch_dir, rendered_ch)

                sitemap_entries.append({
                    "loc": ch_canonical,
                    "lastmod": today_str,
                    "changefreq": "daily",
                    "priority": "0.85"
                })

            # Render Subject Pages: Clean URL /<subject>/
            sub_canonical = f"{config.get('site_url', '').rstrip('/')}/{sub_id}/"
            rendered_sub = template_subject.render(
                config=config,
                current_subject=sub_info,
                grouped_chapters=grouped_by_chapter,
                total_notes_count=len(sub_notes),
                page_title=f"{sub_info['name']} Notes",
                page_description=sub_info.get("description", ""),
                current_url=sub_canonical,
                root_path="../",
                ad_slots=ad_slots,
                current_year=current_year
            )

            write_clean_page(sub_id, rendered_sub)

            sitemap_entries.append({
                "loc": sub_canonical,
                "lastmod": today_str,
                "changefreq": "daily",
                "priority": "0.9"
            })

    # 3. Render Home Page: Clean URL /
    home_canonical = f"{config.get('site_url', '').rstrip('/')}/"
    rendered_index = template_index.render(
        config=config,
        notes=all_notes,
        subjects_data=subjects_dict,
        page_title="",
        page_description=config.get("description", ""),
        current_url=home_canonical,
        root_path="",
        ad_slots=ad_slots,
        current_year=current_year
    )
    write_clean_page("", rendered_index)

    sitemap_entries.append({
        "loc": home_canonical,
        "lastmod": today_str,
        "changefreq": "daily",
        "priority": "1.0"
    })

    # 4. Render Standalone Compliance Pages with Clean URLs (e.g. /about/, /privacy-policy/)
    if PAGES_DIR.exists():
        for page_file in PAGES_DIR.glob("*.md"):
            meta, md_content = parse_frontmatter(page_file)
            slug = meta.get("slug") or page_file.stem
            title = meta.get("title", slug.replace("-", " ").title())
            html_content = markdown_to_html(md_content)

            clean_page_dir = slug
            page_canonical = f"{config.get('site_url', '').rstrip('/')}/{clean_page_dir}/"

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
                ad_slots=ad_slots,
                current_year=current_year
            )

            write_clean_page(clean_page_dir, rendered_page)

            sitemap_entries.append({
                "loc": page_canonical,
                "lastmod": meta.get("last_modified", today_str),
                "changefreq": "monthly",
                "priority": "0.5"
            })

    # 4b. Generate Custom 404 Page for Cloudflare Pages
    rendered_404 = template_page.render(
        config=config,
        page={"title": "Page Not Found", "slug": "404", "last_modified": today_str},
        content="<p style='font-size: 1.1rem; color: var(--text-muted); margin-bottom: 1.5rem;'>The study topic or page you are looking for could not be found or may have been updated.</p><a href='/' style='display: inline-flex; align-items: center; gap: 0.5rem; background: var(--accent); color: #ffffff; padding: 0.65rem 1.25rem; border-radius: 8px; text-decoration: none; font-weight: 500;'>&larr; Return to All Notes</a>",
        page_title="404 - Page Not Found",
        page_description=f"Page not found - {config.get('site_name')}",
        current_url=f"{config.get('site_url', '').rstrip('/')}/404.html",
        root_path="/",
        ad_slots=ad_slots,
        current_year=current_year
    )
    with open(OUTPUT_DIR / "404.html", "w", encoding="utf-8") as f:
        f.write(rendered_404)

    # 5. Generate Valid XML Sitemap with Clean URLs
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

    # 6. Generate robots.txt
    robots_txt = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {config.get('site_url', '').rstrip('/')}/sitemap.xml"
    ]
    with open(OUTPUT_DIR / "robots.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(robots_txt))

    # 7. Generate Live Search Engine Index (search_index.json)
    search_index = []
    for note in all_notes:
        plain_content = re.sub(r'(\*\*|__|\*|_|`|#|\[|\]|\([^\)]*\)|<[^>]+>|\$\$|\$)', ' ', note.get("raw_md", ""))
        clean_snippet = ' '.join(plain_content.split())[:500]
        search_index.append({
            "title": note["title"],
            "slug": note["slug"],
            "subject": note["subject"],
            "subject_name": note["subject_name"],
            "branch": note.get("branch", ""),
            "branch_name": note.get("branch_name", ""),
            "chapter": note["chapter"],
            "chapter_name": note["chapter_name"],
            "url": f"/{note['url_path']}/",
            "excerpt": note["excerpt"],
            "tags": note["tags"],
            "reading_time": note["reading_time"],
            "content": clean_snippet
        })

    with open(OUTPUT_DIR / "search_index.json", "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)

    print(f"✅ Build complete! Compiled {len(all_notes)} topics across chapters with 100% Clean URLs (0 .html) and {len(sitemap_entries)} sitemap URLs.")
    return len(all_notes)


if __name__ == "__main__":
    build_site()
