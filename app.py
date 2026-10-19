#!/usr/bin/env python3
"""
shrtnotes Studio - Local Website Management Application
======================================================
Visual dashboard to write and organize study notes with:
- Chapter-Wise hierarchy (Subject -> Chapter -> Topic)
- Clean URLs (no .html extensions)
- Universal multi-platform ad engine (AdSense, Media.net, Ezoic, Custom HTML)
- LAN mobile preview & 1-Click GitHub deployment
"""

import os
import sys
import json
import socket
import subprocess
import yaml
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, send_from_directory

from generator import (
    BASE_DIR, NOTES_DIR, PAGES_DIR, OUTPUT_DIR, CONFIG_FILE,
    DEFAULT_ICONS, get_icon,
    load_config, save_config, parse_frontmatter, build_site
)

app = Flask(__name__)
app.secret_key = "shrtnotes-studio-secret-key-2026"


def get_local_ip():
    """Detect local LAN IP address for mobile testing."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_all_notes_list():
    """List all topics with metadata for editing."""
    notes = []
    config = load_config()
    subjects_map = {s["id"]: s for s in config.get("subjects", [])}

    if NOTES_DIR.exists():
        for f in NOTES_DIR.glob("**/*.md"):
            meta, md = parse_frontmatter(f)
            if not meta.get("title"):
                continue

            sub_id = str(meta.get("subject", "")).lower().strip()
            chapter_id = str(meta.get("chapter", "general")).lower().strip().replace(" ", "-")

            rel_parts = f.relative_to(NOTES_DIR).parts
            if not sub_id and len(rel_parts) >= 2:
                sub_id = rel_parts[0]
            if chapter_id == "general" and len(rel_parts) >= 3:
                chapter_id = rel_parts[1]

            sub_info = subjects_map.get(sub_id, {})
            sub_name = sub_info.get("name", sub_id.capitalize())

            # Find chapter name
            ch_name = chapter_id.replace("-", " ").title()
            for ch in sub_info.get("chapters", []):
                if ch["id"] == chapter_id or ch.get("name", "").lower() == chapter_id.lower():
                    ch_name = ch["name"]
                    break

            raw_tags = meta.get("tags", [])
            if isinstance(raw_tags, str):
                note_tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
            elif isinstance(raw_tags, list):
                note_tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
            else:
                note_tags = []

            notes.append({
                "file_path": str(f.relative_to(NOTES_DIR)),
                "title": meta.get("title", f.stem),
                "slug": meta.get("slug", f.stem),
                "subject": sub_id,
                "subject_name": sub_name,
                "chapter": chapter_id,
                "chapter_name": ch_name,
                "date": meta.get("date", ""),
                "last_modified": meta.get("last_modified", ""),
                "excerpt": meta.get("excerpt", ""),
                "tags": note_tags
            })
    notes.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
    return notes


def get_git_remote():
    """Get current git remote origin URL."""
    try:
        res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(BASE_DIR), capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    config = load_config()
    return config.get("github", {}).get("repo_url", "")


def get_ssh_public_key():
    """Retrieve the generated SSH public key if present."""
    for key_file in ["id_ed25519.pub", "id_rsa.pub"]:
        p = Path.home() / ".ssh" / key_file
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    return ""


def generate_qr_svg(url):
    """Generate high-contrast vector SVG QR code for mobile scanning."""
    try:
        import qrcode
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(url, image_factory=factory, box_size=8, border=2)
        return img.to_string().decode("utf-8")
    except Exception as e:
        print(f"QR code generation error for {url}: {e}")
        return ""


# ==============================================================================
# Base Studio Layout
# ==============================================================================
STUDIO_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>shrtnotes Studio - Site Management</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --sidebar-bg: #080c14;
      --text: #f9fafb;
      --text-muted: #9ca3af;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: var(--font); background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
    
    .studio-sidebar { width: 270px; background: var(--sidebar-bg); border-right: 1px solid var(--card-border); display: flex; flex-direction: column; }
    .studio-brand { padding: 1.25rem 1.5rem; font-size: 1.25rem; font-weight: 700; border-bottom: 1px solid var(--card-border); display: flex; align-items: center; gap: 0.6rem; }
    .studio-brand svg { width: 22px; height: 22px; stroke: var(--accent); }
    .nav-menu { list-style: none; padding: 1rem 0.75rem; display: flex; flex-direction: column; gap: 0.35rem; flex: 1; overflow-y: auto; }
    .nav-btn { display: flex; align-items: center; gap: 0.75rem; padding: 0.7rem 1rem; border-radius: 8px; color: var(--text-muted); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: all 0.15s; }
    .nav-btn svg { width: 18px; height: 18px; }
    .nav-btn:hover, .nav-btn.active { color: #fff; background: #1e293b; }
    .nav-btn.active { background: #1e3a8a; color: #93c5fd; }
    
    .lan-pill { margin: 1rem; padding: 0.85rem; background: #172554; border: 1px solid #1e40af; border-radius: 8px; font-size: 0.8rem; }
    .lan-pill strong { color: #93c5fd; display: block; margin-bottom: 0.25rem; }
    .lan-pill a { color: #60a5fa; text-decoration: none; word-break: break-all; }
    
    .studio-main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }
    .studio-topbar { padding: 1rem 2rem; background: var(--card-bg); border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center; }
    .topbar-actions { display: flex; gap: 0.75rem; }
    .btn { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.55rem 1.1rem; border-radius: 6px; font-size: 0.875rem; font-weight: 600; cursor: pointer; border: none; text-decoration: none; transition: all 0.15s; }
    .btn svg { width: 16px; height: 16px; }
    .btn-primary { background: var(--accent); color: #fff; }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-success { background: var(--success); color: #fff; }
    .btn-success:hover { background: #059669; }
    .btn-secondary { background: #374151; color: #fff; }
    .btn-secondary:hover { background: #4b5563; }
    .btn-danger { background: var(--danger); color: #fff; }
    .btn-danger:hover { background: #dc2626; }
    
    .content-area { padding: 2rem; max-width: 1100px; margin: 0 auto; width: 100%; }
    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 1.75rem; margin-bottom: 1.75rem; }
    .card-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem; }
    .card-title svg { width: 20px; height: 20px; stroke: var(--accent); }
    
    .form-group { margin-bottom: 1.25rem; }
    .form-label { display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text-muted); }
    .form-control { width: 100%; padding: 0.65rem 0.85rem; background: #0f172a; border: 1px solid var(--card-border); border-radius: 6px; color: #fff; font-size: 0.925rem; outline: none; font-family: inherit; }
    .form-control:focus { border-color: var(--accent); }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
    textarea.form-control { resize: vertical; min-height: 380px; font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; line-height: 1.5; }
    
    .flash-alert { padding: 0.85rem 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; }
    .flash-success { background: #064e3b; border: 1px solid #059669; color: #a7f3d0; }
    .flash-danger { background: #7f1d1d; border: 1px solid #dc2626; color: #fecaca; }
    
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .data-table th, .data-table td { padding: 0.85rem 1rem; border-bottom: 1px solid var(--card-border); text-align: left; }
    .data-table th { color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .data-table tr:hover { background: #1e293b; }
    
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-blue { background: #1e3a8a; color: #93c5fd; }
    .badge-purple { background: #3b0764; color: #d8b4fe; }

    /* Quick Connect & Testing Hub Styles */
    .testing-hub { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 2rem; }
    @media (max-width: 990px) { .testing-hub { grid-template-columns: 1fr; } }
    .hub-card { border-radius: 10px; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; position: relative; }
    .hub-lan { border: 1px solid #1e40af; background: linear-gradient(145deg, #0f172a 0%, #172554 100%); }
    .hub-prod { border: 1px solid #065f46; background: linear-gradient(145deg, #091a18 0%, #064e3b 100%); }
    .hub-card-header { display: flex; align-items: flex-start; gap: 0.75rem; }
    .hub-card-icon { width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    .hub-card-body { display: flex; align-items: center; gap: 1.15rem; background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 0.85rem; }
    .hub-qr-box { background: #ffffff; border-radius: 6px; padding: 6px; width: 92px; height: 92px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.4); }
    .hub-qr-box svg { width: 100%; height: 100%; display: block; }
    .hub-details { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; min-width: 0; }
    .hub-url-pill { display: flex; align-items: center; justify-content: space-between; background: #0b1120; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 0.4rem 0.65rem; gap: 0.5rem; }
    .hub-url-text { font-family: 'JetBrains Mono', monospace; font-size: 0.775rem; color: #cbd5e1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .hub-copy-btn { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.15); color: #93c5fd; padding: 0.25rem 0.55rem; border-radius: 4px; font-size: 0.725rem; cursor: pointer; display: inline-flex; align-items: center; gap: 0.35rem; flex-shrink: 0; transition: all 0.15s; }
    .hub-copy-btn:hover { background: #3b82f6; color: #fff; }
    .hub-actions { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
  </style>
</head>
<body>

  <!-- Left Navigation Bar -->
  <aside class="studio-sidebar">
    <div class="studio-brand">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
        <path d="M6 6h10"/>
        <path d="M6 10h10"/>
      </svg>
      <span>shrtnotes Studio</span>
    </div>

    <ul class="nav-menu">
      <li>
        <a href="{{ url_for('route_notes') }}" class="nav-btn {% if active_tab == 'notes' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>
          <span>All Topics ({{ notes_count }})</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_new_note') }}" class="nav-btn {% if active_tab == 'new_note' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
          <span>Write New Topic</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_subjects') }}" class="nav-btn {% if active_tab == 'subjects' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>
          <span>Subjects & Chapters</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_design') }}" class="nav-btn {% if active_tab == 'design' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19 7-7 3 3-7 7-3-3z"/><path d="m18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="m2 2 7.586 7.586"/><circle cx="11" cy="11" r="2"/></svg>
          <span>Design & Theme</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_ads') }}" class="nav-btn {% if active_tab == 'ads' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>
          <span>Monetization & Ads</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_seo') }}" class="nav-btn {% if active_tab == 'seo' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>
          <span>SEO & Google Search</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_legal_pages') }}" class="nav-btn {% if active_tab == 'pages' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <span>Legal Pages</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_deploy') }}" class="nav-btn {% if active_tab == 'deploy' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m16 12-4-4-4 4"/><path d="M12 16V8"/></svg>
          <span>Deploy to GitHub</span>
        </a>
      </li>
    </ul>

    <!-- LAN Mobile & Live Site Info Pill -->
    <div class="lan-pill">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
        <strong style="color: #93c5fd; font-size: 0.8rem;">Mobile Testing (LAN)</strong>
        <span class="badge" style="background: #1e40af; color: #dbeafe; font-size: 0.65rem;">Wi-Fi</span>
      </div>
      <a href="{{ lan_url }}" target="_blank" style="font-size: 0.775rem; color: #60a5fa; word-break: break-all; display: block; margin-bottom: 0.5rem;">{{ lan_url }}</a>
      <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.45rem; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.725rem; color: #94a3b8;">Production:</span>
        <a href="{{ deployed_url }}" target="_blank" style="font-size: 0.725rem; color: #34d399; font-weight: 600; text-decoration: none;">Live Site &rarr;</a>
      </div>
    </div>
  </aside>

  <!-- Main View Area -->
  <main class="studio-main">
    <header class="studio-topbar">
      <div>
        <h2 style="font-size: 1.15rem; font-weight: 600;">{{ page_heading }}</h2>
      </div>
      <div class="topbar-actions">
        <a href="/preview/" target="_blank" class="btn btn-secondary" title="Preview your live site in browser">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
          <span>View Site Preview</span>
        </a>
        <form method="POST" action="{{ url_for('route_rebuild') }}" style="display: inline;">
          <button type="submit" class="btn btn-primary" title="Recompiles all Clean URL HTML pages, XML sitemaps, and robots.txt">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Rebuild Site</span>
          </button>
        </form>
      </div>
    </header>

    <div class="content-area">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, msg in messages %}
            <div class="flash-alert flash-{{ category }}">{{ msg }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}

      <!-- Quick Connect & Device Testing Hub (LAN Mobile QR & Deployed Live Site) -->
      <div class="testing-hub">
        <!-- 1. LAN Mobile Testing Card with QR Code -->
        <div class="hub-card hub-lan">
          <div class="hub-card-header">
            <div class="hub-card-icon" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa;">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><line x1="12" x2="12.01" y1="18" y2="18"/></svg>
            </div>
            <div style="flex: 1; min-width: 0;">
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap;">
                <strong style="font-size: 0.95rem; color: #93c5fd;">LAN Mobile Testing</strong>
                <span class="badge" style="background: #1e3a8a; color: #bfdbfe;">Local Wi-Fi / Hotspot</span>
              </div>
              <p style="font-size: 0.775rem; color: #94a3b8; margin-top: 0.2rem;">Scan with phone camera to test mobile responsive view & LaTeX formulas live</p>
            </div>
          </div>

          <div class="hub-card-body">
            <div class="hub-qr-box" title="Scan with your phone camera to test live on mobile">
              {{ lan_qr_svg|safe }}
            </div>
            <div class="hub-details">
              <div class="hub-url-pill">
                <span class="hub-url-text" title="{{ lan_url }}">{{ lan_url }}</span>
                <button type="button" class="hub-copy-btn" onclick="copyHubUrl('{{ lan_url }}', this)" title="Copy LAN preview URL">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                  <span>Copy</span>
                </button>
              </div>
              <div class="hub-actions">
                <a href="{{ lan_url }}" target="_blank" class="btn btn-primary" style="padding: 0.4rem 0.85rem; font-size: 0.825rem;">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>
                  <span>Open Preview</span>
                </a>
                <span style="font-size: 0.725rem; color: #64748b;">Phone must be on same Wi-Fi</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. Live Deployed Site Card (Next to that) -->
        <div class="hub-card hub-prod">
          <div class="hub-card-header">
            <div class="hub-card-icon" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
            </div>
            <div style="flex: 1; min-width: 0;">
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap;">
                <strong style="font-size: 0.95rem; color: #a7f3d0;">Live Deployed Site</strong>
                <span class="badge" style="background: #064e3b; color: #6ee7b7;">🟢 Cloudflare Pages Live</span>
              </div>
              <p style="font-size: 0.775rem; color: #94a3b8; margin-top: 0.2rem;">Public production website with automatic edge CDN & HTTPS</p>
            </div>
          </div>

          <div class="hub-card-body">
            <div class="hub-qr-box" title="Scan with phone camera to open live deployed site">
              {{ deployed_qr_svg|safe }}
            </div>
            <div class="hub-details">
              <div class="hub-url-pill">
                <span class="hub-url-text" title="{{ deployed_url }}">{{ deployed_url }}</span>
                <button type="button" class="hub-copy-btn" onclick="copyHubUrl('{{ deployed_url }}', this)" title="Copy live site URL">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                  <span>Copy</span>
                </button>
              </div>
              <div class="hub-actions">
                <a href="{{ deployed_url }}" target="_blank" class="btn btn-success" style="padding: 0.4rem 0.85rem; font-size: 0.825rem;">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>
                  <span>Open Live Site</span>
                </a>
                <span style="font-size: 0.725rem; color: #34d399;">shrtnotes.pages.dev</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Dynamic Tab Content -->
      <!-- CONTENT_PLACEHOLDER -->
    </div>
  </main>

  <script>
    function copyHubUrl(text, btn) {
      navigator.clipboard.writeText(text).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span>Copied!</span>`;
        btn.style.background = '#059669';
        btn.style.color = '#ffffff';
        setTimeout(() => {
          btn.innerHTML = originalHtml;
          btn.style.background = '';
          btn.style.color = '';
        }, 1800);
      }).catch(err => {
        prompt('Copy this link:', text);
      });
    }
  </script>
</body>
</html>
"""

