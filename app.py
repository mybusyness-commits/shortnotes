#!/usr/bin/env python3
"""
shrtnotes Studio - Local Website Management Application
======================================================
Visual dashboard to write, edit, and organize study notes,
customize site tree hierarchy & icons, manage Google AdSense slots,
test over LAN without 404s, and deploy to GitHub & Cloudflare Pages with 1 click.
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
    """List all notes with metadata for editing."""
    notes = []
    if NOTES_DIR.exists():
        for f in NOTES_DIR.glob("**/*.md"):
            meta, md = parse_frontmatter(f)
            if not meta.get("title"):
                continue
            notes.append({
                "file_path": str(f.relative_to(NOTES_DIR)),
                "title": meta.get("title", f.stem),
                "slug": meta.get("slug", f.stem),
                "subject": meta.get("subject", ""),
                "chapter": meta.get("chapter", "General"),
                "date": meta.get("date", ""),
                "last_modified": meta.get("last_modified", ""),
                "excerpt": meta.get("excerpt", "")
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


# ==============================================================================
# Base Studio Layout (Clean, Zero Emojis)
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
    
    /* Sidebar */
    .studio-sidebar { width: 260px; background: var(--sidebar-bg); border-right: 1px solid var(--card-border); display: flex; flex-direction: column; }
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
    
    /* Main Content */
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
    
    /* Forms */
    .form-group { margin-bottom: 1.25rem; }
    .form-label { display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.4rem; color: var(--text-muted); }
    .form-control { width: 100%; padding: 0.65rem 0.85rem; background: #0f172a; border: 1px solid var(--card-border); border-radius: 6px; color: #fff; font-size: 0.925rem; outline: none; font-family: inherit; }
    .form-control:focus { border-color: var(--accent); }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
    textarea.form-control { resize: vertical; min-height: 380px; font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; line-height: 1.5; }
    
    /* Flash messages */
    .flash-alert { padding: 0.85rem 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; }
    .flash-success { background: #064e3b; border: 1px solid #059669; color: #a7f3d0; }
    .flash-danger { background: #7f1d1d; border: 1px solid #dc2626; color: #fecaca; }
    
    /* Table */
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .data-table th, .data-table td { padding: 0.85rem 1rem; border-bottom: 1px solid var(--card-border); text-align: left; }
    .data-table th { color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .data-table tr:hover { background: #1e293b; }
    
    .subject-icon-preview svg { width: 22px; height: 22px; stroke: var(--accent); }
    
    /* Ad Box info */
    .ad-preview-box { border: 1px dashed #3b82f6; background: rgba(59, 130, 246, 0.05); padding: 1.25rem; border-radius: 8px; margin-top: 1rem; }
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
          <span>All Notes ({{ notes_count }})</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_new_note') }}" class="nav-btn {% if active_tab == 'new_note' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
          <span>Write New Note</span>
        </a>
      </li>
      <li>
        <a href="{{ url_for('route_subjects') }}" class="nav-btn {% if active_tab == 'subjects' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>
          <span>Subjects & Tree</span>
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
          <span>Google AdSense</span>
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

    <!-- LAN Mobile Testing Info Pill -->
    <div class="lan-pill">
      <strong>LAN Mobile Testing:</strong>
      <p style="margin-bottom: 0.35rem; color: #cbd5e1;">Test on your phone via Wi-Fi:</p>
      <a href="http://{{ lan_ip }}:5050/preview/index.html" target="_blank">http://{{ lan_ip }}:5050/preview/index.html</a>
    </div>
  </aside>

  <!-- Main View Area -->
  <main class="studio-main">
    <header class="studio-topbar">
      <div>
        <h2 style="font-size: 1.15rem; font-weight: 600;">{{ page_heading }}</h2>
      </div>
      <div class="topbar-actions">
        <a href="/preview/index.html" target="_blank" class="btn btn-secondary" title="Preview your live site in browser">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
          <span>View Site Preview</span>
        </a>
        <form method="POST" action="{{ url_for('route_rebuild') }}" style="display: inline;">
          <button type="submit" class="btn btn-primary" title="Recompiles all HTML, XML sitemaps, and robots.txt">
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

      <!-- Dynamic Tab Content -->
      <!-- CONTENT_PLACEHOLDER -->
    </div>
  </main>

</body>
</html>
"""

