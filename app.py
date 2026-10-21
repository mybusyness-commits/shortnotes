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
import re
import time
import requests
import yaml
import urllib3.util.connection as urllib_conn
try:
    urllib_conn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass
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

            rel_parts = f.relative_to(NOTES_DIR).parts
            sub_id = str(meta.get("subject", "")).lower().strip()
            if not sub_id and len(rel_parts) >= 2:
                sub_id = rel_parts[0].lower().strip()

            sub_info = subjects_map.get(sub_id, {})
            sub_name = sub_info.get("name", sub_id.capitalize())

            # Detect branch
            branch_id = str(meta.get("branch", "")).lower().strip()
            if not branch_id and len(rel_parts) >= 4:
                branch_id = rel_parts[1].lower().strip()

            # Chapter handling
            chapter_id = str(meta.get("chapter", "")).lower().strip().replace(" ", "-")
            if not chapter_id:
                if len(rel_parts) >= 4:
                    chapter_id = rel_parts[2].lower().strip().replace(" ", "-")
                elif len(rel_parts) >= 3:
                    chapter_id = rel_parts[1].lower().strip().replace(" ", "-")
                else:
                    chapter_id = "general"

            branch_name = ""
            ch_name = chapter_id.replace("-", " ").title()

            if branch_id and sub_info.get("branches"):
                for b in sub_info.get("branches", []):
                    if b["id"] == branch_id or b.get("name", "").lower() == branch_id.lower():
                        branch_id = b["id"]
                        branch_name = b["name"]
                        for ch in b.get("chapters", []):
                            if ch["id"] == chapter_id or ch.get("name", "").lower() == chapter_id.lower():
                                ch_name = ch["name"]
                                break
                        break
            else:
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
                "branch": branch_id,
                "branch_name": branch_name,
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
# AI Model Connector (Gemini, Groq, OpenAI, Ollama)
# ==============================================================================
def call_ai_model(prompt, system_instruction=None, json_mode=False, provider=None, api_key=None, model=None, custom_endpoint=None):
    """
    Unified AI model caller supporting Google Gemini, Groq, OpenAI, Ollama, and custom endpoints.
    Returns (success: bool, result_or_error: str).
    """
    config = load_config()
    ai_cfg = config.get("ai", {})
    provider = (provider or ai_cfg.get("provider", "gemini")).lower()
    api_key = (api_key or ai_cfg.get("api_key", "")).strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    model = (model or ai_cfg.get("model", "")).strip()
    custom_endpoint = (custom_endpoint or ai_cfg.get("custom_endpoint", "")).strip()

    if not api_key and provider != "ollama":
        return False, "AI API Key is not configured. Please enter your API key in AI Settings (Studio -> AI Copilot & Models)."

    system_text = system_instruction or ai_cfg.get(
        "system_instructions",
        "You are an expert academic tutor and LaTeX formula specialist for shrtnotes. You transform study notes into clear, high-yield revision summaries with proper KaTeX formulas and responsive tables."
    )

    if provider == "gemini":
        candidate_models = [model] if model else []
        for fb in ["gemini-3.6-flash", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
            if fb not in candidate_models:
                candidate_models.append(fb)

        last_err = ""
        for cur_model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{cur_model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [{"text": f"{system_text}\n\nTask:\n{prompt}" if system_text else prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 4096
                }
            }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            # Allow 1 quick retry on 503 high demand before switching model
            for attempt in range(2):
                try:
                    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=40)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            return True, text.strip()
                    elif resp.status_code == 503:
                        if attempt == 0:
                            time.sleep(1.5)
                            continue
                        last_err = f"Gemini API 503 High Demand on {cur_model}"
                        break
                    elif resp.status_code == 404:
                        last_err = f"Gemini API 404 (Model {cur_model} deprecated/not found)"
                        break
                    else:
                        try:
                            err_json = resp.json()
                            err_msg = err_json.get("error", {}).get("message", resp.text)
                        except Exception:
                            err_msg = resp.text
                        last_err = f"Gemini API Error ({resp.status_code}) on {cur_model}: {err_msg}"
                        if resp.status_code == 429:
                            return False, last_err
                        break
                except requests.exceptions.Timeout:
                    last_err = f"Gemini API request timed out on {cur_model} (waited 40s)."
                    break
                except Exception as e:
                    return False, f"Failed to call Gemini API: {str(e)}"

        return False, last_err or "Gemini API unavailable across candidate models. Please check your key or try Groq/Ollama."

    elif provider in ["openai", "groq", "ollama", "custom"]:
        base_url = custom_endpoint or ai_cfg.get("custom_endpoint", "").strip()
        if not base_url:
            if provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
                if not model:
                    model = "llama-3.3-70b-versatile"
            elif provider == "ollama":
                base_url = "http://localhost:11434/v1"
                if not model:
                    model = "llama3"
            else:  # openai
                base_url = "https://api.openai.com/v1"
                if not model:
                    model = "gpt-4o-mini"

        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        messages = []
        if system_text:
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096
        }
        if json_mode and provider in ["openai", "groq"]:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            if resp.status_code != 200:
                try:
                    err_json = resp.json()
                    err_msg = err_json.get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                return False, f"AI Provider Error ({resp.status_code}): {err_msg}"

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return False, "AI returned empty response choices."
            text = choices[0].get("message", {}).get("content", "")
            return True, text.strip()
        except requests.exceptions.Timeout:
            return False, "AI API request timed out (30s). Please try again."
        except Exception as e:
            return False, f"Failed to call AI API: {str(e)}"

    return False, f"Unsupported AI provider '{provider}'."