# ==============================================================================
# Route: List All Topics
# ==============================================================================
NOTES_LIST_HTML = """
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
    <h3 class="card-title" style="margin-bottom: 0;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <span>Published Study Topics (Chapter-Wise)</span>
    </h3>
    <a href="{{ url_for('route_new_note') }}" class="btn btn-primary">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
      <span>Write Topic</span>
    </a>
  </div>

  <table class="data-table">
    <thead>
      <tr>
        <th>Subject</th>
        <th>Chapter</th>
        <th>Topic Title</th>
        <th>Last Updated</th>
        <th style="text-align: right;">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for note in notes %}
      <tr>
        <td><span class="badge badge-blue">{{ note.subject_name }}</span></td>
        <td><span class="badge badge-purple">{{ note.chapter_name }}</span></td>
        <td>
          <strong>{{ note.title }}</strong>
          {% if note.tags %}
          <div style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-top: 0.3rem;">
            {% for t in note.tags %}
            <span style="font-size: 0.7rem; background: rgba(59, 130, 246, 0.15); color: #93c5fd; padding: 1px 6px; border-radius: 4px;">#{{ t }}</span>
            {% endfor %}
          </div>
          {% endif %}
        </td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">{{ note.last_modified }}</td>
        <td style="text-align: right; white-space: nowrap;">
          <a href="{{ url_for('route_edit_note', rel_path=note.file_path) }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">
            Edit
          </a>
          <form method="POST" action="{{ url_for('route_delete_note') }}" style="display: inline;" onsubmit="return confirm('Delete topic {{ note.title }}?');">
            <input type="hidden" name="rel_path" value="{{ note.file_path }}">
            <button type="submit" class="btn btn-danger" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
      {% if not notes %}
      <tr>
        <td colspan="5" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
          No topics created yet. Click "Write Topic" to publish your first chapter topic!
        </td>
      </tr>
      {% endif %}
    </tbody>
  </table>
</div>
"""

# ==============================================================================
# Route: Topic Editor (New / Edit)
# ==============================================================================
NOTE_FORM_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span>{% if is_edit %}Edit Topic{% else %}Write New Study Topic{% endif %}</span>
  </h3>

  <form method="POST" action="{{ action_url }}">
    {% if is_edit %}
    <input type="hidden" name="original_path" value="{{ original_path }}">
    {% endif %}

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Subject *</label>
        <select name="subject" id="note-subject-select" class="form-control" required onchange="updateChapterOptions()">
          {% for sub in config.subjects %}
          <option value="{{ sub.id }}" {% if note_meta.get('subject') == sub.id %}selected{% endif %}>{{ sub.name }}</option>
          {% endfor %}
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Chapter *</label>
        <select name="chapter" id="note-chapter-select" class="form-control" required>
          <!-- Populated dynamically via JS -->
        </select>
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Topic Title *</label>
        <input type="text" name="title" class="form-control" value="{{ note_meta.get('title', '') }}" placeholder="e.g. Fundamental Theorem of Calculus" required>
      </div>
      <div class="form-group">
        <label class="form-label">URL Slug (lowercase-hyphens) *</label>
        <input type="text" name="slug" class="form-control" value="{{ note_meta.get('slug', '') }}" placeholder="e.g. fundamental-theorem" required>
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Google Search Snippet / Excerpt (1-2 sentences)</label>
        <input type="text" name="excerpt" class="form-control" value="{{ note_meta.get('excerpt', '') }}" placeholder="A 1-2 sentence high-yield summary for Google search results...">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Displays under your topic title in Google search results.</span>
      </div>
      <div class="form-group">
        <label class="form-label">SEO Keywords & Topic Tags (comma-separated)</label>
        <input type="text" name="tags" class="form-control" value="{{ tags_str }}" placeholder="e.g. calculus, derivatives, integration, fundamental-theorem">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Used for Google indexing, Schema.org metadata, and page tag badges.</span>
      </div>
    </div>

    <div class="form-group">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
        <label class="form-label" style="margin-bottom: 0;">Topic Content (Markdown & KaTeX Formulas Supported) *</label>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Inline: $E = mc^2$ | Centered: $$\\int x dx$$</span>
      </div>
      <textarea name="content" class="form-control" placeholder="Write your topic notes here..." required>{{ raw_content }}</textarea>
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
        <span>Save Topic & Rebuild Clean URLs</span>
      </button>
      <a href="{{ url_for('route_notes') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>

