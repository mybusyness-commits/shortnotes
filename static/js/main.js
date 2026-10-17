/**
 * shrtnotes - Client-Side Interactive Engine
 * Handles:
 * - Theme switcher (Light/Dark) with persistence
 * - Mobile full navigation drawer with backdrop
 * - Mobile note chapter navigation drawer
 * - Interactive instant search filtering
 * - Code block copy buttons
 */

(function () {
  'use strict';

  // 1. Theme Management
  const THEME_KEY = 'shrtnotes_theme';
  const htmlEl = document.documentElement;
  const themeToggleBtn = document.getElementById('theme-toggle-btn');

  function getPreferredTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    htmlEl.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    updateThemeIcon(theme);
  }

  function updateThemeIcon(theme) {
    if (!themeToggleBtn) return;
    const sunIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`;
    const moonIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`;
    themeToggleBtn.innerHTML = theme === 'dark' ? sunIcon : moonIcon;
    themeToggleBtn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
  }

  // Initialize theme
  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const current = htmlEl.getAttribute('data-theme') || 'light';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  // 2. Mobile Full Navigation Drawer
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const mobileNavDrawer = document.getElementById('mobile-nav-drawer');
  const mobileNavClose = document.getElementById('mobile-nav-close');
  const mobileBackdrop = document.getElementById('mobile-backdrop');

  function openMobileNav() {
    if (mobileNavDrawer && mobileBackdrop) {
      mobileNavDrawer.classList.add('open');
      mobileBackdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeMobileNav() {
    if (mobileNavDrawer && mobileBackdrop) {
      mobileNavDrawer.classList.remove('open');
      mobileBackdrop.classList.remove('open');
      document.body.style.overflow = '';
    }
    const contentSidebar = document.getElementById('content-sidebar');
    if (contentSidebar) {
      contentSidebar.classList.remove('mobile-open');
    }
  }

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', openMobileNav);
  }

  if (mobileNavClose) {
    mobileNavClose.addEventListener('click', closeMobileNav);
  }

  if (mobileBackdrop) {
    mobileBackdrop.addEventListener('click', closeMobileNav);
  }

  // 3. Mobile Chapter Navigation Toggle for Notes
  const mobileChapterBtn = document.getElementById('mobile-chapter-toggle-btn');
  const contentSidebar = document.getElementById('content-sidebar');
  const sidebarCloseBtn = document.getElementById('sidebar-close-btn');

  if (mobileChapterBtn && contentSidebar) {
    mobileChapterBtn.addEventListener('click', () => {
      contentSidebar.classList.add('mobile-open');
      if (mobileBackdrop) {
        mobileBackdrop.classList.add('open');
        document.body.style.overflow = 'hidden';
      }
    });
  }

  if (sidebarCloseBtn && contentSidebar) {
    sidebarCloseBtn.addEventListener('click', () => {
      contentSidebar.classList.remove('mobile-open');
      if (mobileBackdrop) {
        mobileBackdrop.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  }

  // 4. Client-Side Instant Search Filter
  const searchInput = document.getElementById('global-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', function (e) {
      const query = e.target.value.toLowerCase().trim();
      const noteRows = document.querySelectorAll('.note-row');
      noteRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (!query || text.includes(query)) {
          row.style.display = 'flex';
        } else {
          row.style.display = 'none';
        }
      });
    });
  }

  // 5. Code Block Copy Buttons
  document.querySelectorAll('.prose pre').forEach(pre => {
    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-copy-btn';
    copyBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`;
    copyBtn.title = "Copy code";
    copyBtn.style.cssText = "position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 4px 6px; border-radius: 4px; cursor: pointer;";
    pre.style.position = 'relative';
    pre.appendChild(copyBtn);

    copyBtn.addEventListener('click', () => {
      const code = pre.querySelector('code')?.innerText || pre.innerText;
      navigator.clipboard.writeText(code).then(() => {
        copyBtn.innerText = "Copied!";
        setTimeout(() => {
          copyBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`;
        }, 1500);
      });
    });
  });
})();