# ==============================================================================
# Route: List All Notes
# ==============================================================================
NOTES_LIST_HTML = """
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
    <h3 class="card-title" style="margin-bottom: 0;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <span>Published Study Notes</span>
    </h3>
    <a href="{{ url_for('route_new_note') }}" class="btn btn-primary">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
      <span>Create Note</span>
    </a>
  </div>

  <table class="data-table">
    <thead>
      <tr>
        <th>Subject</th>
        <th>Chapter</th>
        <th>Title</th>
        <th>Last Updated</th>
        <th style="text-align: right;">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for note in notes %}
      <tr>
        <td><span style="background: #1e3a8a; color: #93c5fd; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">{{ note.subject }}</span></td>
        <td>{{ note.chapter }}</td>
        <td><strong>{{ note.title }}</strong></td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">{{ note.last_modified }}</td>
        <td style="text-align: right;">
          <a href="{{ url_for('route_edit_note', rel_path=note.file_path) }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">
            Edit Note
          </a>
          <form method="POST" action="{{ url_for('route_delete_note') }}" style="display: inline;" onsubmit="return confirm('Are you sure you want to delete this note?');">
            <input type="hidden" name="rel_path" value="{{ note.file_path }}">
            <button type="submit" class="btn btn-danger" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
      {% if not notes %}
      <tr>
        <td colspan="5" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
          No notes created yet. Click "Create Note" to write your first high-yield note!
        </td>
      </tr>
      {% endif %}
    </tbody>
  </table>
</div>
"""