<script>
  const subjectsData = {{ subjects_json|safe }};
  const currentChapter = "{{ note_meta.get('chapter', '') }}";

  function updateChapterOptions() {
    const subSelect = document.getElementById('note-subject-select');
    const chSelect = document.getElementById('note-chapter-select');
    const selectedSubId = subSelect.value;

    chSelect.innerHTML = '';
    const subObj = subjectsData.find(s => s.id === selectedSubId);
    if (subObj && subObj.chapters && subObj.chapters.length > 0) {
      subObj.chapters.forEach(ch => {
        const opt = document.createElement('option');
        opt.value = ch.id;
        opt.textContent = ch.name;
        if (ch.id === currentChapter || ch.name.toLowerCase() === currentChapter.toLowerCase()) {
          opt.selected = true;
        }
        chSelect.appendChild(opt);
      });
    } else {
      const opt = document.createElement('option');
      opt.value = 'general';
      opt.textContent = 'General Concepts';
      chSelect.appendChild(opt);
    }
  }

  // Initialize on page load
  updateChapterOptions();
</script>
"""

# ==============================================================================
# Route: Subject & Chapter Hierarchy Manager
# ==============================================================================
SUBJECTS_HTML = """
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
    <h3 class="card-title" style="margin-bottom: 0;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>
      <span>Site Tree: Subjects & Chapters Hierarchy</span>
    </h3>
  </div>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Structure your notes into Chapters and Topics. You can add new chapters under any subject, edit names, or customize icons.
  </p>

  {% for sub in config.subjects %}
  <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.75rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div style="width: 32px; height: 32px; border-radius: 6px; background: #1e293b; display: flex; align-items: center; justify-content: center; color: var(--accent);">
          {{ get_icon(sub.icon)|safe }}
        </div>
        <div>
          <strong style="font-size: 1.05rem;">{{ sub.name }}</strong>
          <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 0.5rem;">(<code>/{{ sub.id }}/</code>)</span>
        </div>
      </div>
      <div style="display: flex; gap: 0.5rem;">
        <a href="{{ url_for('route_edit_subject', sub_id=sub.id) }}" class="btn btn-secondary" style="padding: 0.3rem 0.65rem; font-size: 0.775rem;">Edit Subject</a>
        <form method="POST" action="{{ url_for('route_delete_subject', sub_id=sub.id) }}" style="display: inline;" onsubmit="return confirm('Delete subject {{ sub.name }} and all its chapters?');">
          <button type="submit" class="btn btn-danger" style="padding: 0.3rem 0.65rem; font-size: 0.775rem;">Delete</button>
        </form>
      </div>
    </div>

    <!-- Chapters list under this subject -->
    <div style="margin-left: 1rem;">
      <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.6rem; letter-spacing: 0.05em;">
        Chapters in {{ sub.name }}:
      </div>
      <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;">
        {% for ch in sub.chapters %}
        <div style="background: #111827; border: 1px solid var(--card-border); border-radius: 6px; padding: 0.65rem 0.85rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="font-size: 0.9rem;">{{ ch.name }}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;"><code>/{{ sub.id }}/{{ ch.id }}/</code></span>
            {% if ch.description %}
            <p style="font-size: 0.775rem; color: var(--text-muted); margin-top: 0.15rem;">{{ ch.description }}</p>
            {% endif %}
          </div>
          <div style="display: flex; gap: 0.4rem;">
            <a href="{{ url_for('route_new_note') }}?sub={{ sub.id }}&ch={{ ch.id }}" class="btn btn-success" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;">+ Add Topic</a>
            <a href="{{ url_for('route_edit_chapter', sub_id=sub.id, ch_id=ch.id) }}" class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;">Edit</a>
            <form method="POST" action="{{ url_for('route_delete_chapter', sub_id=sub.id, ch_id=ch.id) }}" style="display: inline;" onsubmit="return confirm('Delete chapter {{ ch.name }}?');">
              <button type="submit" class="btn btn-danger" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;">Delete</button>
            </form>
          </div>
        </div>
        {% endfor %}
        {% if not sub.chapters %}
        <div style="color: var(--text-muted); font-size: 0.8rem; font-style: italic;">No chapters added yet. Add a chapter below.</div>
        {% endif %}
      </div>

      <!-- Quick Add Chapter Form -->
      <form method="POST" action="{{ url_for('route_add_chapter', sub_id=sub.id) }}" style="background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 6px; border: 1px dashed var(--card-border); display: flex; gap: 0.75rem; align-items: center;">
        <input type="text" name="ch_name" class="form-control" placeholder="New Chapter Name (e.g. Thermodynamics)" style="padding: 0.4rem 0.65rem; font-size: 0.85rem;" required>
        <input type="text" name="ch_id" class="form-control" placeholder="Slug (e.g. thermodynamics)" style="padding: 0.4rem 0.65rem; font-size: 0.85rem;" required>
        <input type="text" name="ch_desc" class="form-control" placeholder="Short description (optional)" style="padding: 0.4rem 0.65rem; font-size: 0.85rem;">
        <button type="submit" class="btn btn-primary" style="white-space: nowrap; padding: 0.4rem 0.85rem; font-size: 0.825rem;">+ Add Chapter</button>
      </form>
    </div>
  </div>
  {% endfor %}

  <!-- Add New Subject Form -->
  <h4 style="font-size: 1.05rem; margin: 2rem 0 1rem; color: #93c5fd;">Create New Subject</h4>
  <form method="POST" action="{{ url_for('route_add_subject') }}">
    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Subject ID (lowercase, e.g. 'economics') *</label>
        <input type="text" name="sub_id" class="form-control" placeholder="e.g. economics" required>
      </div>
      <div class="form-group">
        <label class="form-label">Subject Name (e.g. 'Economics') *</label>
        <input type="text" name="sub_name" class="form-control" placeholder="e.g. Economics" required>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Short Description *</label>
      <input type="text" name="sub_desc" class="form-control" placeholder="e.g. Microeconomics, macroeconomics, and market principles." required>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Choose Preset Icon</label>
        <select name="sub_icon_preset" class="form-control">
          {% for icon_key in preset_keys %}
          <option value="{{ icon_key }}">{{ icon_key|title }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">OR Paste Custom SVG Code (Optional)</label>
        <input type="text" name="sub_icon_custom" class="form-control" placeholder="Paste &lt;svg ...&gt;...&lt;/svg&gt; markup">
      </div>
    </div>

    <button type="submit" class="btn btn-primary" style="margin-top: 0.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
      <span>Add Subject</span>
    </button>
  </form>
</div>
"""

CHAPTER_EDIT_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span>Edit Chapter: {{ target_chapter.name }} ({{ sub.name }})</span>
  </h3>

  <form method="POST" action="{{ url_for('route_save_chapter', sub_id=sub.id, ch_id=target_chapter.id) }}">
    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Chapter ID</label>
        <input type="text" class="form-control" value="{{ target_chapter.id }}" readonly style="opacity: 0.6; cursor: not-allowed;">
      </div>
      <div class="form-group">
        <label class="form-label">Chapter Name *</label>
        <input type="text" name="ch_name" class="form-control" value="{{ target_chapter.name }}" required>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Chapter Description</label>
      <input type="text" name="ch_desc" class="form-control" value="{{ target_chapter.description }}">
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
        <span>Save Chapter & Rebuild</span>
      </button>
      <a href="{{ url_for('route_subjects') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
"""

SUBJECT_EDIT_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span>Edit Subject: {{ target_sub.name }}</span>
  </h3>

  <form method="POST" action="{{ url_for('route_save_subject', sub_id=target_sub.id) }}">
    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Subject ID</label>
        <input type="text" class="form-control" value="{{ target_sub.id }}" readonly style="opacity: 0.6; cursor: not-allowed;">
      </div>
      <div class="form-group">
        <label class="form-label">Display Name *</label>
        <input type="text" name="sub_name" class="form-control" value="{{ target_sub.name }}" required>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Description *</label>
      <input type="text" name="sub_desc" class="form-control" value="{{ target_sub.description }}" required>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Preset Icon</label>
        <select name="sub_icon_preset" class="form-control">
          {% for icon_key in preset_keys %}
          <option value="{{ icon_key }}" {% if target_sub.icon == icon_key %}selected{% endif %}>{{ icon_key|title }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Current Icon Preview</label>
        <div style="width: 44px; height: 44px; border-radius: 8px; background: #1e293b; display: flex; align-items: center; justify-content: center; color: var(--accent);">
          {{ get_icon(target_sub.icon)|safe }}
        </div>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">OR Paste Custom SVG Code (Overrides Preset Icon)</label>
      <textarea name="sub_icon_custom" class="form-control" style="min-height: 120px;" placeholder="Paste &lt;svg ...&gt;...&lt;/svg&gt; markup">{% if target_sub.icon.startswith('<svg') %}{{ target_sub.icon }}{% endif %}</textarea>
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
        <span>Save Changes & Rebuild</span>
      </button>
      <a href="{{ url_for('route_subjects') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
"""

# ==============================================================================
# Route: Universal Multi-Network Ad Manager
# ==============================================================================
ADS_HTML = """
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
    <h3 class="card-title" style="margin-bottom: 0;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>
      <span>Universal Ad Platform & Monetization Manager</span>
    </h3>
    <span class="badge" style="background: #064e3b; color: #a7f3d0; font-size: 0.8rem; padding: 0.35rem 0.75rem;">Zero-CLS Containers Active</span>
  </div>
  
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Supports <strong>Google AdSense, Adsterra, Media.net, Ezoic, Carbon, custom sponsor banners, or any network</strong>. Paste your network's code in the matching slot dimensions below.
  </p>

  <!-- Dimension Quick Reference Card -->
  <div style="background: #172554; border: 1px solid #1e40af; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; font-weight: 700; color: #93c5fd; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">
      Standard IAB Ad Dimensions Cheat-Sheet:
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; font-size: 0.8rem; color: #cbd5e1;">
      <div>&bull; <strong>Header:</strong> 728&times;90 (Desktop) / 320&times;50 (Mobile)</div>
      <div>&bull; <strong>In-Article:</strong> 300&times;250 (Medium) / 336&times;280</div>
      <div>&bull; <strong>Sidebar Rail:</strong> 300&times;600 (Half Page) / 160&times;600</div>
      <div>&bull; <strong>Footer:</strong> 728&times;90 (Leaderboard) / 468&times;60</div>
    </div>
  </div>

  <form method="POST" action="{{ url_for('route_save_ads') }}">
    <div class="form-group" style="margin-bottom: 1.5rem;">
      <label style="display: flex; align-items: center; gap: 0.75rem; font-size: 1rem; cursor: pointer;">
        <input type="checkbox" name="ads_enabled" value="true" {% if config.ads.enabled %}checked{% endif %} style="width: 20px; height: 20px;">
        <span><strong>Enable Ads Across Website</strong></span>
      </label>
    </div>

    <!-- Global Head Script -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px;">
      <label class="form-label">Global &lt;head&gt; Ad Script / Tag (Universal)</label>
      <textarea name="head_code" class="form-control" style="min-height: 80px;" placeholder="Paste any header script from Google AdSense, Media.net, or Ezoic (e.g. &lt;script async src=...&gt;&lt;/script&gt;)">{{ config.ads.head_code }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">This script will be injected into the &lt;head&gt; of all pages automatically.</span>
    </div>

    <!-- Slot 1: Header Banner -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">1. Top Header Banner Ad Code</label>
        <div style="display: flex; gap: 0.35rem;">
          <span class="badge" style="background: #1e3a8a; color: #93c5fd;">728&times;90 Desktop Leaderboard</span>
          <span class="badge" style="background: #064e3b; color: #a7f3d0;">320&times;50 Mobile</span>
        </div>
      </div>
      <textarea name="header_ad" class="form-control" style="min-height: 90px;" placeholder="Paste HTML/JS ad unit code for the 728x90 or 320x50 top header leaderboard">{{ config.ads.header_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Appears right below navigation on all pages. Fixed container prevents page jumping.</span>
    </div>

    <!-- Slot 2: In-Article Ad -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">2. In-Article Ad Code (Inside Study Topic)</label>
        <div style="display: flex; gap: 0.35rem;">
          <span class="badge" style="background: #1e3a8a; color: #93c5fd;">300&times;250 Medium Rectangle</span>
          <span class="badge" style="background: #064e3b; color: #a7f3d0;">336&times;280 Large Rectangle</span>
        </div>
      </div>
      <textarea name="in_article_ad" class="form-control" style="min-height: 90px;" placeholder="Paste HTML/JS ad unit code for 300x250 or 336x280 in-article unit">{{ config.ads.in_article_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Placed right before main topic prose notes. Highest visibility for reading users.</span>
    </div>

    <!-- Slot 3: Sidebar Sticky Ad -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">3. Desktop Sticky Sidebar & Lateral Rail Ad Code</label>
        <div style="display: flex; gap: 0.35rem;">
          <span class="badge" style="background: #1e3a8a; color: #93c5fd;">300&times;600 Half-Page</span>
          <span class="badge" style="background: #064e3b; color: #a7f3d0;">160&times;600 Skyscraper</span>
          <span class="badge" style="background: #581c87; color: #e9d5ff;">300&times;250</span>
        </div>
      </div>
      <textarea name="sidebar_ad" class="form-control" style="min-height: 90px;" placeholder="Paste HTML/JS ad unit code for 300x600, 160x600, or 300x250 sidebar placement">{{ config.ads.sidebar_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Pins to the lateral rail on widescreen desktop screens without disturbing reading flow.</span>
    </div>

    <!-- Slot 4: Footer Ad -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">4. Bottom Footer Banner Ad Code</label>
        <div style="display: flex; gap: 0.35rem;">
          <span class="badge" style="background: #1e3a8a; color: #93c5fd;">728&times;90 Leaderboard</span>
          <span class="badge" style="background: #064e3b; color: #a7f3d0;">468&times;60 Classic Banner</span>
        </div>
      </div>
      <textarea name="footer_ad" class="form-control" style="min-height: 90px;" placeholder="Paste HTML/JS ad unit code for 728x90 or 468x60 bottom banner">{{ config.ads.footer_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Displays above the footer. Catches users after finishing reading a note.</span>
    </div>

    <!-- Google AdSense Quick Setup Accordion/Helper -->
    <div style="background: #172554; border: 1px solid #1e40af; border-radius: 8px; padding: 1.25rem; margin-top: 1.5rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin-bottom: 0.5rem;">Google AdSense Quick Setup (Optional Helper)</h4>
      <p style="font-size: 0.8rem; color: #cbd5e1; margin-bottom: 1rem;">
        If you prefer not to paste raw ad snippets and want standard AdSense units, enter your Client ID and Slot IDs below:
      </p>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label" style="color: #93c5fd;">AdSense Client ID</label>
          <input type="text" name="adsense_client_id" class="form-control" value="{{ config.ads.adsense.client_id }}" placeholder="ca-pub-1234567890123456">
        </div>
        <div class="form-group">
          <label class="form-label" style="color: #93c5fd;">Header Slot ID (728&times;90)</label>
          <input type="text" name="adsense_header_slot" class="form-control" value="{{ config.ads.adsense.header_slot }}" placeholder="e.g. 1234567890">
        </div>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label" style="color: #93c5fd;">In-Article Slot ID (300&times;250)</label>
          <input type="text" name="adsense_in_article_slot" class="form-control" value="{{ config.ads.adsense.in_article_slot }}" placeholder="e.g. 2345678901">
        </div>
        <div class="form-group">
          <label class="form-label" style="color: #93c5fd;">Sidebar Slot ID (300&times;600 / 160&times;600)</label>
          <input type="text" name="adsense_sidebar_slot" class="form-control" value="{{ config.ads.adsense.sidebar_slot }}" placeholder="e.g. 3456789012">
        </div>
      </div>
    </div>

    <button type="submit" class="btn btn-success" style="margin-top: 1.5rem; font-size: 1rem; padding: 0.75rem 1.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
      <span>Save Ad Settings & Rebuild Site</span>
    </button>
  </form>
</div>
"""

SEO_HTML = """
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
    <h3 class="card-title" style="margin-bottom: 0;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>
      <span>Search Engine Optimization (SEO) & Google Console Setup</span>
    </h3>
    <a href="https://search.google.com/search-console" target="_blank" rel="noopener" class="btn btn-primary" style="font-size: 0.8rem; padding: 0.4rem 0.85rem;">
      Open Google Search Console &rarr;
    </a>
  </div>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Configure all necessary meta tags, search engine verification codes, indexing rules, and structured sitemaps required for Googlebot ranking and AdSense approval.
  </p>

  <form method="POST" action="{{ url_for('route_save_seo') }}">
    <!-- Card 1: Google Search Console Verification -->
    <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        <span>1. Search Engine Ownership Verification</span>
      </h4>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">
        Prove ownership of your website in Google Search Console and Bing Webmaster Tools. Paste either the full &lt;meta&gt; tag or just the verification code.
      </p>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Google Search Console Verification Tag / Code *</label>
          <input type="text" name="google_site_verification" class="form-control" value="{{ seo.get('google_site_verification', '') }}" placeholder="e.g. google-site-verification=abcXYZ or abcXYZ">
          <span style="font-size: 0.75rem; color: var(--text-muted);">From GSC &rarr; Settings &rarr; Ownership verification &rarr; HTML Tag</span>
        </div>
        <div class="form-group">
          <label class="form-label">Bing Webmaster Tools Verification Tag (Optional)</label>
          <input type="text" name="bing_site_verification" class="form-control" value="{{ seo.get('bing_site_verification', '') }}" placeholder="e.g. msvalidate.01 code or full meta tag">
          <span style="font-size: 0.75rem; color: var(--text-muted);">For indexing on Bing & Yahoo search.</span>
        </div>
      </div>
    </div>

    <!-- Card 2: XML Sitemap & Crawling Control -->
    <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/></svg>
        <span>2. XML Sitemap & Google Indexing Directives</span>
      </h4>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">
        Your sitemap is automatically generated with Clean URLs for all Subjects, Chapters, Topics, and Compliance pages.
      </p>

      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 0.85rem 1rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; display: block;">Your Live Sitemap URL:</span>
          <code id="sitemap-url-val" style="color: #38bdf8; font-size: 0.875rem;">{{ config.site_url }}/sitemap.xml</code>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button type="button" class="btn btn-secondary" onclick="copySitemapUrl()" id="copy-sitemap-btn" style="font-size: 0.75rem; padding: 0.35rem 0.75rem;">
            Copy Sitemap URL
          </button>
          <a href="https://search.google.com/search-console/sitemaps" target="_blank" rel="noopener" class="btn btn-primary" style="font-size: 0.75rem; padding: 0.35rem 0.75rem;">
            Submit to Google &rarr;
          </a>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Robots Indexing Directive</label>
        <input type="text" name="robots_directive" class="form-control" value="{{ seo.get('robots_directive', 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1') }}" required>
        <span style="font-size: 0.75rem; color: var(--text-muted);">
          <code>max-image-preview:large</code> allows Google Discover and rich image search snippets.
        </span>
      </div>
    </div>

    <!-- Card 3: Global Search Keywords & Descriptions -->
    <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
        <span>3. Global Search Keywords & Meta Descriptions</span>
      </h4>

      <div class="form-group">
        <label class="form-label">Global Website Keywords (comma-separated)</label>
        <input type="text" name="meta_keywords" class="form-control" value="{{ seo.get('meta_keywords', '') }}" placeholder="e.g. study notes, short notes, high yield formulas, mathematics, physics, chemistry, biology, exam revision">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Keywords applicable to your entire study platform. (Individual topics also have their own per-topic tags!)</span>
      </div>

      <div class="form-group">
        <label class="form-label">Global Fallback Meta Description</label>
        <input type="text" name="meta_description" class="form-control" value="{{ seo.get('meta_description', config.description) }}" placeholder="A 150-160 character description of your website for search engines...">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Used on your homepage, search results, and category archives.</span>
      </div>
    </div>

    <!-- Card 4: Social Sharing, OpenGraph & Google Analytics -->
    <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
        <span>4. Social Sharing & Analytics (GA4)</span>
      </h4>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Default Social Share Image URL (og:image)</label>
          <input type="url" name="og_image" class="form-control" value="{{ seo.get('og_image', '') }}" placeholder="https://shrtnotes.pages.dev/static/images/og-preview.png">
          <span style="font-size: 0.75rem; color: var(--text-muted);">Displays when someone shares your notes on Twitter, WhatsApp, or LinkedIn.</span>
        </div>
        <div class="form-group">
          <label class="form-label">Twitter / X Handle (Optional)</label>
          <input type="text" name="twitter_handle" class="form-control" value="{{ seo.get('twitter_handle', '') }}" placeholder="@shrtnotes">
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Google Analytics Measurement ID (GA4)</label>
        <input type="text" name="google_analytics_id" class="form-control" value="{{ config.analytics.get('google_analytics_id', '') or seo.get('google_analytics_id', '') }}" placeholder="G-XXXXXXXXXX">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Tracks visitor count, popular study notes, and search queries in Google Analytics.</span>
      </div>
    </div>

    <button type="submit" class="btn btn-success" style="font-size: 1rem; padding: 0.75rem 1.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
      <span>Save SEO Settings & Rebuild Website</span>
    </button>
  </form>
</div>

<script>
function copySitemapUrl() {
  const url = document.getElementById("sitemap-url-val").innerText;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.getElementById("copy-sitemap-btn");
    btn.textContent = "Copied!";
    btn.style.background = "#10b981";
    setTimeout(() => {
      btn.textContent = "Copy Sitemap URL";
      btn.style.background = "";
    }, 2500);
  });
}
</script>
"""


# ==============================================================================
# Helper for Rendering Studio Templates
# ==============================================================================
def render_studio_view(child_content, active_tab, page_heading, **kwargs):
    config = load_config()
    notes = get_all_notes_list()
    lan_ip = get_local_ip()

    lan_url = f"http://{lan_ip}:5050/preview/"
    deployed_url = config.get("site_url", "https://shrtnotes.pages.dev").rstrip("/")
    if not deployed_url:
        deployed_url = "https://shrtnotes.pages.dev"

    lan_qr_svg = generate_qr_svg(lan_url)
    deployed_qr_svg = generate_qr_svg(deployed_url)

    cleaned = child_content.replace('{% extends "studio_base" %}', '').replace('{% block studio_content %}', '').replace('{% endblock %}', '')
    full_template = STUDIO_HTML.replace('<!-- CONTENT_PLACEHOLDER -->', cleaned)

    return render_template_string(
        full_template,
        active_tab=active_tab,
        page_heading=page_heading,
        config=config,
        notes_count=len(notes),
        lan_ip=lan_ip,
        lan_url=lan_url,
        deployed_url=deployed_url,
        lan_qr_svg=lan_qr_svg,
        deployed_qr_svg=deployed_qr_svg,
        get_icon=get_icon,
        **kwargs
    )


# ==============================================================================
# Flask Endpoints
# ==============================================================================
@app.route("/")
def route_index():
    return redirect(url_for("route_notes"))


@app.route("/notes")
def route_notes():
    notes = get_all_notes_list()
    return render_studio_view(
        NOTES_LIST_HTML,
        active_tab="notes",
        page_heading="All Published Topics (Chapter-Wise)",
        notes=notes
    )


@app.route("/notes/new")
def route_new_note():
    config = load_config()
    pre_sub = request.args.get("sub", "")
    pre_ch = request.args.get("ch", "")

    note_meta = {}
    if pre_sub:
        note_meta["subject"] = pre_sub
    if pre_ch:
        note_meta["chapter"] = pre_ch

    return render_studio_view(
        NOTE_FORM_HTML,
        active_tab="new_note",
        page_heading="Write New Study Topic",
        is_edit=False,
        note_meta=note_meta,
        tags_str="",
        raw_content="",
        subjects_json=json.dumps(config.get("subjects", [])),
        action_url=url_for("route_save_note")
    )


@app.route("/notes/edit")
def route_edit_note():
    rel_path = request.args.get("rel_path")
    if not rel_path:
        flash("Note path not specified.", "danger")
        return redirect(url_for("route_notes"))

    target_file = NOTES_DIR / rel_path
    if not target_file.exists():
        flash("Topic file does not exist.", "danger")
        return redirect(url_for("route_notes"))

    meta, raw_content = parse_frontmatter(target_file)
    meta["slug"] = meta.get("slug") or target_file.stem
    config = load_config()

    tags_val = meta.get("tags", [])
    if isinstance(tags_val, list):
        tags_str = ", ".join(tags_val)
    elif isinstance(tags_val, str):
        tags_str = tags_val
    else:
        tags_str = ""

    return render_studio_view(
        NOTE_FORM_HTML,
        active_tab="notes",
        page_heading=f"Edit Topic: {meta.get('title', '')}",
        is_edit=True,
        original_path=rel_path,
        note_meta=meta,
        tags_str=tags_str,
        raw_content=raw_content,
        subjects_json=json.dumps(config.get("subjects", [])),
        action_url=url_for("route_save_note")
    )


@app.route("/notes/save", methods=["POST"])
def route_save_note():
    is_edit = bool(request.form.get("original_path"))
    original_path = request.form.get("original_path")
    title = request.form.get("title", "").strip()
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    subject = request.form.get("subject", "").strip().lower()
    chapter = request.form.get("chapter", "").strip().lower().replace(" ", "-")
    excerpt = request.form.get("excerpt", "").strip()
    raw_tags = request.form.get("tags", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not slug or not subject:
        flash("Title, Slug, and Subject are required.", "danger")
        return redirect(request.referrer or url_for("route_notes"))

    today_str = datetime.now().strftime("%Y-%m-%d")

    date_val = today_str
    if is_edit and original_path:
        old_file = NOTES_DIR / original_path
        if old_file.exists():
            old_meta, _ = parse_frontmatter(old_file)
            date_val = old_meta.get("date", today_str)
            target_path = NOTES_DIR / subject / chapter / f"{slug}.md"
            if str(old_file) != str(target_path):
                old_file.unlink()

    tags_list = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

    frontmatter = {
        "title": title,
        "slug": slug,
        "subject": subject,
        "chapter": chapter,
        "excerpt": excerpt,
        "tags": tags_list,
        "date": date_val,
        "last_modified": today_str
    }

    target_dir = NOTES_DIR / subject / chapter
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{slug}.md"

    file_content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{content}\n"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(file_content)

    count = build_site()
    flash(f"Topic '{title}' saved successfully under {chapter.title()}! Rebuilt {count} topics with Clean URLs.", "success")
    return redirect(url_for("route_notes"))


@app.route("/notes/delete", methods=["POST"])
def route_delete_note():
    rel_path = request.form.get("rel_path")
    if rel_path:
        target_file = NOTES_DIR / rel_path
        if target_file.exists():
            target_file.unlink()
            build_site()
            flash("Topic deleted and Clean URLs rebuilt.", "success")
    return redirect(url_for("route_notes"))


# ==============================================================================
# Subjects & Chapters Management
# ==============================================================================
@app.route("/subjects")
def route_subjects():
    return render_studio_view(
        SUBJECTS_HTML,
        active_tab="subjects",
        page_heading="Subject Directory & Chapter Tree",
        preset_keys=list(DEFAULT_ICONS.keys())
    )


@app.route("/subjects/add", methods=["POST"])
def route_add_subject():
    sub_id = request.form.get("sub_id", "").strip().lower()
    sub_name = request.form.get("sub_name", "").strip()
    sub_desc = request.form.get("sub_desc", "").strip()
    sub_icon_custom = request.form.get("sub_icon_custom", "").strip()
    sub_icon_preset = request.form.get("sub_icon_preset", "book").strip()

    icon_val = sub_icon_custom if sub_icon_custom.startswith("<svg") else sub_icon_preset

    if not sub_id or not sub_name:
        flash("Subject ID and Name are required.", "danger")
        return redirect(url_for("route_subjects"))

    config = load_config()
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            flash(f"Subject '{sub_id}' already exists.", "danger")
            return redirect(url_for("route_subjects"))

    config["subjects"].append({
        "id": sub_id,
        "name": sub_name,
        "description": sub_desc,
        "icon": icon_val,
        "chapters": []
    })

    save_config(config)
    build_site()
    flash(f"Subject '{sub_name}' added! Clean category URL created at /{sub_id}/.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/edit/<sub_id>")
def route_edit_subject(sub_id):
    config = load_config()
    target = next((s for s in config.get("subjects", []) if s["id"] == sub_id), None)
    if not target:
        flash("Subject not found.", "danger")
        return redirect(url_for("route_subjects"))

    return render_studio_view(
        SUBJECT_EDIT_HTML,
        active_tab="subjects",
        page_heading=f"Edit Subject: {target['name']}",
        target_sub=target,
        preset_keys=list(DEFAULT_ICONS.keys())
    )


@app.route("/subjects/save/<sub_id>", methods=["POST"])
def route_save_subject(sub_id):
    config = load_config()
    sub_name = request.form.get("sub_name", "").strip()
    sub_desc = request.form.get("sub_desc", "").strip()
    sub_icon_custom = request.form.get("sub_icon_custom", "").strip()
    sub_icon_preset = request.form.get("sub_icon_preset", "book").strip()

    icon_val = sub_icon_custom if sub_icon_custom.startswith("<svg") else sub_icon_preset

    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            s["name"] = sub_name
            s["description"] = sub_desc
            s["icon"] = icon_val
            break

    save_config(config)
    build_site()
    flash(f"Subject '{sub_name}' updated successfully.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/delete/<sub_id>", methods=["POST"])
def route_delete_subject(sub_id):
    config = load_config()
    config["subjects"] = [s for s in config.get("subjects", []) if s["id"] != sub_id]
    save_config(config)
    build_site()
    flash(f"Subject '{sub_id}' deleted.", "success")
    return redirect(url_for("route_subjects"))


# Chapter Management
@app.route("/subjects/<sub_id>/chapter/add", methods=["POST"])
def route_add_chapter(sub_id):
    ch_name = request.form.get("ch_name", "").strip()
    ch_id = request.form.get("ch_id", "").strip().lower().replace(" ", "-")
    ch_desc = request.form.get("ch_desc", "").strip()

    if not ch_name or not ch_id:
        flash("Chapter name and slug are required.", "danger")
        return redirect(url_for("route_subjects"))

    config = load_config()
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            if "chapters" not in s:
                s["chapters"] = []
            # Check duplicate
            if any(c["id"] == ch_id for c in s["chapters"]):
                flash(f"Chapter '{ch_id}' already exists under this subject.", "danger")
                return redirect(url_for("route_subjects"))
            s["chapters"].append({
                "id": ch_id,
                "name": ch_name,
                "description": ch_desc
            })
            break

    save_config(config)
    build_site()
    flash(f"Chapter '{ch_name}' added under {sub_id}! Clean URL created at /{sub_id}/{ch_id}/.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/<sub_id>/chapter/edit/<ch_id>")
def route_edit_chapter(sub_id, ch_id):
    config = load_config()
    sub = next((s for s in config.get("subjects", []) if s["id"] == sub_id), None)
    if not sub:
        flash("Subject not found.", "danger")
        return redirect(url_for("route_subjects"))

    target_ch = next((c for c in sub.get("chapters", []) if c["id"] == ch_id), None)
    if not target_ch:
        flash("Chapter not found.", "danger")
        return redirect(url_for("route_subjects"))

    return render_studio_view(
        CHAPTER_EDIT_HTML,
        active_tab="subjects",
        page_heading=f"Edit Chapter: {target_ch['name']}",
        sub=sub,
        target_chapter=target_ch
    )


@app.route("/subjects/<sub_id>/chapter/save/<ch_id>", methods=["POST"])
def route_save_chapter(sub_id, ch_id):
    ch_name = request.form.get("ch_name", "").strip()
    ch_desc = request.form.get("ch_desc", "").strip()

    config = load_config()
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            for c in s.get("chapters", []):
                if c["id"] == ch_id:
                    c["name"] = ch_name
                    c["description"] = ch_desc
                    break

    save_config(config)
    build_site()
    flash(f"Chapter '{ch_name}' updated successfully.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/<sub_id>/chapter/delete/<ch_id>", methods=["POST"])
def route_delete_chapter(sub_id, ch_id):
    config = load_config()
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            s["chapters"] = [c for c in s.get("chapters", []) if c["id"] != ch_id]
            break

    save_config(config)
    build_site()
    flash("Chapter removed from tree.", "success")
    return redirect(url_for("route_subjects"))


# ==============================================================================
# Design, Ads, and Pages Routes
# ==============================================================================
@app.route("/design")
def route_design():
    config = load_config()
    current_template = config.get("theme", {}).get("template", "modern")
    return render_studio_view(
        """
        <div class="card">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19 7-7 3 3-7 7-3-3z"/><path d="m18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="m2 2 7.586 7.586"/><circle cx="11" cy="11" r="2"/></svg>
            <span>Website Design, Themes & Templates</span>
          </h3>
          <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
            Switch design templates anytime. All 3 templates share the exact same structural grid, container paddings, and alignment geometry, so <strong>your site alignment and ads will NEVER be disturbed or misaligned</strong>.
          </p>

          <form method="POST" action="{{ url_for('route_save_design') }}">
            <!-- Template Selector Cards -->
            <div style="margin-bottom: 2rem;">
              <label class="form-label" style="font-size: 0.95rem; font-weight: 700; color: #93c5fd; margin-bottom: 0.75rem;">
                Select Active Design Template:
              </label>

              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                <!-- Template 1: Modern Minimalist -->
                <label style="display: block; cursor: pointer;">
                  <div style="background: #0f172a; border: 2px solid {% if current_template == 'modern' %}#3b82f6{% else %}var(--card-border){% endif %}; border-radius: 8px; padding: 1.25rem; transition: all 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                      <strong style="font-size: 1rem; color: #fff;">1. Modern Minimalist</strong>
                      <input type="radio" name="template" value="modern" {% if current_template == 'modern' %}checked{% endif %} style="width: 18px; height: 18px;">
                    </div>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                      Clean neo-grotesque sans-serif, crisp blue accents, rounded corners. Default clean look.
                    </p>
                    <div style="display: flex; gap: 0.4rem;">
                      <span class="badge" style="background: #1e3a8a; color: #93c5fd;">Inter Font</span>
                      <span class="badge" style="background: #2563eb; color: #ffffff;">#2563eb Blue</span>
                    </div>
                  </div>
                </label>

                <!-- Template 2: Academic Classic -->
                <label style="display: block; cursor: pointer;">
                  <div style="background: #0f172a; border: 2px solid {% if current_template == 'academic' %}#14b8a6{% else %}var(--card-border){% endif %}; border-radius: 8px; padding: 1.25rem; transition: all 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                      <strong style="font-size: 1rem; color: #fff;">2. Academic Classic</strong>
                      <input type="radio" name="template" value="academic" {% if current_template == 'academic' %}checked{% endif %} style="width: 18px; height: 18px;">
                    </div>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                      Scholarly serif headings (Merriweather), refined forest emerald accents, textbook editorial styling.
                    </p>
                    <div style="display: flex; gap: 0.4rem;">
                      <span class="badge" style="background: #064e3b; color: #a7f3d0;">Serif Headings</span>
                      <span class="badge" style="background: #0f766e; color: #ffffff;">#0f766e Emerald</span>
                    </div>
                  </div>
                </label>

                <!-- Template 3: Obsidian Tech -->
                <label style="display: block; cursor: pointer;">
                  <div style="background: #0f172a; border: 2px solid {% if current_template == 'obsidian' %}#8b5cf6{% else %}var(--card-border){% endif %}; border-radius: 8px; padding: 1.25rem; transition: all 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                      <strong style="font-size: 1rem; color: #fff;">3. Obsidian Tech</strong>
                      <input type="radio" name="template" value="obsidian" {% if current_template == 'obsidian' %}checked{% endif %} style="width: 18px; height: 18px;">
                    </div>
                    <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                      Cyber technical aesthetic, sleek violet & indigo accents, monospace metadata badges. High-contrast formula focus.
                    </p>
                    <div style="display: flex; gap: 0.4rem;">
                      <span class="badge" style="background: #3b0764; color: #d8b4fe;">Monospace Badges</span>
                      <span class="badge" style="background: #7c3aed; color: #ffffff;">#7c3aed Violet</span>
                    </div>
                  </div>
                </label>
              </div>
            </div>

            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Website Name</label>
                <input type="text" name="site_name" class="form-control" value="{{ config.site_name }}" required>
              </div>
              <div class="form-group">
                <label class="form-label">Tagline</label>
                <input type="text" name="tagline" class="form-control" value="{{ config.tagline }}" required>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Site Meta Description</label>
              <input type="text" name="description" class="form-control" value="{{ config.description }}" required>
            </div>
            <div class="form-grid">
              <div class="form-group">
                <label class="form-label">Site Canonical URL (without trailing slash)</label>
                <input type="url" name="site_url" class="form-control" value="{{ config.site_url }}" required>
              </div>
              <div class="form-group">
                <label class="form-label">Author / Editorial Attribution</label>
                <input type="text" name="author" class="form-control" value="{{ config.author }}" required>
              </div>
            </div>
            <button type="submit" class="btn btn-success" style="margin-top: 1.5rem; font-size: 1rem; padding: 0.75rem 1.5rem;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
              <span>Save Design & Rebuild Website</span>
            </button>
          </form>
        </div>
        """,
        active_tab="design",
        page_heading="Website Design, Colors & Switchable Templates",
        current_template=current_template
    )


@app.route("/design/save", methods=["POST"])
def route_save_design():
    config = load_config()
    config["site_name"] = request.form.get("site_name", config["site_name"]).strip()
    config["tagline"] = request.form.get("tagline", config["tagline"]).strip()
    config["description"] = request.form.get("description", config["description"]).strip()
    config["site_url"] = request.form.get("site_url", config["site_url"]).strip().rstrip("/")
    config["author"] = request.form.get("author", config["author"]).strip()

    if "theme" not in config:
        config["theme"] = {}
    config["theme"]["template"] = request.form.get("template", "modern").strip()

    save_config(config)
    build_site()
    flash(f"Design settings saved! Switched to '{config['theme']['template'].title()}' template with 100% stable alignment.", "success")
    return redirect(url_for("route_design"))


@app.route("/ads")
def route_ads():
    return render_studio_view(
        ADS_HTML,
        active_tab="ads",
        page_heading="Universal Monetization & Ad Network Controls"
    )


@app.route("/ads/save", methods=["POST"])
def route_save_ads():
    config = load_config()
    if "ads" not in config:
        config["ads"] = {}

    config["ads"]["enabled"] = bool(request.form.get("ads_enabled"))
    config["ads"]["head_code"] = request.form.get("head_code", "").strip()
    config["ads"]["header_ad"] = request.form.get("header_ad", "").strip()
    config["ads"]["in_article_ad"] = request.form.get("in_article_ad", "").strip()
    config["ads"]["sidebar_ad"] = request.form.get("sidebar_ad", "").strip()
    config["ads"]["footer_ad"] = request.form.get("footer_ad", "").strip()

    if "adsense" not in config["ads"]:
        config["ads"]["adsense"] = {}
    config["ads"]["adsense"]["client_id"] = request.form.get("adsense_client_id", "").strip()
    config["ads"]["adsense"]["header_slot"] = request.form.get("adsense_header_slot", "").strip()
    config["ads"]["adsense"]["in_article_slot"] = request.form.get("adsense_in_article_slot", "").strip()
    config["ads"]["adsense"]["sidebar_slot"] = request.form.get("adsense_sidebar_slot", "").strip()

    save_config(config)
    build_site()
    flash("Ad network settings saved and site rebuilt with zero-CLS containers.", "success")
    return redirect(url_for("route_ads"))


@app.route("/seo")
def route_seo():
    config = load_config()
    seo = config.get("seo", {})
    return render_studio_view(
        SEO_HTML,
        active_tab="seo",
        page_heading="Search Engine Optimization & Google Search Setup",
        seo=seo
    )


@app.route("/seo/save", methods=["POST"])
def route_save_seo():
    config = load_config()
    if "seo" not in config:
        config["seo"] = {}

    g_ver = request.form.get("google_site_verification", "").strip()
    config["seo"]["google_site_verification"] = g_ver
    config["seo"]["bing_site_verification"] = request.form.get("bing_site_verification", "").strip()
    config["seo"]["robots_directive"] = request.form.get("robots_directive", "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1").strip()
    config["seo"]["meta_keywords"] = request.form.get("meta_keywords", "").strip()
    config["seo"]["meta_description"] = request.form.get("meta_description", "").strip()
    config["seo"]["og_image"] = request.form.get("og_image", "").strip()
    config["seo"]["twitter_handle"] = request.form.get("twitter_handle", "").strip()

    ga_id = request.form.get("google_analytics_id", "").strip()
    if "analytics" not in config:
        config["analytics"] = {}
    config["analytics"]["google_analytics_id"] = ga_id
    config["seo"]["google_analytics_id"] = ga_id

    save_config(config)
    build_site()
    flash("SEO settings and Google verification meta tags saved! Clean URLs and sitemap updated.", "success")
    return redirect(url_for("route_seo"))


@app.route("/pages")
def route_legal_pages():
    return render_studio_view(
        """
        <div class="card">
          <h3 class="card-title">Compliance & Trust Pages (Clean URLs)</h3>
          <table class="data-table">
            <thead>
              <tr><th>Page</th><th>Clean URL</th><th>Action</th></tr>
            </thead>
            <tbody>
              <tr><td><strong>About Us</strong></td><td><code>/about/</code></td><td><a href="{{ url_for('route_edit_page', slug='about') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit</a></td></tr>
              <tr><td><strong>Privacy Policy</strong></td><td><code>/privacy-policy/</code></td><td><a href="{{ url_for('route_edit_page', slug='privacy-policy') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit</a></td></tr>
              <tr><td><strong>Terms and Conditions</strong></td><td><code>/terms-and-conditions/</code></td><td><a href="{{ url_for('route_edit_page', slug='terms-and-conditions') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit</a></td></tr>
              <tr><td><strong>Contact Us</strong></td><td><code>/contact/</code></td><td><a href="{{ url_for('route_edit_page', slug='contact') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit</a></td></tr>
              <tr><td><strong>Disclaimer</strong></td><td><code>/disclaimer/</code></td><td><a href="{{ url_for('route_edit_page', slug='disclaimer') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit</a></td></tr>
            </tbody>
          </table>
        </div>
        """,
        active_tab="pages",
        page_heading="Mandatory AdSense Compliance Pages"
    )


@app.route("/pages/edit/<slug>")
def route_edit_page(slug):
    page_file = PAGES_DIR / f"{slug}.md"
    if not page_file.exists():
        flash("Page not found.", "danger")
        return redirect(url_for("route_legal_pages"))

    meta, content = parse_frontmatter(page_file)
    return render_studio_view(
        """
        <div class="card">
          <h3 class="card-title">Edit Page: {{ slug.replace('-', ' ').title() }}</h3>
          <form method="POST" action="{{ url_for('route_save_page', slug=slug) }}">
            <div class="form-group">
              <label class="form-label">Page Title</label>
              <input type="text" name="title" class="form-control" value="{{ page_meta.get('title', slug.replace('-', ' ').title()) }}" required>
            </div>
            <div class="form-group">
              <label class="form-label">Page Content (Markdown)</label>
              <textarea name="content" class="form-control" style="min-height: 450px;" required>{{ raw_content }}</textarea>
            </div>
            <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
              <button type="submit" class="btn btn-success">Save Page & Rebuild</button>
              <a href="{{ url_for('route_legal_pages') }}" class="btn btn-secondary">Cancel</a>
            </div>
          </form>
        </div>
        """,
        active_tab="pages",
        page_heading=f"Edit {slug.replace('-', ' ').title()}",
        slug=slug,
        page_meta=meta,
        raw_content=content
    )


@app.route("/pages/save/<slug>", methods=["POST"])
def route_save_page(slug):
    page_file = PAGES_DIR / f"{slug}.md"
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    today_str = datetime.now().strftime("%Y-%m-%d")

    meta = {"title": title, "slug": slug, "last_modified": today_str}
    file_content = f"---\n{yaml.dump(meta, sort_keys=False)}---\n\n{content}\n"
    with open(page_file, "w", encoding="utf-8") as f:
        f.write(file_content)

    build_site()
    flash(f"Page '{title}' updated and published with Clean URL /{slug}/.", "success")
    return redirect(url_for("route_legal_pages"))


@app.route("/rebuild", methods=["POST"])
def route_rebuild():
    count = build_site()
    flash(f"Full website rebuild complete! {count} topics compiled with Clean URLs.", "success")
    return redirect(request.referrer or url_for("route_notes"))


# Deploy to GitHub
DEPLOY_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="m12 12 4 4m0 0-4 4m4-4H4"/></svg>
    <span>Deploy Website to GitHub & Cloudflare Pages</span>
  </h3>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Pushing your site to GitHub triggers Cloudflare Pages to build and distribute your clean-URL static website globally.
  </p>

  <!-- Section 1: GitHub Authentication -->
  <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        <span>1. GitHub Authentication Setup</span>
      </h4>
      <form method="POST" action="{{ url_for('route_test_ssh') }}" style="margin: 0;">
        <button type="submit" class="btn btn-secondary" style="font-size: 0.75rem; padding: 0.35rem 0.75rem;">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
          <span>Test SSH Connection</span>
        </button>
      </form>
    </div>

    <!-- Option A: SSH Key (Recommended) -->
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <strong style="color: #f8fafc; font-size: 0.875rem;">Option A: Authorize SSH Key (Recommended & 1-Time Only)</strong>
        <a href="https://github.com/settings/ssh/new" target="_blank" rel="noopener" class="btn btn-primary" style="font-size: 0.75rem; padding: 0.3rem 0.75rem; text-decoration: none;">
          Add Key to GitHub &rarr;
        </a>
      </div>
      <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem;">
        GitHub needs your public key to authenticate pushes without passwords. Copy this key and paste it into your GitHub account:
      </p>

      <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem;">
        <input type="text" id="ssh-key-box" class="form-control" value="{{ ssh_pub_key }}" readonly style="font-family: monospace; font-size: 0.8rem; background: #0b1120; color: #38bdf8;">
        <button type="button" class="btn btn-secondary" onclick="copySSHKey()" style="white-space: nowrap; font-size: 0.8rem; padding: 0.55rem 0.9rem;" id="copy-btn">
          Copy Public Key
        </button>
      </div>

      <div style="background: rgba(0,0,0,0.25); border-radius: 4px; padding: 0.65rem 0.85rem; font-size: 0.775rem; color: #cbd5e1; line-height: 1.5;">
        <strong>Quick 3-Step Setup:</strong><br>
        1. Click <strong>"Copy Public Key"</strong> above.<br>
        2. Click <a href="https://github.com/settings/ssh/new" target="_blank" rel="noopener" style="color: #60a5fa; text-decoration: underline;">Add Key to GitHub</a>.<br>
        3. Give it a Title (e.g. <code>shrtnotes-studio</code>), paste the key into the <strong>Key</strong> box, and click <strong>Add SSH key</strong>.
      </div>
    </div>

    <!-- Option B: Personal Access Token (HTTPS) -->
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 1rem;">
      <strong style="color: #f8fafc; font-size: 0.875rem; display: block; margin-bottom: 0.35rem;">Option B: Or Use a GitHub Personal Access Token (HTTPS)</strong>
      <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.65rem;">
        If you prefer not to use SSH, generate a token at <a href="https://github.com/settings/tokens/new" target="_blank" rel="noopener" style="color: #60a5fa; text-decoration: underline;">GitHub Tokens</a> (select <code>repo</code> access) and paste it below:
      </p>
      <form method="POST" action="{{ url_for('route_setup_token') }}" style="display: flex; gap: 0.5rem;">
        <input type="password" name="token" class="form-control" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx" style="font-size: 0.85rem;" required>
        <button type="submit" class="btn btn-secondary" style="white-space: nowrap; font-size: 0.8rem; padding: 0.55rem 0.9rem;">
          Connect Token & Switch to HTTPS
        </button>
      </form>
    </div>
  </div>

  <!-- Section 2: Repository Settings -->
  <form method="POST" action="{{ url_for('route_save_repo') }}" style="margin-bottom: 1.5rem; background: #0f172a; padding: 1.25rem; border-radius: 8px; border: 1px solid var(--card-border);">
    <h4 style="font-size: 0.95rem; margin-bottom: 0.75rem; color: #93c5fd; display: flex; align-items: center; justify-content: space-between;">
      <span>2. GitHub Repository Link</span>
      {% if git_remote %}
      <span style="font-size: 0.75rem; background: #064e3b; color: #a7f3d0; padding: 2px 8px; border-radius: 4px;">Connected</span>
      {% else %}
      <span style="font-size: 0.75rem; background: #78350f; color: #fde68a; padding: 2px 8px; border-radius: 4px;">Not Linked Yet</span>
      {% endif %}
    </h4>
    <div class="form-grid">
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <label class="form-label">Repository Remote URL *</label>
        <input type="text" name="repo_url" class="form-control" value="{{ git_remote }}" placeholder="git@github.com:mybusyness-commits/shortnotes.git" required>
      </div>
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <label class="form-label">Branch *</label>
        <input type="text" name="branch" class="form-control" value="{{ branch }}" placeholder="main" required>
      </div>
    </div>
    <button type="submit" class="btn btn-primary" style="margin-top: 0.5rem; font-size: 0.85rem;">Save Repository Link</button>
  </form>

  <!-- Section 3: Status & Deploy -->
  <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
    <h4 style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.6rem; letter-spacing: 0.05em;">Current Git Status:</h4>
    <pre style="color: #93c5fd; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; overflow-x: auto; white-space: pre-wrap; margin: 0;">{{ git_status }}</pre>
  </div>

  <form method="POST" action="{{ url_for('route_execute_deploy') }}">
    <div class="form-group">
      <label class="form-label">Deployment Commit Message</label>
      <input type="text" name="commit_message" class="form-control" value="Update chapter topics ({{ today_str }})" required>
    </div>
    <button type="submit" class="btn btn-success" style="font-size: 1.05rem; padding: 0.85rem 1.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>
      <span>Deploy Now to GitHub & Cloudflare</span>
    </button>
  </form>
</div>

<script>
function copySSHKey() {
  const copyText = document.getElementById("ssh-key-box");
  copyText.select();
  copyText.setSelectionRange(0, 99999);
  navigator.clipboard.writeText(copyText.value).then(() => {
    const btn = document.getElementById("copy-btn");
    btn.textContent = "Copied to Clipboard!";
    btn.style.background = "#10b981";
    btn.style.color = "#ffffff";
    setTimeout(() => {
      btn.textContent = "Copy Public Key";
      btn.style.background = "";
      btn.style.color = "";
    }, 2500);
  });
}
</script>
"""

@app.route("/deploy")
def route_deploy():
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    git_remote = get_git_remote()
    config = load_config()
    branch = config.get("github", {}).get("branch", "main")
    ssh_pub_key = get_ssh_public_key()

    try:
        status_res = subprocess.run(["git", "status", "--short"], cwd=str(BASE_DIR), capture_output=True, text=True)
        git_status = status_res.stdout.strip() or "All files are committed and ready for deployment."
    except Exception as e:
        git_status = f"Git status check: {e}"

    return render_studio_view(
        DEPLOY_HTML,
        active_tab="deploy",
        page_heading="Deploy Website to GitHub & Cloudflare",
        git_remote=git_remote,
        branch=branch,
        git_status=git_status,
        today_str=today_str,
        ssh_pub_key=ssh_pub_key
    )


@app.route("/deploy/test_ssh", methods=["POST"])
def route_test_ssh():
    try:
        res = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-T", "git@github.com"],
            capture_output=True,
            text=True,
            timeout=8
        )
        combined = (res.stdout + " " + res.stderr).strip()
        if "successfully authenticated" in combined:
            flash(f"GitHub SSH Connected! Authentication verified: {combined}", "success")
        else:
            flash(
                "GitHub rejected the connection: 'Permission denied (publickey)'. "
                "Your key has not been added to GitHub yet. Please copy the public key shown below and add it at https://github.com/settings/ssh/new",
                "warning"
            )
    except Exception as e:
        flash(f"Error testing SSH connection: {e}", "danger")

    return redirect(url_for("route_deploy"))


@app.route("/deploy/setup_token", methods=["POST"])
def route_setup_token():
    token = request.form.get("token", "").strip()
    if not token:
        flash("Token cannot be empty.", "danger")
        return redirect(url_for("route_deploy"))

    remote = get_git_remote()
    repo_path = "mybusyness-commits/shortnotes.git"
    if "github.com:" in remote:
        repo_path = remote.split("github.com:")[-1]
    elif "github.com/" in remote:
        repo_path = remote.split("github.com/")[-1]

    repo_path = repo_path.lstrip("/").replace(".git", "") + ".git"
    new_remote = f"https://{token}@github.com/{repo_path}"

    try:
        subprocess.run(["git", "remote", "set-url", "origin", new_remote], cwd=str(BASE_DIR), check=True)
        config = load_config()
        if "github" not in config:
            config["github"] = {}
        config["github"]["repo_url"] = new_remote
        save_config(config)
        flash("Personal Access Token saved! Switched remote to authenticated HTTPS.", "success")
    except Exception as e:
        flash(f"Error configuring token remote: {e}", "danger")

    return redirect(url_for("route_deploy"))


@app.route("/deploy/save_repo", methods=["POST"])
def route_save_repo():
    repo_url = request.form.get("repo_url", "").strip()
    branch = request.form.get("branch", "main").strip()

    if not repo_url:
        flash("Repository URL cannot be empty.", "danger")
        return redirect(url_for("route_deploy"))

    try:
        check = subprocess.run(["git", "remote"], cwd=str(BASE_DIR), capture_output=True, text=True)
        remotes = check.stdout.split()
        if "origin" in remotes:
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=str(BASE_DIR), check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=str(BASE_DIR), check=True)

        config = load_config()
        if "github" not in config:
            config["github"] = {}
        config["github"]["repo_url"] = repo_url
        config["github"]["branch"] = branch
        save_config(config)

        flash(f"GitHub repository link saved successfully: {repo_url}", "success")
    except Exception as e:
        flash(f"Error saving repository link: {e}", "danger")

    return redirect(url_for("route_deploy"))


@app.route("/deploy/execute", methods=["POST"])
def route_execute_deploy():
    commit_msg = request.form.get("commit_message", "Update study notes").strip()
    config = load_config()
    branch = config.get("github", {}).get("branch", "main")

    git_remote = get_git_remote()
    if not git_remote:
        flash("Please save your GitHub Repository Link first before deploying.", "danger")
        return redirect(url_for("route_deploy"))

    try:
        build_site()
        subprocess.run(["git", "add", "."], cwd=str(BASE_DIR), check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(BASE_DIR), capture_output=True, text=True)
        push_res = subprocess.run(["git", "push", "origin", branch], cwd=str(BASE_DIR), capture_output=True, text=True)

        if push_res.returncode == 0:
            flash("Deployment triggered successfully! Pushed to GitHub. Cloudflare Pages is now updating your live site.", "success")
        else:
            err = (push_res.stderr or push_res.stdout or "").strip()
            if "Permission denied (publickey)" in err:
                flash(
                    "GitHub rejected the connection: Permission denied (publickey). "
                    "Your SSH key has not been added to your GitHub account yet. "
                    "Please copy the SSH public key displayed under Step 1, add it at https://github.com/settings/ssh/new, and then click Deploy again!",
                    "danger"
                )
            elif "Authentication failed" in err or "fatal: could not read Username" in err:
                flash(f"GitHub authentication failed: {err}. Please verify your Personal Access Token or repository permissions.", "danger")
            else:
                flash(f"Git push notice: {err}", "danger")
    except Exception as e:
        flash(f"Deployment error: {e}", "danger")

    return redirect(url_for("route_deploy"))


# ==============================================================================
# Live Static Preview Server & Fallback Catch-All (Clean URLs & Zero 404s)
# ==============================================================================
@app.route("/preview/")
@app.route("/preview/<path:filename>")
def route_preview(filename=""):
    if not OUTPUT_DIR.exists():
        build_site()

    if not filename or filename.endswith("/"):
        filename = f"{filename}index.html"

    target = OUTPUT_DIR / filename
    if target.is_dir():
        filename = f"{filename.rstrip('/')}/index.html"

    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/<path:req_path>")
def route_fallback_preview(req_path):
    """
    Fallback server for Clean URLs on LAN:
    Automatically serves the index.html of any clean URL path (e.g. /about/ or /mathematics/calculus/).
    """
    reserved = ("notes", "design", "ads", "seo", "subjects", "pages", "deploy", "preview", "rebuild")
    parts = req_path.split("/")
    if parts[0] in reserved and not (parts[0] == "pages" and len(parts) > 1):
        return "Not found", 404

    target = OUTPUT_DIR / req_path
    if target.is_dir():
        target = target / "index.html"
        req_path = f"{req_path.rstrip('/')}/index.html"

    if target.exists() and target.is_file():
        return send_from_directory(str(OUTPUT_DIR), req_path)

    return "Page not found (404)", 404


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  🚀 shrtnotes Studio is running!")
    print(f"  👉 Local Browser:   http://localhost:5050")
    print(f"  👉 Mobile / LAN:     http://{get_local_ip()}:5050/preview/")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