def offline_fallback_formatter(text):
    """Smart offline formatting heuristics when AI is unavailable or busy."""
    import re
    lines = text.strip().split("\n")
    formatted_lines = []
    
    greek = {
        r'\bpi\b': r'\pi', r'\btheta\b': r'\theta', r'\balpha\b': r'\alpha',
        r'\bbeta\b': r'\beta', r'\bgamma\b': r'\gamma', r'\bdelta\b': r'\delta',
        r'\blambda\b': r'\lambda', r'\bomega\b': r'\omega', r'\bmu\b': r'\mu',
        r'\bphi\b': r'\phi', r'\bsigma\b': r'\sigma', r'\bepsilon\b': r'\epsilon'
    }

    for line in lines:
        s = line.strip()
        if not s:
            formatted_lines.append("")
            continue

        is_formula = (
            any(sym in s for sym in ["=", "\\int", "\\sum", "\\sqrt", "lim", "->"])
            and not s.startswith("#")
            and not s.startswith("$")
            and not s.startswith("*")
            and len(s.split()) < 15
        )

        if is_formula:
            clean_s = s
            for k, v in greek.items():
                clean_s = re.sub(k, v, clean_s)
            formatted_lines.append(f"$$\n{clean_s}\n$$")
        else:
            formatted_lines.append(line)

    return "\n".join(formatted_lines)


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

    /* Left Sidebar Testing & Production Hub Styles */
    .sidebar-hub {
      margin: 0.65rem;
      padding: 0.65rem;
      background: #0d1527;
      border: 1px solid #1e293b;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
    }
    .sidebar-hub-tabs {
      display: flex;
      background: #080c14;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 2px;
      gap: 2px;
    }
    .sidebar-hub-tab {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.35rem;
      padding: 0.35rem 0.45rem;
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.725rem;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
    }
    .sidebar-hub-tab:hover {
      color: #fff;
    }
    .sidebar-hub-tab.active {
      background: #1e293b;
      color: #93c5fd;
      box-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    .sidebar-hub-tab.active.tab-prod {
      color: #6ee7b7;
      background: #064e3b;
    }
    .sidebar-hub-panel {
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }
    .sidebar-hub-qr-row {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      background: rgba(0,0,0,0.25);
      border-radius: 6px;
      padding: 0.45rem;
    }
    .sidebar-qr-box {
      background: #ffffff;
      border-radius: 4px;
      padding: 3px;
      width: 76px;
      height: 76px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .sidebar-qr-box svg {
      width: 100%;
      height: 100%;
      display: block;
    }
    .sidebar-hub-info {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      min-width: 0;
    }
    .sidebar-hub-title {
      font-size: 0.775rem;
      font-weight: 700;
      color: #93c5fd;
    }
    .sidebar-hub-badge {
      display: inline-block;
      font-size: 0.625rem;
      font-weight: 600;
      padding: 1px 5px;
      border-radius: 3px;
      background: #1e3a8a;
      color: #bfdbfe;
      width: fit-content;
    }
    .sidebar-hub-badge.badge-green {
      background: #064e3b;
      color: #a7f3d0;
    }
    .sidebar-url-box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #080c14;
      border: 1px solid #1e293b;
      border-radius: 4px;
      padding: 0.3rem 0.45rem;
      gap: 0.35rem;
    }
    .sidebar-url-text {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.675rem;
      color: #cbd5e1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sidebar-copy-btn {
      background: #1e293b;
      border: 1px solid rgba(255,255,255,0.1);
      color: #93c5fd;
      padding: 0.2rem 0.45rem;
      border-radius: 3px;
      font-size: 0.65rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      flex-shrink: 0;
      transition: all 0.15s;
    }
    .sidebar-copy-btn:hover {
      background: #3b82f6;
      color: #fff;
    }
    .sidebar-hub-actions {
      display: flex;
      gap: 0.4rem;
    }
    .sidebar-hub-btn {
      flex: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.35rem;
      padding: 0.35rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.15s;
    }

    /* AI Copilot & Assistant Styles */
    .ai-copilot-card {
      background: linear-gradient(135deg, #1e1035 0%, #0d1527 100%);
      border: 1px solid #7e22ce;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 12px rgba(126, 34, 206, 0.15);
    }
    .ai-copilot-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .ai-pulse-dot {
      width: 8px;
      height: 8px;
      background: #a855f7;
      border-radius: 50%;
      display: inline-block;
      box-shadow: 0 0 8px #c084fc;
      animation: pulse-ai 2s infinite;
    }
    @keyframes pulse-ai {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.25); }
    }
    .ai-copilot-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .ai-action-btn {
      background: #2e1065;
      border: 1px solid #9333ea;
      color: #e9d5ff;
      padding: 0.45rem 0.85rem;
      border-radius: 6px;
      font-size: 0.825rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.15s ease;
      font-family: inherit;
    }
    .ai-action-btn:hover {
      background: #3b0764;
      border-color: #c084fc;
      color: #fff;
      transform: translateY(-1px);
    }
    .ai-action-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }
    .ai-modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }
    .ai-modal-box {
      background: #111827;
      border: 1px solid #7e22ce;
      border-radius: 12px;
      width: 90%;
      max-width: 680px;
      padding: 1.75rem;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
    }
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
        <a href="{{ url_for('route_ai_settings') }}" class="nav-btn {% if active_tab == 'ai' %}active{% endif %}">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a8 8 0 0 0-8 8c0 3.31 2.01 6.16 4.9 7.37.13.06.2.2.2.35v1.28c0 .55.45 1 1 1h3.8c.55 0 1-.45 1-1v-1.28c0-.15.07-.29.2-.35 2.89-1.21 4.9-4.06 4.9-7.37a8 8 0 0 0-8-8z"/><line x1="9" x2="15" y1="22" y2="22"/><line x1="10" x2="14" y1="18" y2="18"/></svg>
          <span>AI Copilot & Models</span>
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

    <!-- Left Sidebar Testing & Production Hub -->
    <div class="sidebar-hub">
      <div class="sidebar-hub-tabs">
        <button type="button" class="sidebar-hub-tab active tab-lan" id="tab-btn-lan" onclick="switchSidebarHub('lan')">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><line x1="12" x2="12.01" y1="18" y2="18"/></svg>
          <span>LAN Mobile</span>
        </button>
        <button type="button" class="sidebar-hub-tab tab-prod" id="tab-btn-prod" onclick="switchSidebarHub('prod')">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          <span>Live Site</span>
        </button>
      </div>

      <!-- LAN Panel -->
      <div class="sidebar-hub-panel" id="sidebar-panel-lan">
        <div class="sidebar-hub-qr-row">
          <div class="sidebar-qr-box" title="Scan with phone camera to test live on mobile">
            {{ lan_qr_svg|safe }}
          </div>
          <div class="sidebar-hub-info">
            <span class="sidebar-hub-title">Wi-Fi Testing</span>
            <span class="sidebar-hub-badge">Local Hotspot</span>
            <span style="font-size: 0.65rem; color: #64748b; line-height: 1.2; margin-top: 2px;">Same Wi-Fi required</span>
          </div>
        </div>

        <div class="sidebar-url-box">
          <span class="sidebar-url-text" title="{{ lan_url }}">{{ lan_url }}</span>
          <button type="button" class="sidebar-copy-btn" onclick="copySidebarUrl('{{ lan_url }}', this)" title="Copy LAN URL">
            <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            <span>Copy</span>
          </button>
        </div>

        <div class="sidebar-hub-actions">
          <a href="{{ lan_url }}" target="_blank" class="sidebar-hub-btn btn-primary">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>
            <span>Open Preview</span>
          </a>
        </div>
      </div>

      <!-- Deployed Production Panel -->
      <div class="sidebar-hub-panel" id="sidebar-panel-prod" style="display: none;">
        <div class="sidebar-hub-qr-row">
          <div class="sidebar-qr-box" title="Scan with phone camera to open live deployed site">
            {{ deployed_qr_svg|safe }}
          </div>
          <div class="sidebar-hub-info">
            <span class="sidebar-hub-title" style="color: #6ee7b7;">Production</span>
            <span class="sidebar-hub-badge badge-green">Cloudflare Pages</span>
            <span style="font-size: 0.65rem; color: #64748b; line-height: 1.2; margin-top: 2px;">Public edge CDN</span>
          </div>
        </div>

        <div class="sidebar-url-box">
          <span class="sidebar-url-text" title="{{ deployed_url }}">{{ deployed_url }}</span>
          <button type="button" class="sidebar-copy-btn" onclick="copySidebarUrl('{{ deployed_url }}', this)" title="Copy live URL">
            <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            <span>Copy</span>
          </button>
        </div>

        <div class="sidebar-hub-actions">
          <a href="{{ deployed_url }}" target="_blank" class="sidebar-hub-btn btn-success">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>
            <span>Open Live Site</span>
          </a>
        </div>
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

      <!-- Dynamic Tab Content -->
      <!-- CONTENT_PLACEHOLDER -->
    </div>
  </main>

  <script>
    function switchSidebarHub(tab) {
      const btnLan = document.getElementById('tab-btn-lan');
      const btnProd = document.getElementById('tab-btn-prod');
      const panelLan = document.getElementById('sidebar-panel-lan');
      const panelProd = document.getElementById('sidebar-panel-prod');
      if (tab === 'lan') {
        btnLan.classList.add('active');
        btnProd.classList.remove('active');
        panelLan.style.display = 'flex';
        panelProd.style.display = 'none';
      } else {
        btnProd.classList.add('active');
        btnLan.classList.remove('active');
        panelProd.style.display = 'flex';
        panelLan.style.display = 'none';
      }
    }

    function copySidebarUrl(text, btn) {
      navigator.clipboard.writeText(text).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span>Copied!</span>`;
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
        <td>
          <span class="badge badge-blue">{{ note.subject_name }}</span>
          {% if note.branch_name %}
          <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #6ee7b7; font-size: 0.72rem; margin-left: 0.25rem;">{{ note.branch_name }}</span>
          {% endif %}
        </td>
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
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
    <h3 class="card-title" style="margin-bottom: 0;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
      <span>{% if is_edit %}Edit Topic{% else %}Write New Study Topic{% endif %}</span>
    </h3>
    <button type="button" class="btn" onclick="openAIDraftModal()" style="background: linear-gradient(135deg, #7e22ce 0%, #3b82f6 100%); color: #fff; font-size: 0.85rem; padding: 0.45rem 1rem;">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/></svg>
      <span>🪄 Quick Draft from Raw Text</span>
    </button>
  </div>

  <!-- AI Studio Copilot Panel -->
  <div class="ai-copilot-card">
    <div class="ai-copilot-header">
      <div style="display: flex; align-items: center; gap: 0.6rem;">
        <span class="ai-pulse-dot"></span>
        <strong style="color: #c084fc; font-size: 0.95rem;">AI Studio Copilot</strong>
        <span class="badge" id="ai-status-badge" style="background: rgba(168, 85, 247, 0.2); color: #d8b4fe; font-size: 0.7rem;">
          {{ ai_status_text }}
        </span>
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: center;">
        <a href="{{ url_for('route_ai_settings') }}" target="_blank" style="font-size: 0.75rem; color: #a855f7; text-decoration: underline;">
          ⚙️ AI Settings
        </a>
      </div>
    </div>

    <div style="font-size: 0.775rem; color: #cbd5e1; margin-bottom: 0.75rem;">
      1-Click AI assistance for your topic content, formulas, tables, and Google SEO:
    </div>

    <!-- Quick action buttons -->
    <div class="ai-copilot-actions">
      <button type="button" class="ai-action-btn" id="btn-ai-format" onclick="runAICopilot('format_notes')" title="Converts raw text into clean Markdown with KaTeX formulas and responsive tables">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/></svg>
        <span>✨ Format to KaTeX & Markdown</span>
      </button>

      <button type="button" class="ai-action-btn" id="btn-ai-seo" onclick="runAICopilot('generate_seo')" title="Auto-generates Topic Title, URL Slug, Search Snippet, and SEO Keywords">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <span>🏷️ Auto-Fill SEO & Tags</span>
      </button>

      <button type="button" class="ai-action-btn" id="btn-ai-formula" onclick="runAICopilot('formula_sheet')" title="Generates a High-Yield Formula Cheat-Sheet box at the end of the note">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="9" y2="9"/><line x1="4" x2="20" y1="15" y2="15"/><line x1="10" x2="8" y1="3" y2="21"/><line x1="16" x2="14" y1="3" y2="21"/></svg>
        <span>📐 Add Formula Cheat-Sheet</span>
      </button>

      <button type="button" class="ai-action-btn" id="btn-ai-quiz" onclick="runAICopilot('generate_quiz')" title="Generates 3 practice MCQs with collapsible answers for student recall">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
        <span>📝 Add 3 Practice MCQs</span>
      </button>

      <button type="button" class="ai-action-btn" id="btn-ai-tables" onclick="runAICopilot('fix_tables')" title="Cleans up and formats tables so they never disturb alignment">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/></svg>
        <span>📊 Clean & Align Tables</span>
      </button>
    </div>

    <!-- AI Live Status Banner -->
    <div id="ai-feedback-msg" style="display: none; margin-top: 0.75rem; padding: 0.5rem 0.85rem; border-radius: 6px; font-size: 0.8rem;"></div>
  </div>

  <form method="POST" action="{{ action_url }}" id="topic-form">
    {% if is_edit %}
    <input type="hidden" name="original_path" value="{{ original_path }}">
    {% endif %}

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Subject *</label>
        <select name="subject" id="note-subject-select" class="form-control" required onchange="onSubjectChange()">
          {% for sub in config.subjects %}
          <option value="{{ sub.id }}" {% if note_meta.get('subject') == sub.id %}selected{% endif %}>{{ sub.name }}</option>
          {% endfor %}
        </select>
      </div>

      <div class="form-group" id="branch-select-group" style="display: none;">
        <label class="form-label">Branch *</label>
        <select name="branch" id="note-branch-select" class="form-control" onchange="updateChapterOptions()">
          <!-- Populated dynamically via JS -->
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
        <input type="text" name="title" id="note-title" class="form-control" value="{{ note_meta.get('title', '') }}" placeholder="e.g. Fundamental Theorem of Calculus" required>
      </div>
      <div class="form-group">
        <label class="form-label">URL Slug (lowercase-hyphens) *</label>
        <input type="text" name="slug" id="note-slug" class="form-control" value="{{ note_meta.get('slug', '') }}" placeholder="e.g. fundamental-theorem" required>
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">Google Search Snippet / Excerpt (1-2 sentences)</label>
        <input type="text" name="excerpt" id="note-excerpt" class="form-control" value="{{ note_meta.get('excerpt', '') }}" placeholder="A 1-2 sentence high-yield summary for Google search results...">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Displays under your topic title in Google search results.</span>
      </div>
      <div class="form-group">
        <label class="form-label">SEO Keywords & Topic Tags (comma-separated)</label>
        <input type="text" name="tags" id="note-tags" class="form-control" value="{{ tags_str }}" placeholder="e.g. calculus, derivatives, integration, fundamental-theorem">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Used for Google indexing, Schema.org metadata, and page tag badges.</span>
      </div>
    </div>

    <div class="form-group">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">Topic Content (Markdown & KaTeX Formulas Supported) *</label>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Inline: <code>$E = mc^2$</code> | Block Display: <code>$$\\int_0^1 x dx$$</code></span>
      </div>
      <textarea name="content" id="note-content" class="form-control" placeholder="Write or paste your study notes here..." required>{{ raw_content }}</textarea>
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-success" style="font-size: 0.95rem; padding: 0.65rem 1.4rem;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/></svg>
        <span>Save Topic & Rebuild Clean URLs</span>
      </button>
      <a href="{{ url_for('route_notes') }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>

<!-- Quick Draft Modal -->
<div class="ai-modal-overlay" id="ai-draft-modal">
  <div class="ai-modal-box">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
      <h3 style="font-size: 1.15rem; color: #fff; display: flex; align-items: center; gap: 0.5rem;">
        <span>🪄 Quick Draft with AI Copilot</span>
      </h3>
      <button type="button" onclick="closeAIDraftModal()" style="background: transparent; border: none; color: #94a3b8; font-size: 1.5rem; cursor: pointer; line-height: 1;">&times;</button>
    </div>
    <p style="font-size: 0.825rem; color: #94a3b8; margin-bottom: 1rem;">
      Paste any messy textbook paragraphs, lecture notes, or rough formula text. AI Copilot will automatically structure it into clean Markdown, convert formulas to KaTeX, and fill your title, slug, excerpt, tags, subject, and chapter!
    </p>

    <div class="form-group">
      <label class="form-label">Raw Notes / Study Material:</label>
      <textarea id="ai-raw-draft-input" class="form-control" style="min-height: 200px; font-size: 0.85rem;" placeholder="Paste raw text here, e.g.:&#10;Carnot Heat Engine: The efficiency of a reversible Carnot engine operating between temperatures T1 and T2 is eta = 1 - T2/T1. Work done is W = Q1 - Q2..."></textarea>
    </div>

    <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.25rem;">
      <button type="button" class="btn btn-secondary" onclick="closeAIDraftModal()">Cancel</button>
      <button type="button" class="btn" id="btn-run-draft" onclick="executeAIDraft()" style="background: linear-gradient(135deg, #7e22ce 0%, #3b82f6 100%); color: #fff;">
        <span>✨ Generate Full Topic</span>
      </button>
    </div>
  </div>
</div>

<script>
  const subjectsData = {{ subjects_json|safe }};
  const currentBranch = "{{ note_meta.get('branch', '') }}";
  const currentChapter = "{{ note_meta.get('chapter', '') }}";

  function onSubjectChange() {
    const subSelect = document.getElementById('note-subject-select');
    const branchGroup = document.getElementById('branch-select-group');
    const branchSelect = document.getElementById('note-branch-select');
    const selectedSubId = subSelect.value;
    const subObj = subjectsData.find(s => s.id === selectedSubId);

    if (subObj && subObj.branches && subObj.branches.length > 0) {
      branchGroup.style.display = 'block';
      branchSelect.required = true;
      branchSelect.innerHTML = '';
      subObj.branches.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = b.name;
        if (b.id === currentBranch || b.name.toLowerCase() === currentBranch.toLowerCase()) {
          opt.selected = true;
        }
        branchSelect.appendChild(opt);
      });
    } else {
      branchGroup.style.display = 'none';
      branchSelect.required = false;
      branchSelect.innerHTML = '';
    }
    updateChapterOptions();
  }

  function updateChapterOptions() {
    const subSelect = document.getElementById('note-subject-select');
    const branchSelect = document.getElementById('note-branch-select');
    const chSelect = document.getElementById('note-chapter-select');
    const selectedSubId = subSelect.value;
    const subObj = subjectsData.find(s => s.id === selectedSubId);

    chSelect.innerHTML = '';
    let chapters = [];

    if (subObj && subObj.branches && subObj.branches.length > 0) {
      const selectedBranchId = branchSelect.value;
      const branchObj = subObj.branches.find(b => b.id === selectedBranchId) || subObj.branches[0];
      if (branchObj && branchObj.chapters) {
        chapters = branchObj.chapters;
      }
    } else if (subObj && subObj.chapters) {
      chapters = subObj.chapters;
    }

    if (chapters.length > 0) {
      chapters.forEach(ch => {
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
  onSubjectChange();

  function showAIFeedback(msg, isSuccess = true) {
    const box = document.getElementById('ai-feedback-msg');
    box.style.display = 'block';
    if (isSuccess) {
      box.style.background = '#064e3b';
      box.style.border = '1px solid #059669';
      box.style.color = '#a7f3d0';
      box.innerHTML = msg;
    } else {
      box.style.background = '#450a0a';
      box.style.border = '1px solid #dc2626';
      box.style.color = '#fecaca';
      box.innerHTML = msg;
    }
    setTimeout(() => {
      box.style.display = 'none';
    }, 7000);
  }

  function openAIDraftModal() {
    document.getElementById('ai-draft-modal').style.display = 'flex';
  }

  function closeAIDraftModal() {
    document.getElementById('ai-draft-modal').style.display = 'none';
  }

  async function runAICopilot(action) {
    const contentArea = document.getElementById('note-content');
    const titleInput = document.getElementById('note-title');
    const subSelect = document.getElementById('note-subject-select');
    const branchSelect = document.getElementById('note-branch-select');
    const chSelect = document.getElementById('note-chapter-select');

    const contentVal = contentArea.value.trim();
    if (!contentVal && action !== 'generate_seo') {
      alert('Please enter some text in the topic content textarea first, then run AI Copilot.');
      contentArea.focus();
      return;
    }

    const btnIdMap = {
      'format_notes': 'btn-ai-format',
      'generate_seo': 'btn-ai-seo',
      'formula_sheet': 'btn-ai-formula',
      'generate_quiz': 'btn-ai-quiz',
      'fix_tables': 'btn-ai-tables'
    };
    const targetBtn = document.getElementById(btnIdMap[action]);
    const originalText = targetBtn.innerHTML;
    targetBtn.disabled = true;
    targetBtn.innerHTML = `<span>⏳ Processing with AI...</span>`;

    try {
      const resp = await fetch('{{ url_for("route_api_ai_copilot") }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          content: contentVal,
          title: titleInput.value,
          subject: subSelect.value,
          branch: (branchSelect && branchSelect.offsetParent !== null) ? branchSelect.value : '',
          chapter: chSelect.value
        })
      });

      const res = await resp.json();
      if (!res.success) {
        showAIFeedback(`⚠️ ${res.message} <a href="{{ url_for('route_ai_settings') }}" style="color:#fff; text-decoration:underline; font-weight:bold; margin-left:0.5rem;">Configure API Key &rarr;</a>`, false);
      } else {
        if (action === 'format_notes') {
          contentArea.value = res.data;
          showAIFeedback(res.warning ? ('⚡ ' + res.warning) : '✨ Study notes formatted with KaTeX math formulas and clean Markdown!');
        } else if (action === 'fix_tables') {
          contentArea.value = res.data;
          showAIFeedback('📊 Table formatted into clean, responsive Markdown!');
        } else if (action === 'formula_sheet') {
          contentArea.value = contentArea.value.trim() + '\\n\\n' + res.data;
          showAIFeedback('📐 High-Yield Formula Cheat-Sheet inserted at the bottom!');
        } else if (action === 'generate_quiz') {
          contentArea.value = contentArea.value.trim() + '\\n\\n' + res.data;
          showAIFeedback('📝 3 Practice MCQs inserted with collapsible answers!');
        } else if (action === 'generate_seo') {
          const seo = res.data;
          if (seo.title && !titleInput.value) titleInput.value = seo.title;
          if (seo.slug) document.getElementById('note-slug').value = seo.slug;
          if (seo.excerpt) document.getElementById('note-excerpt').value = seo.excerpt;
          if (seo.tags) document.getElementById('note-tags').value = seo.tags;
          if (seo.subject) {
            subSelect.value = seo.subject;
            onSubjectChange();
            if (seo.branch && branchSelect) {
              branchSelect.value = seo.branch;
              updateChapterOptions();
            }
            if (seo.chapter) chSelect.value = seo.chapter;
          }
          showAIFeedback('🏷️ Title, URL Slug, Excerpt, and SEO Tags generated!');
        }
      }
    } catch (err) {
      showAIFeedback(`Failed to contact AI Copilot: ${err.message}`, false);
    } finally {
      targetBtn.disabled = false;
      targetBtn.innerHTML = originalText;
    }
  }

  async function executeAIDraft() {
    const rawInput = document.getElementById('ai-raw-draft-input').value.trim();
    if (!rawInput) {
      alert('Please paste some study text or notes to draft.');
      return;
    }

    const btn = document.getElementById('btn-run-draft');
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>⏳ Generating Topic...</span>';

    try {
      const resp = await fetch('{{ url_for("route_api_ai_copilot") }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'quick_draft',
          content: rawInput
        })
      });

      const res = await resp.json();
      if (!res.success) {
        alert(res.message);
      } else {
        const d = res.data;
        if (d.title) document.getElementById('note-title').value = d.title;
        if (d.slug) document.getElementById('note-slug').value = d.slug;
        if (d.excerpt) document.getElementById('note-excerpt').value = d.excerpt;
        if (d.tags) document.getElementById('note-tags').value = d.tags;
        if (d.content) document.getElementById('note-content').value = d.content;
        if (d.subject) {
          const subSelect = document.getElementById('note-subject-select');
          subSelect.value = d.subject;
          onSubjectChange();
          if (d.branch && document.getElementById('note-branch-select')) {
            document.getElementById('note-branch-select').value = d.branch;
            updateChapterOptions();
          }
          if (d.chapter) document.getElementById('note-chapter-select').value = d.chapter;
        }
        closeAIDraftModal();
        showAIFeedback('🎉 Topic draft created successfully! Review and click Save when ready.');
      }
    } catch (err) {
      alert(`Error generating draft: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
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
    {% if sub.branches %}
    <!-- Branches list under this subject -->
    <div style="margin-left: 1rem;">
      <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.6rem; letter-spacing: 0.05em;">
        Branches & Chapters in {{ sub.name }}:
      </div>
      {% for b in sub.branches %}
      <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--card-border); border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.5rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <div style="width: 24px; height: 24px; border-radius: 4px; background: rgba(59, 130, 246, 0.15); display: flex; align-items: center; justify-content: center; color: var(--accent);">
              {{ get_icon(b.icon or sub.icon)|safe }}
            </div>
            <strong style="font-size: 0.95rem; color: #93c5fd;">{{ b.name }}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted);">(<code>/{{ sub.id }}/{{ b.id }}/</code>)</span>
          </div>
          <span class="badge badge-blue" style="font-size: 0.72rem;">{{ b.chapters|length }} Chapters</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0.85rem;">
          {% for ch in b.chapters %}
          <div style="background: #111827; border: 1px solid var(--card-border); border-radius: 6px; padding: 0.65rem 0.85rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong style="font-size: 0.9rem;">{{ ch.name }}</strong>
              <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;"><code>/{{ sub.id }}/{{ b.id }}/{{ ch.id }}/</code></span>
              {% if ch.description %}
              <p style="font-size: 0.775rem; color: var(--text-muted); margin-top: 0.15rem;">{{ ch.description }}</p>
              {% endif %}
            </div>
            <div style="display: flex; gap: 0.4rem;">
              <a href="{{ url_for('route_new_note') }}?sub={{ sub.id }}&branch={{ b.id }}&ch={{ ch.id }}" class="btn btn-success" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;">+ Add Topic</a>
              <a href="{{ url_for('route_edit_chapter', sub_id=sub.id, ch_id=ch.id) }}" class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;">Edit</a>
              <form method="POST" action="{{ url_for('route_delete_chapter', sub_id=sub.id, ch_id=ch.id) }}" style="display: inline;" onsubmit="return confirm('Delete chapter {{ ch.name }}?');">
                <button type="submit" class="btn btn-danger" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;">Delete</button>
              </form>
            </div>
          </div>
          {% endfor %}
          {% if not b.chapters %}
          <div style="color: var(--text-muted); font-size: 0.8rem; font-style: italic;">No chapters in {{ b.name }} yet. Add a chapter below.</div>
          {% endif %}
        </div>

        <!-- Quick Add Chapter Form to this branch -->
        <form method="POST" action="{{ url_for('route_add_chapter', sub_id=sub.id) }}" style="background: rgba(0,0,0,0.2); padding: 0.6rem; border-radius: 6px; border: 1px dashed var(--card-border); display: flex; gap: 0.6rem; align-items: center;">
          <input type="hidden" name="branch_id" value="{{ b.id }}">
          <input type="text" name="ch_name" class="form-control" placeholder="New Chapter in {{ b.name }} (e.g. Hydrocarbons)" style="padding: 0.35rem 0.6rem; font-size: 0.8rem;" required>
          <input type="text" name="ch_id" class="form-control" placeholder="Slug (e.g. hydrocarbons)" style="padding: 0.35rem 0.6rem; font-size: 0.8rem;" required>
          <input type="text" name="ch_desc" class="form-control" placeholder="Short description (optional)" style="padding: 0.35rem 0.6rem; font-size: 0.8rem;">
          <button type="submit" class="btn btn-primary" style="white-space: nowrap; padding: 0.35rem 0.75rem; font-size: 0.8rem;">+ Add to {{ b.name }}</button>
        </form>
      </div>
      {% endfor %}
    </div>

    {% else %}
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
    {% endif %}
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
    <span>Edit Chapter: {{ target_chapter.name }} ({{ sub.name }}{% if branch %} &gt; {{ branch.name }}{% endif %})</span>
  </h3>

  <form method="POST" action="{{ url_for('route_save_chapter', sub_id=sub.id, ch_id=target_chapter.id) }}">
    {% if branch %}
    <input type="hidden" name="branch_id" value="{{ branch.id }}">
    {% endif %}
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

  <!-- Adsterra High-Yield Optimization Guide -->
  <div style="background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); border: 1px solid #4338ca; border-radius: 10px; padding: 1.5rem; margin-bottom: 2rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
      <span style="font-size: 1.5rem;">💰</span>
      <div>
        <h3 style="font-size: 1.15rem; color: #e0e7ff; margin: 0; font-weight: 700;">Adsterra Maximum Revenue Blueprint</h3>
        <span style="font-size: 0.8rem; color: #a5b4fc;">How to achieve maximum RPM without annoying or interrupting students</span>
      </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1rem; font-size: 0.825rem; color: #cbd5e1;">
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
        <strong style="color: #93c5fd; display: block; margin-bottom: 0.25rem;">👑 300&times;250 Medium Rectangle (#1 Format)</strong>
        Generates highest eCPM ($1.50–$3.50+) across all countries. Fits 100% of mobile screens and desktop sidebars without any clipping.
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
        <strong style="color: #a7f3d0; display: block; margin-bottom: 0.25rem;">📌 160&times;600 Sticky Lateral Rail</strong>
        Stays in view for 3–5 minutes while students read formulas. Extreme viewability dwell time drastically increases advertiser bids.
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
        <strong style="color: #fde047; display: block; margin-bottom: 0.25rem;">💡 Native Recommendation Widget</strong>
        Matches study note cards! Produces 3x–8x higher CTR than standard banners with ZERO annoyance to students.
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 0.85rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
        <strong style="color: #f472b6; display: block; margin-bottom: 0.25rem;">📱 Mobile Responsive Separation</strong>
        728&times;90 for desktop monitors and 320&times;50 for smartphones. Prevents layout breakages and maximizes mobile revenue.
      </div>
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
      <textarea name="head_code" class="form-control" style="min-height: 70px;" placeholder="Paste any header script (e.g. Media.net, Ezoic, Google AdSense)">{{ config.ads.head_code }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Injected into &lt;head&gt; across all pages automatically.</span>
    </div>

    <!-- Slot 1: Header Banners (Desktop & Mobile) -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">1. Top Header Banner (Desktop 728&times;90)</label>
        <span class="badge" style="background: #1e3a8a; color: #93c5fd;">728&times;90 Desktop Leaderboard</span>
      </div>
      <textarea name="header_ad" class="form-control" style="min-height: 80px;" placeholder="Paste Desktop 728x90 Leaderboard ad unit code">{{ config.ads.header_ad }}</textarea>
      
      <div style="margin-top: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
          <label class="form-label" style="margin-bottom: 0; font-size: 0.85rem; color: #a7f3d0;">Mobile Header Banner (320&times;50 / 300&times;250)</label>
          <span class="badge" style="background: #064e3b; color: #a7f3d0;">320&times;50 Mobile Phone</span>
        </div>
        <textarea name="header_ad_mobile" class="form-control" style="min-height: 70px;" placeholder="Optional: Paste dedicated 320x50 or 300x250 mobile ad code. (If blank, desktop unit scales responsively)">{{ config.ads.header_ad_mobile }}</textarea>
        <span style="font-size: 0.725rem; color: var(--text-muted);">Displayed exclusively on smartphones to guarantee zero horizontal scrolling.</span>
      </div>
    </div>

    <!-- Slot 2: Top In-Article Ad (Primary 300x250) -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">2. Top In-Article Ad (Highest CPM & Fill Rate)</label>
        <span class="badge" style="background: #1e3a8a; color: #93c5fd;">300&times;250 Medium Rectangle</span>
      </div>
      <textarea name="in_article_ad" class="form-control" style="min-height: 80px;" placeholder="Paste HTML/JS unit code for 300x250 Medium Rectangle">{{ config.ads.in_article_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Placed right before notes prose. Flawless on both desktop and mobile viewports.</span>
    </div>

    <!-- Slot 3: Post-Article Natural Break (Secondary 300x250) -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">3. Post-Article / End-of-Note Ad (300&times;250)</label>
        <span class="badge" style="background: #064e3b; color: #a7f3d0;">300&times;250 Natural Break</span>
      </div>
      <textarea name="in_article_ad_2" class="form-control" style="min-height: 80px;" placeholder="Optional: Paste a second 300x250 ad tag for the end of note reading (before Next/Prev buttons)">{{ config.ads.in_article_ad_2 }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Appears when the student completes reading. High engagement, zero distraction during study.</span>
    </div>

    <!-- Slot 4: Sidebar Sticky Skyscraper -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">4. Desktop Sticky Lateral Rail Ad Code</label>
        <div style="display: flex; gap: 0.35rem;">
          <span class="badge" style="background: #1e3a8a; color: #93c5fd;">160&times;600 Skyscraper</span>
          <span class="badge" style="background: #581c87; color: #e9d5ff;">300&times;600 Half-Page</span>
        </div>
      </div>
      <textarea name="sidebar_ad" class="form-control" style="min-height: 80px;" placeholder="Paste HTML/JS unit code for 160x600 or 300x600 sidebar">{{ config.ads.sidebar_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Pins to desktop widescreen lateral rail. Generates high viewability income while reading.</span>
    </div>

    <!-- Slot 5: Native Recommendation Widget -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">5. Adsterra Native Recommendation Widget (Highest CTR)</label>
        <span class="badge" style="background: #854d0e; color: #fef08a;">Native 1x4 or 2x2</span>
      </div>
      <textarea name="native_ad" class="form-control" style="min-height: 80px;" placeholder="Paste Adsterra Native Banner script here">{{ config.ads.native_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Blends seamlessly with topic recommendation cards. Yields 3x–8x higher click rates.</span>
    </div>

    <!-- Slot 6: Bottom Footer Banners -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">6. Bottom Footer Banner (Desktop)</label>
        <span class="badge" style="background: #1e3a8a; color: #93c5fd;">728&times;90 / 468&times;60</span>
      </div>
      <textarea name="footer_ad" class="form-control" style="min-height: 80px;" placeholder="Paste Desktop bottom banner unit code">{{ config.ads.footer_ad }}</textarea>

      <div style="margin-top: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
          <label class="form-label" style="margin-bottom: 0; font-size: 0.85rem; color: #a7f3d0;">Mobile Footer Banner (320&times;50)</label>
          <span class="badge" style="background: #064e3b; color: #a7f3d0;">320&times;50 Mobile</span>
        </div>
        <textarea name="footer_ad_mobile" class="form-control" style="min-height: 70px;" placeholder="Optional: Paste 320x50 mobile footer unit code">{{ config.ads.footer_ad_mobile }}</textarea>
      </div>
    </div>

    <!-- Slot 7: Adsterra Social Bar (In-Page Push) -->
    <div class="form-group" style="background: #0f172a; border: 1px solid var(--card-border); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
        <label class="form-label" style="margin-bottom: 0;">7. Adsterra Social Bar (Optional High-CPM In-Page Push)</label>
        <span class="badge" style="background: #701a75; color: #f5d0fe;">$2.00–$5.00+ CPM</span>
      </div>
      <textarea name="social_bar_ad" class="form-control" style="min-height: 70px;" placeholder="Optional: Paste Adsterra Social Bar script code">{{ config.ads.social_bar_ad }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Displays as a non-intrusive lightweight pill with an instant close button. Extremely high CPM.</span>
    </div>

    <!-- Google AdSense Quick Setup Helper -->
    <div style="background: #172554; border: 1px solid #1e40af; border-radius: 8px; padding: 1.25rem; margin-top: 1.5rem;">
      <h4 style="font-size: 0.95rem; color: #93c5fd; margin-bottom: 0.5rem;">Google AdSense Fallback Helper (Optional)</h4>
      <p style="font-size: 0.8rem; color: #cbd5e1; margin-bottom: 1rem;">
        If you prefer standard AdSense auto-units, enter your Client ID and Slot IDs below:
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
# AI Settings Template
# ==============================================================================
AI_SETTINGS_HTML = """
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
    <div>
      <h3 class="card-title" style="margin-bottom: 0.25rem;">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a8 8 0 0 0-8 8c0 3.31 2.01 6.16 4.9 7.37.13.06.2.2.2.35v1.28c0 .55.45 1 1 1h3.8c.55 0 1-.45 1-1v-1.28c0-.15.07-.29.2-.35 2.89-1.21 4.9-4.06 4.9-7.37a8 8 0 0 0-8-8z"/><line x1="9" x2="15" y1="22" y2="22"/><line x1="10" x2="14" y1="18" y2="18"/></svg>
        <span>AI Studio Copilot & Model Settings</span>
      </h3>
      <p style="font-size: 0.85rem; color: var(--text-muted);">
        Connect an AI model to automate notes formatting, KaTeX LaTeX math, SEO keyword tags, and table cleanup.
      </p>
    </div>
    <button type="button" class="btn btn-secondary" onclick="runConnectionTest()" id="btn-quick-test" style="border: 1px solid #7e22ce; color: #d8b4fe;">
      ⚡ Test Connection
    </button>
  </div>

  <!-- Live Connection Diagnostic Box -->
  <div id="test-result-box" style="display: none; margin-bottom: 1.5rem; padding: 1rem 1.25rem; border-radius: 8px; font-size: 0.875rem;"></div>

  <form method="POST" action="{{ url_for('route_save_ai_settings') }}">
    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">AI Provider *</label>
        <select name="provider" id="ai-provider-select" class="form-control" onchange="onProviderChange()">
          <option value="gemini" {% if ai.provider == 'gemini' %}selected{% endif %}>Google Gemini (Recommended - 100% Free via Google AI Studio)</option>
          <option value="groq" {% if ai.provider == 'groq' %}selected{% endif %}>Groq Cloud (Ultra-Fast LLaMA-3 Free Tier)</option>
          <option value="openai" {% if ai.provider == 'openai' %}selected{% endif %}>OpenAI (GPT-4o mini)</option>
          <option value="ollama" {% if ai.provider == 'ollama' %}selected{% endif %}>Local Ollama (100% Free, Offline on your PC)</option>
          <option value="custom" {% if ai.provider == 'custom' %}selected{% endif %}>Custom OpenAI-Compatible Endpoint</option>
        </select>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Gemini is free (15 requests/min) and excels at KaTeX formulas.</span>
      </div>

      <div class="form-group">
        <label class="form-label">Model Name *</label>
        <input type="text" name="model" id="ai-model-input" class="form-control" value="{{ ai.model or 'gemini-3.6-flash' }}" placeholder="e.g. gemini-3.6-flash" required>
        <div style="display: flex; gap: 0.35rem; margin-top: 0.4rem; flex-wrap: wrap;">
          <button type="button" class="badge" style="background:#1e293b; color:#93c5fd; border:none; cursor:pointer;" onclick="setModel('gemini-3.6-flash')">gemini-3.6-flash (Fastest &amp; Recommended)</button>
          <button type="button" class="badge" style="background:#1e293b; color:#93c5fd; border:none; cursor:pointer;" onclick="setModel('gemini-flash-lite-latest')">gemini-flash-lite</button>
          <button type="button" class="badge" style="background:#1e293b; color:#93c5fd; border:none; cursor:pointer;" onclick="setModel('gemini-3.8-flash')">gemini-3.8-flash</button>
          <button type="button" class="badge" style="background:#1e293b; color:#93c5fd; border:none; cursor:pointer;" onclick="setModel('llama-3.3-70b-versatile')">llama-3.3-70b (Groq)</button>
          <button type="button" class="badge" style="background:#1e293b; color:#93c5fd; border:none; cursor:pointer;" onclick="setModel('gpt-4o-mini')">gpt-4o-mini (OpenAI)</button>
          <button type="button" class="badge" style="background:#1e293b; color:#93c5fd; border:none; cursor:pointer;" onclick="setModel('llama3')">llama3 (Ollama)</button>
        </div>
      </div>
    </div>

    <div class="form-grid">
      <div class="form-group">
        <label class="form-label">API Key <span id="api-key-req-label">*</span></label>
        <div style="position: relative;">
          <input type="password" name="api_key" id="ai-api-key" class="form-control" value="{{ ai.api_key }}" placeholder="Paste API Key here...">
          <button type="button" onclick="toggleKeyVisibility()" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: transparent; border: none; color: #94a3b8; cursor: pointer; font-size: 0.8rem;">
            👁️ Show/Hide
          </button>
        </div>
        <span style="font-size: 0.75rem; color: var(--text-muted);" id="api-key-hint">Never shared publicly; stored locally in your workspace config.</span>
      </div>

      <div class="form-group" id="endpoint-group">
        <label class="form-label">Custom API Base URL (Optional for Ollama / Proxies)</label>
        <input type="text" name="custom_endpoint" id="ai-endpoint-input" class="form-control" value="{{ ai.custom_endpoint }}" placeholder="e.g. http://localhost:11434/v1">
        <span style="font-size: 0.75rem; color: var(--text-muted);">Leave empty for official Gemini / Groq / OpenAI clouds.</span>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Custom System Instructions / Persona Prompt</label>
      <textarea name="system_instructions" class="form-control" style="min-height: 100px; font-size: 0.85rem;">{{ ai.system_instructions }}</textarea>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Defines how the AI structures study notes, handles formulas, and organizes tables.</span>
    </div>

    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1.5rem;">
      <button type="submit" class="btn btn-primary" style="padding: 0.65rem 1.4rem;">
        <span>Save AI Settings</span>
      </button>
      <button type="button" class="btn btn-secondary" onclick="runConnectionTest()">
        <span>⚡ Test Connection</span>
      </button>
    </div>
  </form>
</div>

<!-- Step by Step Setup Guide Card -->
<div class="card" style="border-left: 4px solid #3b82f6;">
  <h4 style="font-size: 1rem; font-weight: 700; color: #93c5fd; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
    <span>📖 How to Get Your Free Google Gemini API Key in 30 Seconds</span>
  </h4>
  <ol style="margin-left: 1.25rem; font-size: 0.875rem; color: #cbd5e1; line-height: 1.8;">
    <li>Go to <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #60a5fa; font-weight: 600; text-decoration: underline;">Google AI Studio API Keys (aistudio.google.com) &rarr;</a> and log in with your Google account.</li>
    <li>Click the blue <strong>"Create API key"</strong> button.</li>
    <li>Copy your generated key, paste it into the <strong>API Key</strong> field above, and click <strong>Save AI Settings</strong>.</li>
    <li><em>Cost:</em> 100% Free! Google provides 15 requests per minute and 1,500 requests per day at zero charge.</li>
  </ol>
</div>

<!-- Interactive AI Playground Card -->
<div class="card">
  <h4 style="font-size: 1rem; font-weight: 700; color: #d8b4fe; margin-bottom: 0.75rem;">
    🧪 AI Copilot Playground (Live Sandbox)
  </h4>
  <p style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 1rem;">
    Test how AI processes your raw formulas, concepts, or tables before adding them to notes:
  </p>

  <div class="form-grid">
    <div>
      <label class="form-label">Input Raw Study Text:</label>
      <textarea id="playground-input" class="form-control" style="min-height: 180px; font-size: 0.85rem;" placeholder="e.g. Newton's second law states that F = m * a where F is net force in Newtons, m is mass in kg, and a is acceleration in m/s^2. Kinetic energy is KE = 1/2 m v^2."></textarea>
      <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
        <button type="button" class="btn btn-secondary" onclick="runPlaygroundTest('format')">✨ Test KaTeX Format</button>
        <button type="button" class="btn btn-secondary" onclick="runPlaygroundTest('quiz')">📝 Test MCQ Generator</button>
      </div>
    </div>

    <div>
      <label class="form-label">AI Rendered Output (KaTeX & Markdown):</label>
      <textarea id="playground-output" class="form-control" style="min-height: 180px; font-size: 0.85rem;" placeholder="Result will appear here..." readonly></textarea>
    </div>
  </div>
</div>

<script>
  function toggleKeyVisibility() {
    const keyInput = document.getElementById('ai-api-key');
    keyInput.type = keyInput.type === 'password' ? 'text' : 'password';
  }

  function setModel(modelName) {
    document.getElementById('ai-model-input').value = modelName;
  }

  function onProviderChange() {
    const provider = document.getElementById('ai-provider-select').value;
    const modelInput = document.getElementById('ai-model-input');
    const endpointInput = document.getElementById('ai-endpoint-input');
    const keyReq = document.getElementById('api-key-req-label');

    if (provider === 'gemini') {
      if (!modelInput.value || modelInput.value.includes('llama') || modelInput.value.includes('gpt')) {
        modelInput.value = 'gemini-3.6-flash';
      }
      keyReq.textContent = '*';
    } else if (provider === 'groq') {
      modelInput.value = 'llama-3.3-70b-versatile';
      keyReq.textContent = '*';
    } else if (provider === 'openai') {
      modelInput.value = 'gpt-4o-mini';
      keyReq.textContent = '*';
    } else if (provider === 'ollama') {
      modelInput.value = 'llama3';
      if (!endpointInput.value) endpointInput.value = 'http://localhost:11434/v1';
      keyReq.textContent = '(Not needed for local Ollama)';
    }
  }

  async function runConnectionTest() {
    const box = document.getElementById('test-result-box');
    box.style.display = 'block';
    box.style.background = '#1e293b';
    box.style.color = '#93c5fd';
    box.innerHTML = '<span>⚡ Testing AI connection... Sending ping request to model...</span>';

    try {
      const resp = await fetch('{{ url_for("route_api_ai_test") }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: document.getElementById('ai-provider-select').value,
          api_key: document.getElementById('ai-api-key').value,
          model: document.getElementById('ai-model-input').value,
          custom_endpoint: document.getElementById('ai-endpoint-input').value
        })
      });

      const data = await resp.json();
      if (data.success) {
        box.style.background = '#064e3b';
        box.style.border = '1px solid #059669';
        box.style.color = '#a7f3d0';
        box.innerHTML = `<strong>✅ AI Connection Successful! (${data.latency_ms}ms)</strong><br><span style="font-size: 0.8rem; opacity: 0.9;">Model <em>${data.model}</em> responded: "${data.reply}"</span>`;
      } else {
        box.style.background = '#450a0a';
        box.style.border = '1px solid #dc2626';
        box.style.color = '#fecaca';
        box.innerHTML = `<strong>❌ Connection Failed:</strong><br>${data.message}`;
      }
    } catch (err) {
      box.style.background = '#450a0a';
      box.style.border = '1px solid #dc2626';
      box.style.color = '#fecaca';
      box.innerHTML = `<strong>❌ Request Error:</strong> ${err.message}`;
    }
  }

  async function runPlaygroundTest(mode) {
    const input = document.getElementById('playground-input').value.trim();
    const output = document.getElementById('playground-output');
    if (!input) {
      alert('Please enter some text in the playground input.');
      return;
    }

    output.value = 'Processing with AI model...';
    try {
      const resp = await fetch('{{ url_for("route_api_ai_copilot") }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: mode === 'format' ? 'format_notes' : 'generate_quiz',
          content: input
        })
      });
      const data = await resp.json();
      if (data.success) {
        output.value = data.data;
      } else {
        output.value = 'Error: ' + data.message;
      }
    } catch (e) {
      output.value = 'Error: ' + e.message;
    }
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

    ai_cfg = config.get("ai", {})
    ai_provider = ai_cfg.get("provider", "gemini").capitalize()
    has_key = bool(ai_cfg.get("api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip())
    if ai_cfg.get("provider") == "ollama":
        ai_status_text = "🟢 Ollama (Local)"
    elif has_key:
        ai_status_text = f"🟢 {ai_provider} Ready"
    else:
        ai_status_text = "⚙️ Configure AI Key"

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
        ai_status_text=ai_status_text,
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
    pre_branch = request.args.get("branch", "")
    pre_ch = request.args.get("ch", "")

    note_meta = {}
    if pre_sub:
        note_meta["subject"] = pre_sub
    if pre_branch:
        note_meta["branch"] = pre_branch
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
    rel_parts = target_file.relative_to(NOTES_DIR).parts
    if not meta.get("branch") and len(rel_parts) >= 4:
        meta["branch"] = rel_parts[1]
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
    branch = request.form.get("branch", "").strip().lower()
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
            if branch:
                target_path = NOTES_DIR / subject / branch / chapter / f"{slug}.md"
            else:
                target_path = NOTES_DIR / subject / chapter / f"{slug}.md"
            if str(old_file.resolve()) != str(target_path.resolve()):
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
    if branch:
        frontmatter["branch"] = branch

    if branch:
        target_dir = NOTES_DIR / subject / branch / chapter
    else:
        target_dir = NOTES_DIR / subject / chapter
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{slug}.md"

    file_content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{content}\n"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(file_content)

    count = build_site()
    dest_name = f"{branch.title()} > {chapter.title()}" if branch else chapter.title()
    flash(f"Topic '{title}' saved successfully under {dest_name}! Rebuilt {count} topics with Clean URLs.", "success")
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
    branch_id = request.form.get("branch_id", "").strip().lower()

    if not ch_name or not ch_id:
        flash("Chapter name and slug are required.", "danger")
        return redirect(url_for("route_subjects"))

    config = load_config()
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            if branch_id and s.get("branches"):
                branch_match = next((b for b in s["branches"] if b["id"] == branch_id), None)
                if branch_match:
                    if "chapters" not in branch_match:
                        branch_match["chapters"] = []
                    if any(c["id"] == ch_id for c in branch_match["chapters"]):
                        flash(f"Chapter '{ch_id}' already exists in {branch_match['name']}.", "danger")
                        return redirect(url_for("route_subjects"))
                    branch_match["chapters"].append({
                        "id": ch_id,
                        "name": ch_name,
                        "description": ch_desc
                    })
                    break
            else:
                if "chapters" not in s:
                    s["chapters"] = []
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
    clean_url = f"/{sub_id}/{branch_id}/{ch_id}/" if branch_id else f"/{sub_id}/{ch_id}/"
    flash(f"Chapter '{ch_name}' added under {sub_id}! Clean URL created at {clean_url}.", "success")
    return redirect(url_for("route_subjects"))


@app.route("/subjects/<sub_id>/chapter/edit/<ch_id>")
def route_edit_chapter(sub_id, ch_id):
    config = load_config()
    sub = next((s for s in config.get("subjects", []) if s["id"] == sub_id), None)
    if not sub:
        flash("Subject not found.", "danger")
        return redirect(url_for("route_subjects"))

    target_ch = None
    target_branch = None

    if sub.get("branches"):
        for b in sub["branches"]:
            for c in b.get("chapters", []):
                if c["id"] == ch_id:
                    target_ch = c
                    target_branch = b
                    break
            if target_ch:
                break

    if not target_ch:
        target_ch = next((c for c in sub.get("chapters", []) if c["id"] == ch_id), None)

    if not target_ch:
        flash("Chapter not found.", "danger")
        return redirect(url_for("route_subjects"))

    return render_studio_view(
        CHAPTER_EDIT_HTML,
        active_tab="subjects",
        page_heading=f"Edit Chapter: {target_ch['name']}",
        sub=sub,
        branch=target_branch,
        target_chapter=target_ch
    )


@app.route("/subjects/<sub_id>/chapter/save/<ch_id>", methods=["POST"])
def route_save_chapter(sub_id, ch_id):
    ch_name = request.form.get("ch_name", "").strip()
    ch_desc = request.form.get("ch_desc", "").strip()
    branch_id = request.form.get("branch_id", "").strip().lower()

    config = load_config()
    for s in config.get("subjects", []):
        if s["id"] == sub_id:
            found = False
            if s.get("branches"):
                for b in s["branches"]:
                    if branch_id and b["id"] != branch_id:
                        continue
                    for c in b.get("chapters", []):
                        if c["id"] == ch_id:
                            c["name"] = ch_name
                            c["description"] = ch_desc
                            found = True
                            break
                    if found:
                        break
            if not found:
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
            if s.get("branches"):
                for b in s["branches"]:
                    b["chapters"] = [c for c in b.get("chapters", []) if c["id"] != ch_id]
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
    config["ads"]["header_ad_mobile"] = request.form.get("header_ad_mobile", "").strip()
    config["ads"]["in_article_ad"] = request.form.get("in_article_ad", "").strip()
    config["ads"]["in_article_ad_2"] = request.form.get("in_article_ad_2", "").strip()
    config["ads"]["sidebar_ad"] = request.form.get("sidebar_ad", "").strip()
    config["ads"]["native_ad"] = request.form.get("native_ad", "").strip()
    config["ads"]["footer_ad"] = request.form.get("footer_ad", "").strip()
    config["ads"]["footer_ad_mobile"] = request.form.get("footer_ad_mobile", "").strip()
    config["ads"]["social_bar_ad"] = request.form.get("social_bar_ad", "").strip()

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


# ==============================================================================
# AI Studio Copilot Routes
# ==============================================================================
@app.route("/ai")
def route_ai_settings():
    config = load_config()
    ai_cfg = config.get("ai", {})
    return render_studio_view(
        AI_SETTINGS_HTML,
        active_tab="ai",
        page_heading="AI Studio Copilot & Model Configuration",
        ai=ai_cfg
    )


@app.route("/ai/save", methods=["POST"])
def route_save_ai_settings():
    config = load_config()
    if "ai" not in config:
        config["ai"] = {}

    config["ai"]["provider"] = request.form.get("provider", "gemini").strip()
    config["ai"]["api_key"] = request.form.get("api_key", "").strip()
    config["ai"]["model"] = request.form.get("model", "gemini-3.6-flash").strip()
    config["ai"]["custom_endpoint"] = request.form.get("custom_endpoint", "").strip()
    config["ai"]["system_instructions"] = request.form.get("system_instructions", "").strip()

    save_config(config)
    flash("AI Copilot settings saved successfully!", "success")
    return redirect(url_for("route_ai_settings"))


@app.route("/api/ai/test", methods=["POST"])
def route_api_ai_test():
    payload = request.get_json(silent=True) or {}
    config = load_config()
    ai_cfg = config.get("ai", {})

    provider = payload.get("provider") or ai_cfg.get("provider", "gemini")
    api_key = payload.get("api_key") or ai_cfg.get("api_key", "")
    model = payload.get("model") or ai_cfg.get("model", "gemini-3.6-flash")
    endpoint = payload.get("custom_endpoint") or ai_cfg.get("custom_endpoint", "")

    t0 = time.time()
    success, reply = call_ai_model(
        "Ping test: reply with 'AI Copilot is online and ready for shrtnotes!'",
        provider=provider,
        api_key=api_key,
        model=model,
        custom_endpoint=endpoint
    )
    latency = int((time.time() - t0) * 1000)

    if success:
        return jsonify({
            "success": True,
            "latency_ms": latency,
            "model": model,
            "reply": reply
        })
    else:
        return jsonify({
            "success": False,
            "message": reply
        })


@app.route("/api/ai/copilot", methods=["POST"])
def route_api_ai_copilot():
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    content = data.get("content", "").strip()
    title = data.get("title", "").strip()
    subject = data.get("subject", "").strip()
    chapter = data.get("chapter", "").strip()

    config = load_config()
    ai_cfg = config.get("ai", {})
    api_key = ai_cfg.get("api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    provider = ai_cfg.get("provider", "gemini")

    if not api_key and provider != "ollama":
        if action == "format_notes" and content:
            formatted = offline_fallback_formatter(content)
            return jsonify({
                "success": True,
                "data": formatted,
                "offline": True,
                "message": "Basic offline formatting applied. Configure a free Gemini API key in AI Settings for full LaTeX intelligence."
            })
        return jsonify({
            "success": False,
            "message": "AI API key not configured. Please add your free Google Gemini API key under 'AI Copilot & Models' in the left menu."
        })

    if action == "format_notes":
        prompt = f"""You are an expert academic study notes formatter for a high-yield student revision site.
Transform the following raw study notes into clean, beautiful GitHub Flavored Markdown with proper KaTeX formulas and responsive tables.

FORMATTING RULES:
1. Use hierarchical Markdown headings (# for Main Section, ## for Subsections, ### for Concepts).
2. All mathematical, physical, or chemical equations MUST use valid KaTeX / LaTeX syntax:
   - Use inline math `$ ... $` for variables, small expressions, and symbols in text (e.g. `$x$`, `$E = mc^2$`).
   - Use block display `$$ ... $$` for standalone formulas, derivations, theorems, and definitions.
   - Never use broken LaTeX syntax like `\\( ... \\)` or `\\[ ... \\]` — always use `$...$` or `$$...$$`.
3. Highlight key terms, definitions, and takeaways using **bold**.
4. If there are tables or tabular data, format them into clean Markdown tables with header separators.
5. If there are step-by-step procedures or proofs, use clean numbered lists.
6. Keep the tone concise, clear, and high-yield. Do not include unnecessary conversational filler words.
7. Return ONLY the formatted Markdown content. Do not wrap the whole response in ```markdown code blocks.

RAW NOTES TO FORMAT:
{content}"""
        success, res = call_ai_model(prompt)
        if success:
            res = res.strip()
            if res.startswith("```markdown") and res.endswith("```"):
                res = res[11:-3].strip()
            elif res.startswith("```") and res.endswith("```"):
                res = res[3:-3].strip()
            return jsonify({"success": True, "data": res})
        else:
            fallback_res = offline_fallback_formatter(content)
            return jsonify({
                "success": True,
                "data": fallback_res,
                "warning": "Formatted using local LaTeX heuristics (Google Gemini was queued/busy)."
            })

    elif action == "generate_seo":
        subjects_summary = []
        for s in config.get("subjects", []):
            if s.get("branches"):
                for b in s["branches"]:
                    ch_list = [c["id"] for c in b.get("chapters", [])]
                    subjects_summary.append(f"Subject '{s['id']}', Branch '{b['id']}' ({b['name']}) -> Chapters: {ch_list}")
            else:
                ch_list = [c["id"] for c in s.get("chapters", [])]
                subjects_summary.append(f"Subject '{s['id']}' ({s['name']}) -> Chapters: {ch_list}")
        subjects_tree = "\n".join(subjects_summary)

        prompt = f"""You are an SEO and content classification specialist for an academic study notes platform.
Analyze the following note content and extract optimized metadata.

Available Subjects and Chapters in the site tree:
{subjects_tree}

Return a valid JSON object with these EXACT keys (no surrounding markdown, just pure JSON):
{{
  "title": "A crisp, search-optimized topic title (e.g. Fundamental Theorem of Calculus)",
  "slug": "url-friendly-slug-in-lowercase-hyphens-only (e.g. fundamental-theorem-calculus)",
  "excerpt": "A high-yield 1-2 sentence summary for Google search snippet (max 150 characters)",
  "tags": "5-8 comma-separated search keywords in lowercase (e.g. calculus, derivatives, integrals, limits)",
  "subject": "matching subject ID from the tree if found, else best match",
  "branch": "matching branch ID if subject has branches (e.g. organic, inorganic, or physical for chemistry), else empty string",
  "chapter": "matching chapter ID from the tree if found, else best match"
}}

NOTE TITLE: {title}
NOTE CONTENT:
{content}"""
        success, res = call_ai_model(prompt, json_mode=True)
        if success:
            try:
                clean_json = res.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                parsed = json.loads(clean_json.strip())
                return jsonify({"success": True, "data": parsed})
            except Exception as e:
                return jsonify({"success": False, "message": f"Failed to parse AI JSON response: {e}"})
        return jsonify({"success": False, "message": res})

    elif action == "fix_tables":
        prompt = f"""You are a Markdown table formatter. Format all tabular or structured data in the following text into standard GitHub Flavored Markdown tables.
Ensure column headers are clean and math expressions within cells use inline `$ ... $`.
Return ONLY the formatted markdown text with clean tables.

CONTENT:
{content}"""
        success, res = call_ai_model(prompt)
        if success:
            res = res.strip()
            if res.startswith("```markdown") and res.endswith("```"):
                res = res[11:-3].strip()
            elif res.startswith("```") and res.endswith("```"):
                res = res[3:-3].strip()
            return jsonify({"success": True, "data": res})
        return jsonify({"success": False, "message": res})

    elif action == "formula_sheet":
        prompt = f"""Extract all high-yield formulas and definitions from this topic into a concise "### 📌 Key Formulas & Summary" markdown block with KaTeX formatting (`$$...$$`).
Include brief notes on what each variable represents.
Return ONLY the markdown block.

TOPIC TITLE: {title}
CONTENT:
{content}"""
        success, res = call_ai_model(prompt)
        if success:
            res = res.strip()
            if res.startswith("```markdown") and res.endswith("```"):
                res = res[11:-3].strip()
            elif res.startswith("```") and res.endswith("```"):
                res = res[3:-3].strip()
            return jsonify({"success": True, "data": res})
        return jsonify({"success": False, "message": res})

    elif action == "generate_quiz":
        prompt = f"""Generate 3 high-yield multiple choice practice questions (MCQs) based on this study note.
Format each question in Markdown with 4 options (A, B, C, D).
Hide the correct answer and brief explanation inside a collapsible HTML `<details><summary><b>Reveal Answer & Explanation</b></summary>...</details>` block.
Return ONLY the Markdown starting with "### ✍️ Self-Check Practice Questions".

TOPIC TITLE: {title}
CONTENT:
{content}"""
        success, res = call_ai_model(prompt)
        if success:
            res = res.strip()
            if res.startswith("```markdown") and res.endswith("```"):
                res = res[11:-3].strip()
            elif res.startswith("```") and res.endswith("```"):
                res = res[3:-3].strip()
            return jsonify({"success": True, "data": res})
        return jsonify({"success": False, "message": res})

    elif action == "quick_draft":
        subjects_summary = []
        for s in config.get("subjects", []):
            if s.get("branches"):
                for b in s["branches"]:
                    ch_list = [c["id"] for c in b.get("chapters", [])]
                    subjects_summary.append(f"Subject '{s['id']}', Branch '{b['id']}' ({b['name']}) -> Chapters: {ch_list}")
            else:
                ch_list = [c["id"] for c in s.get("chapters", [])]
                subjects_summary.append(f"Subject '{s['id']}' ({s['name']}) -> Chapters: {ch_list}")
        subjects_tree = "\n".join(subjects_summary)

        prompt = f"""You are an expert academic curriculum creator.
Convert the following raw text/notes into a complete, structured study note.

Available Subjects and Chapters in the site tree:
{subjects_tree}

Return a valid JSON object with these EXACT keys:
{{
  "title": "A crisp, search-optimized topic title",
  "slug": "url-friendly-slug-in-lowercase-hyphens-only",
  "excerpt": "A high-yield 1-2 sentence summary for Google search results (max 150 characters)",
  "tags": "5-8 comma-separated search keywords in lowercase",
  "subject": "matching subject ID from the tree, or best match",
  "branch": "matching branch ID if subject has branches (e.g. organic, inorganic, or physical for chemistry), else empty string",
  "chapter": "matching chapter ID from the tree, or best match",
  "content": "Full formatted Markdown note with # headings, **bold** key terms, inline $...$ and block $$...$$ KaTeX formulas, and clean tables."
}}

RAW TEXT:
{content}"""
        success, res = call_ai_model(prompt, json_mode=True)
        if success:
            try:
                clean_json = res.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                parsed = json.loads(clean_json.strip())
                return jsonify({"success": True, "data": parsed})
            except Exception as e:
                return jsonify({"success": False, "message": f"Failed to parse AI draft JSON: {e}"})
        return jsonify({"success": False, "message": res})

    return jsonify({"success": False, "message": f"Unknown action: {action}"})


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
    reserved = ("notes", "design", "ads", "seo", "subjects", "pages", "deploy", "preview", "rebuild", "ai", "api")
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