# ==============================================================================
# Route: Note Editor (New / Edit)
# ==============================================================================
NOTE_FORM_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span>{% if is_edit %}Edit Note{% else %}Write New Study Note{% endif %}</span>
  </h3>

  <form method="POST" action="{{ action_url }}">
    {% if is_edit %}
    <input type="hidden" name="original_path" value="{{ original_path }}">
    {% endif %}

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Note Title *</label>
        <input type="text" name="title" class="form-control" value="{{ note_meta.get('title', '') }}" placeholder="e.g. Fundamental Theorem of Calculus" required>
      </div>
      <div class="form-group">
        <label class="form-label">URL Slug (lowercase-hyphens) *</label>
        <input type="text" name="slug" class="form-control" value="{{ note_meta.get('slug', '') }}" placeholder="e.g. calculus-fundamental-theorem" required>
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Subject *</label>
        <select name="subject" class="form-control" required>
          {% for sub in config.subjects %}
          <option value="{{ sub.id }}" {% if note_meta.get('subject') == sub.id %}selected{% endif %}>{{ sub.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Chapter / Topic Category *</label>
        <input type="text" name="chapter" class="form-control" value="{{ note_meta.get('chapter', 'General') }}" placeholder="e.g. Differential Calculus" required>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Short Summary / Excerpt (used for Google Search Snippet & Social Cards)</label>
      <input type="text" name="excerpt" class="form-control" value="{{ note_meta.get('excerpt', '') }}" placeholder="A 1-2 sentence high-yield summary...">
    </div>

    <div class="form-group">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
        <label class="form-label" style="margin-bottom: 0;">Note Content (Markdown & KaTeX Formulas Supported) *</label>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Use $formula$ for inline math, or $$formula$$ for centered block math</span>
      </div>
      <textarea name="content" class="form-control" placeholder="Write your notes here using Markdown headers (##), bullet points, and math formulas ($E = mc^2$)..." required>{{ raw_content }}</textarea>
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
        <span>Save Note & Rebuild Site</span>
      </button>
      <a href="{{ url_for('route_notes') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
"""

# ==============================================================================
# Route: Design & Template Customizer
# ==============================================================================
DESIGN_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19 7-7 3 3-7 7-3-3z"/><path d="m18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/></svg>
    <span>Universal Website Design & Branding</span>
  </h3>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Changes made here instantly update <strong>all pages across the entire site</strong>. The layout is rigorously tested to prevent shifts and maintain clean readability on both desktop and mobile.
  </p>

  <form method="POST" action="{{ url_for('route_save_design') }}">
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
      <label class="form-label">Site Meta Description (SEO for Google Search Console)</label>
      <input type="text" name="description" class="form-control" value="{{ config.description }}" required>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Live Site URL (Cloudflare Pages or Custom Domain)</label>
        <input type="url" name="site_url" class="form-control" value="{{ config.site_url }}" required>
      </div>
      <div class="form-group">
        <label class="form-label">Author / Editorial Attribution</label>
        <input type="text" name="author" class="form-control" value="{{ config.author }}" required>
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Primary Brand Color</label>
        <div style="display: flex; gap: 0.75rem; align-items: center;">
          <input type="color" name="primary_color" value="{{ config.theme.primary_color }}" style="width: 50px; height: 38px; border: none; background: none; cursor: pointer;">
          <input type="text" class="form-control" value="{{ config.theme.primary_color }}" readonly>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Accent Color</label>
        <div style="display: flex; gap: 0.75rem; align-items: center;">
          <input type="color" name="accent_color" value="{{ config.theme.accent_color }}" style="width: 50px; height: 38px; border: none; background: none; cursor: pointer;">
          <input type="text" class="form-control" value="{{ config.theme.accent_color }}" readonly>
        </div>
      </div>
    </div>

    <button type="submit" class="btn btn-success" style="margin-top: 1rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
      <span>Save Design & Apply to All Pages</span>
    </button>
  </form>
</div>
"""

# ==============================================================================
# Route: Google AdSense Management
# ==============================================================================
ADS_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>
    <span>Google AdSense Monetization & Comfort Safeguards</span>
  </h3>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Our layout is pre-engineered for Google AdSense compliance: zero layout shifts (CLS), isolated ad boxes that never cover text, and clear 'ADVERTISEMENT' disclosures.
  </p>

  <form method="POST" action="{{ url_for('route_save_ads') }}">
    <div class="form-group" style="margin-bottom: 1.5rem;">
      <label style="display: flex; align-items: center; gap: 0.75rem; font-size: 1rem; cursor: pointer;">
        <input type="checkbox" name="ads_enabled" value="true" {% if config.ads.enabled %}checked{% endif %} style="width: 20px; height: 20px;">
        <span><strong>Enable Google AdSense Units Across Site</strong></span>
      </label>
    </div>

    <div class="form-group">
      <label class="form-label">AdSense Publisher ID (Client ID)</label>
      <input type="text" name="adsense_client_id" class="form-control" value="{{ config.ads.adsense_client_id }}" placeholder="ca-pub-1234567890123456">
      <span style="font-size: 0.75rem; color: var(--text-muted);">Leave as ca-pub-XXXXXXXXXXXXXXXX until you receive AdSense account approval.</span>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Header Banner Ad Slot ID</label>
        <input type="text" name="header_ad_slot" class="form-control" value="{{ config.ads.header_ad_slot }}" placeholder="e.g. 1234567890">
      </div>
      <div class="form-group">
        <label class="form-label">In-Article Ad Slot ID (Middle of Content)</label>
        <input type="text" name="in_article_ad_slot" class="form-control" value="{{ config.ads.in_article_ad_slot }}" placeholder="e.g. 2345678901">
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Desktop Sticky Sidebar Ad Slot ID</label>
        <input type="text" name="sidebar_ad_slot" class="form-control" value="{{ config.ads.sidebar_ad_slot }}" placeholder="e.g. 3456789012">
      </div>
      <div class="form-group">
        <label class="form-label">Footer Ad Slot ID (Above Legal Links)</label>
        <input type="text" name="footer_ad_slot" class="form-control" value="{{ config.ads.footer_ad_slot }}" placeholder="e.g. 4567890123">
      </div>
    </div>

    <div class="ad-preview-box">
      <strong style="color: #60a5fa; font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">AdSense Policy Assurance:</strong>
      <p style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">
        • Fixed height buffers prevent Cumulative Layout Shift (CLS) so pages do not jump when ads load.<br>
        • Ads are cleanly separated from formulas and text blocks, fully conforming to Google's Better Ads Standards.
      </p>
    </div>

    <button type="submit" class="btn btn-success" style="margin-top: 1.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
      <span>Save Ad Settings & Rebuild</span>
    </button>
  </form>
</div>
"""

# ==============================================================================
# Route: Subject Hierarchy & Custom Icon Manager
# ==============================================================================
SUBJECTS_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>
    <span>Subject Hierarchy & Custom Icon Manager</span>
  </h3>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    Manage your site tree. You can edit existing subjects (name, description, icon), choose from preset icons, or paste your own custom SVG code.
  </p>

  <table class="data-table" style="margin-bottom: 2rem;">
    <thead>
      <tr>
        <th style="width: 50px;">Icon</th>
        <th>Subject ID</th>
        <th>Display Name</th>
        <th>Description</th>
        <th style="text-align: right;">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for sub in config.subjects %}
      <tr>
        <td>
          <div style="width: 32px; height: 32px; border-radius: 6px; background: #1e293b; display: flex; align-items: center; justify-content: center; color: var(--accent);">
            {{ get_icon(sub.icon)|safe }}
          </div>
        </td>
        <td><code>{{ sub.id }}</code></td>
        <td><strong>{{ sub.name }}</strong></td>
        <td style="color: var(--text-muted); font-size: 0.85rem;">{{ sub.description }}</td>
        <td style="text-align: right; white-space: nowrap;">
          <a href="{{ url_for('route_edit_subject', sub_id=sub.id) }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">
            Edit
          </a>
          <form method="POST" action="{{ url_for('route_delete_subject', sub_id=sub.id) }}" style="display: inline;" onsubmit="return confirm('Are you sure you want to delete subject {{ sub.name }}?');">
            <button type="submit" class="btn btn-danger" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <h4 style="font-size: 1.05rem; margin-bottom: 1rem; color: #93c5fd;">Add New Subject</h4>
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
          <option value="calculator">Calculator (Maths / Finance)</option>
          <option value="atom">Atom (Physics / Science)</option>
          <option value="flask-conical">Flask (Chemistry / Lab)</option>
          <option value="dna">DNA (Biology / Medicine)</option>
          <option value="book" selected>Book (General / Humanities)</option>
          <option value="code">Code (Programming)</option>
          <option value="cpu">CPU (Computer Science)</option>
          <option value="globe">Globe (Geography / Languages)</option>
          <option value="compass">Compass (Engineering)</option>
          <option value="heart">Heart (Health / Anatomy)</option>
          <option value="scale">Scale (Law / Ethics)</option>
          <option value="brain">Brain (Psychology / Neuroscience)</option>
          <option value="sparkles">Sparkles (Highlights)</option>
          <option value="terminal">Terminal (Command Line)</option>
          <option value="database">Database (Data Systems)</option>
          <option value="palette">Palette (Arts / Design)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">OR Paste Custom SVG Code (Optional)</label>
        <input type="text" name="sub_icon_custom" class="form-control" placeholder="Paste &lt;svg ...&gt;...&lt;/svg&gt; code here to use your own icon">
      </div>
    </div>

    <button type="submit" class="btn btn-primary" style="margin-top: 0.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
      <span>Add Subject & Rebuild Tree</span>
    </button>
  </form>
</div>
"""

SUBJECT_EDIT_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span>Edit Subject: {{ target_sub.name }} ({{ target_sub.id }})</span>
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
      <textarea name="sub_icon_custom" class="form-control" style="min-height: 120px;" placeholder="Paste &lt;svg ...&gt;...&lt;/svg&gt; markup here">{% if target_sub.icon.startswith('<svg') %}{{ target_sub.icon }}{% endif %}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Paste standard SVG markup with viewBox="0 0 24 24" from Lucide, Feather, or Heroicons.</span>
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
        <span>Save Changes & Rebuild Site</span>
      </button>
      <a href="{{ url_for('route_subjects') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
"""

# ==============================================================================
# Route: Legal Compliance Pages Editor
# ==============================================================================
LEGAL_PAGES_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
    <span>Google AdSense & Search Console Mandatory Legal Pages</span>
  </h3>
  <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1.5rem;">
    These pages are strictly evaluated by the Google AdSense approval team. Click any page below to customize its text directly.
  </p>

  <table class="data-table">
    <thead>
      <tr>
        <th>Page</th>
        <th>File</th>
        <th>Purpose</th>
        <th style="text-align: right;">Action</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>About Us</strong></td>
        <td><code>content/pages/about.md</code></td>
        <td>Explains editorial standards, who writes the notes, and academic purpose.</td>
        <td style="text-align: right;"><a href="{{ url_for('route_edit_page', slug='about') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit Text</a></td>
      </tr>
      <tr>
        <td><strong>Privacy Policy</strong></td>
        <td><code>content/pages/privacy-policy.md</code></td>
        <td>Mandatory AdSense DART cookies, GDPR, CCPA disclosures.</td>
        <td style="text-align: right;"><a href="{{ url_for('route_edit_page', slug='privacy-policy') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit Text</a></td>
      </tr>
      <tr>
        <td><strong>Terms and Conditions</strong></td>
        <td><code>content/pages/terms-and-conditions.md</code></td>
        <td>Defines educational use rights and limitations.</td>
        <td style="text-align: right;"><a href="{{ url_for('route_edit_page', slug='terms-and-conditions') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit Text</a></td>
      </tr>
      <tr>
        <td><strong>Contact Us</strong></td>
        <td><code>content/pages/contact.md</code></td>
        <td>Genuine editorial contact details for reader corrections.</td>
        <td style="text-align: right;"><a href="{{ url_for('route_edit_page', slug='contact') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit Text</a></td>
      </tr>
      <tr>
        <td><strong>Disclaimer</strong></td>
        <td><code>content/pages/disclaimer.md</code></td>
        <td>Educational study disclaimer protecting against liability.</td>
        <td style="text-align: right;"><a href="{{ url_for('route_edit_page', slug='disclaimer') }}" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Edit Text</a></td>
      </tr>
    </tbody>
  </table>
</div>
"""

PAGE_EDITOR_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <span>Edit Page: {{ slug.replace('-', ' ').title() }}</span>
  </h3>

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
      <button type="submit" class="btn btn-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
        <span>Save Page & Rebuild</span>
      </button>
      <a href="{{ url_for('route_legal_pages') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
"""

# ==============================================================================
# Route: 1-Click Deploy to GitHub & Cloudflare Pages
# ==============================================================================
DEPLOY_HTML = """
<div class="card">
  <h3 class="card-title">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m16 12-4-4-4 4"/><path d="M12 16V8"/></svg>
    <span>GitHub Repository & Cloudflare Deploy Setup</span>
  </h3>

  <!-- Repository Link Form -->
  <form method="POST" action="{{ url_for('route_save_repo') }}" style="margin-bottom: 2rem; background: #0f172a; padding: 1.25rem; border-radius: 8px; border: 1px solid var(--card-border);">
    <h4 style="font-size: 0.95rem; margin-bottom: 0.75rem; color: #93c5fd; display: flex; align-items: center; justify-content: space-between;">
      <span>GitHub Repository Link</span>
      {% if git_remote %}
      <span style="font-size: 0.75rem; background: #064e3b; color: #a7f3d0; padding: 2px 8px; border-radius: 4px;">Connected</span>
      {% else %}
      <span style="font-size: 0.75rem; background: #78350f; color: #fde68a; padding: 2px 8px; border-radius: 4px;">Not Linked Yet</span>
      {% endif %}
    </h4>

    <div class="form-grid">
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <label class="form-label">Repository URL (HTTPS or SSH) *</label>
        <input type="text" name="repo_url" class="form-control" value="{{ git_remote }}" placeholder="https://github.com/username/shrtnotes.git" required>
      </div>
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <label class="form-label">Branch *</label>
        <input type="text" name="branch" class="form-control" value="{{ branch }}" placeholder="main" required>
      </div>
    </div>
    <button type="submit" class="btn btn-primary" style="margin-top: 0.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
      <span>Save Repository Link</span>
    </button>
  </form>

  <div style="background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
    <h4 style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.6rem; letter-spacing: 0.05em;">Current Git Status:</h4>
    <pre style="color: #93c5fd; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; overflow-x: auto; white-space: pre-wrap;">{{ git_status }}</pre>
  </div>

  <form method="POST" action="{{ url_for('route_execute_deploy') }}">
    <div class="form-group">
      <label class="form-label">Deployment Commit Message</label>
      <input type="text" name="commit_message" class="form-control" value="Update study notes ({{ today_str }})" required>
    </div>

    <button type="submit" class="btn btn-success" style="font-size: 1rem; padding: 0.75rem 1.5rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/></svg>
      <span>Deploy Now to GitHub</span>
    </button>
  </form>
</div>
"""


# ==============================================================================
# Helper for Rendering Views with Base Template
# ==============================================================================
def render_studio_view(child_content, active_tab, page_heading, **kwargs):
    config = load_config()
    notes = get_all_notes_list()
    lan_ip = get_local_ip()

    cleaned = child_content.replace('{% extends "studio_base" %}', '').replace('{% block studio_content %}', '').replace('{% endblock %}', '')
    full_template = STUDIO_HTML.replace('<!-- CONTENT_PLACEHOLDER -->', cleaned)

    return render_template_string(
        full_template,
        active_tab=active_tab,
        page_heading=page_heading,
        config=config,
        notes_count=len(notes),
        lan_ip=lan_ip,
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
        page_heading="All Published Study Notes",
        notes=notes
    )


@app.route("/notes/new")
def route_new_note():
    return render_studio_view(
        NOTE_FORM_HTML,
        active_tab="new_note",
        page_heading="Write New Study Note",
        is_edit=False,
        note_meta={},
        raw_content="",
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
        flash("Note file does not exist.", "danger")
        return redirect(url_for("route_notes"))

    meta, raw_content = parse_frontmatter(target_file)
    meta["slug"] = meta.get("slug") or target_file.stem

    return render_studio_view(
        NOTE_FORM_HTML,
        active_tab="notes",
        page_heading=f"Edit Note: {meta.get('title', '')}",
        is_edit=True,
        original_path=rel_path,
        note_meta=meta,
        raw_content=raw_content,
        action_url=url_for("route_save_note")
    )


@app.route("/notes/save", methods=["POST"])
def route_save_note():
    is_edit = bool(request.form.get("original_path"))
    original_path = request.form.get("original_path")
    title = request.form.get("title", "").strip()
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    subject = request.form.get("subject", "").strip().lower()
    chapter = request.form.get("chapter", "").strip()
    excerpt = request.form.get("excerpt", "").strip()
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
            if str(old_file) != str(NOTES_DIR / subject / f"{slug}.md"):
                old_file.unlink()

    frontmatter = {
        "title": title,
        "slug": slug,
        "subject": subject,
        "chapter": chapter,
        "excerpt": excerpt,
        "date": date_val,
        "last_modified": today_str
    }

    target_dir = NOTES_DIR / subject
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{slug}.md"

    file_content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{content}\n"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(file_content)

    count = build_site()
    flash(f"Note '{title}' saved successfully! Rebuilt {count} notes and updated sitemap.xml.", "success")
    return redirect(url_for("route_notes"))


@app.route("/notes/delete", methods=["POST"])
def route_delete_note():
    rel_path = request.form.get("rel_path")
    if rel_path:
        target_file = NOTES_DIR / rel_path
        if target_file.exists():
            target_file.unlink()
            build_site()
            flash("Note deleted and site rebuild complete.", "success")
    return redirect(url_for("route_notes"))


@app.route("/design")
def route_design():
    return render_studio_view(
        DESIGN_HTML,
        active_tab="design",
        page_heading="Website Design, Colors & Branding"
    )


@app.route("/design/save", methods=["POST"])
def route_save_design():
    config = load_config()
    config["site_name"] = request.form.get("site_name", config["site_name"]).strip()
    config["tagline"] = request.form.get("tagline", config["tagline"]).strip()
    config["description"] = request.form.get("description", config["description"]).strip()
    config["site_url"] = request.form.get("site_url", config["site_url"]).strip().rstrip("/")
    config["author"] = request.form.get("author", config["author"]).strip()

    config["theme"]["primary_color"] = request.form.get("primary_color", config["theme"]["primary_color"])
    config["theme"]["accent_color"] = request.form.get("accent_color", config["theme"]["accent_color"])

    save_config(config)
    build_site()
    flash("Design settings saved! All website pages re-rendered with new branding.", "success")
    return redirect(url_for("route_design"))


@app.route("/ads")
def route_ads():
    return render_studio_view(
        ADS_HTML,
        active_tab="ads",
        page_heading="Google AdSense & Comfort Safeguards"
    )


@app.route("/ads/save", methods=["POST"])
def route_save_ads():
    config = load_config()
    config["ads"]["enabled"] = bool(request.form.get("ads_enabled"))
    config["ads"]["adsense_client_id"] = request.form.get("adsense_client_id", "").strip()
    config["ads"]["header_ad_slot"] = request.form.get("header_ad_slot", "").strip()
    config["ads"]["in_article_ad_slot"] = request.form.get("in_article_ad_slot", "").strip()
    config["ads"]["sidebar_ad_slot"] = request.form.get("sidebar_ad_slot", "").strip()
    config["ads"]["footer_ad_slot"] = request.form.get("footer_ad_slot", "").strip()

    save_config(config)
    build_site()
    flash("AdSense settings updated and site rebuilt successfully.", "success")
    return redirect(url_for("route_ads"))


# ==============================================================================
# Subject Management (Add, Edit, Delete, Custom SVG Icons)
# ==============================================================================
@app.route("/subjects")
def route_subjects():
    return render_studio_view(
        SUBJECTS_HTML,
        active_tab="subjects",
        page_heading="Subject Directory & Site Tree"
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
            flash(f"Subject with ID '{sub_id}' already exists.", "danger")
            return redirect(url_for("route_subjects"))

    config["subjects"].append({
        "id": sub_id,
        "name": sub_name,
        "description": sub_desc,
        "icon": icon_val
    })

    save_config(config)
    build_site()
    flash(f"Subject '{sub_name}' added! New subject page, navigation link, and sitemap entries created.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/edit/<sub_id>")
def route_edit_subject(sub_id):
    config = load_config()
    target = None
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            target = s
            break

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

    found = False
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            s["name"] = sub_name
            s["description"] = sub_desc
            s["icon"] = icon_val
            found = True
            break

    if not found:
        flash("Subject not found.", "danger")
        return redirect(url_for("route_subjects"))

    save_config(config)
    build_site()
    flash(f"Subject '{sub_name}' updated successfully! All pages recompiled.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/delete/<sub_id>", methods=["POST"])
def route_delete_subject(sub_id):
    config = load_config()
    initial_count = len(config.get("subjects", []))
    config["subjects"] = [s for s in config.get("subjects", []) if s["id"] != sub_id]

    if len(config["subjects"]) < initial_count:
        save_config(config)
        build_site()
        flash(f"Subject '{sub_id}' deleted and site tree rebuilt.", "success")
    else:
        flash("Subject not found.", "danger")

    return redirect(url_for("route_subjects"))


# ==============================================================================
# Legal Compliance Pages
# ==============================================================================
@app.route("/pages")
def route_legal_pages():
    return render_studio_view(
        LEGAL_PAGES_HTML,
        active_tab="pages",
        page_heading="AdSense Mandatory Legal Pages"
    )


@app.route("/pages/edit/<slug>")
def route_edit_page(slug):
    page_file = PAGES_DIR / f"{slug}.md"
    if not page_file.exists():
        flash("Page not found.", "danger")
        return redirect(url_for("route_legal_pages"))

    meta, content = parse_frontmatter(page_file)
    return render_studio_view(
        PAGE_EDITOR_HTML,
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

    meta = {
        "title": title,
        "slug": slug,
        "last_modified": today_str
    }
    file_content = f"---\n{yaml.dump(meta, sort_keys=False)}---\n\n{content}\n"
    with open(page_file, "w", encoding="utf-8") as f:
        f.write(file_content)

    build_site()
    flash(f"Page '{title}' updated and published successfully.", "success")
    return redirect(url_for("route_legal_pages"))


@app.route("/rebuild", methods=["POST"])
def route_rebuild():
    count = build_site()
    flash(f"Full website rebuild complete! {count} study notes compiled with updated sitemaps.", "success")
    return redirect(request.referrer or url_for("route_notes"))


# ==============================================================================
# Deploy & Git Remote Linking
# ==============================================================================
@app.route("/deploy")
def route_deploy():
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    git_remote = get_git_remote()
    config = load_config()
    branch = config.get("github", {}).get("branch", "main")

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
        today_str=today_str
    )


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
        # 1. Rebuild site
        build_site()

        # 2. git add
        subprocess.run(["git", "add", "."], cwd=str(BASE_DIR), check=True)

        # 3. git commit (ignore error if no changes)
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True
        )

        # 4. git push
        push_res = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True
        )

        if push_res.returncode == 0:
            flash("Deployment triggered successfully! Changes pushed to GitHub. Cloudflare Pages is now deploying your site.", "success")
        else:
            err_msg = push_res.stderr or push_res.stdout or "Push error"
            flash(f"Git push result: {err_msg}. If pushing for the first time, check your GitHub token/credentials.", "danger")

    except Exception as e:
        flash(f"Deployment error: {e}", "danger")

    return redirect(url_for("route_deploy"))


# ==============================================================================
# Live Static Preview Server & Fallback Catch-All (Zero 404s on LAN)
# ==============================================================================
@app.route("/preview/")
@app.route("/preview/<path:filename>")
def route_preview(filename="index.html"):
    if not OUTPUT_DIR.exists():
        build_site()
    
    target = OUTPUT_DIR / filename
    if target.is_dir():
        filename = f"{filename.rstrip('/')}/index.html"

    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/<path:req_path>")
def route_fallback_preview(req_path):
    """
    Fallback server for direct paths on LAN:
    If a request is made outside /preview/ (e.g. /pages/about.html or /physics/thermodynamics-carnot-engine.html),
    it is automatically served from OUTPUT_DIR so users never hit a 404!
    """
    # Exclude internal studio route prefixes
    reserved = ("notes", "design", "ads", "subjects", "pages", "deploy", "preview", "rebuild")
    parts = req_path.split("/")
    if parts[0] in reserved and not (parts[0] == "pages" and len(parts) > 1 and parts[1].endswith(".html")):
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
    print(f"  👉 Mobile / LAN:     http://{get_local_ip()}:5050/preview/index.html")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
