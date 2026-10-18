/**
 * shrtnotes - Client-Side Interactive Engine
 * ==========================================
 * Features:
 * - Theme Switcher (Light/Dark) with localStorage persistence
 * - Desktop Subjects Navigation Dropdown
 * - Search Icon Trigger & Expandable Search Overlay
 * - Intelligent Live Multi-Field Auto-Suggest Engine (Subject, Chapter, Topic, Tags, Content)
 * - Mobile Full Navigation Drawer
 * - Mobile Chapter Navigation Drawer
 * - Code Block Copy Buttons
 */

(function () {
  'use strict';

  // ===========================================================================
  // 1. Theme Management (Light / Dark Mode)
  // ===========================================================================
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

  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const current = htmlEl.getAttribute('data-theme') || 'light';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  // ===========================================================================
  // 2. Desktop Subjects Dropdown Menu
  // ===========================================================================
  const subjectsDropdownBtn = document.getElementById('subjects-dropdown-btn');
  const subjectsDropdownContainer = document.getElementById('subjects-dropdown-container');

  if (subjectsDropdownBtn && subjectsDropdownContainer) {
    subjectsDropdownBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = subjectsDropdownContainer.classList.contains('open');
      subjectsDropdownContainer.classList.toggle('open', !isOpen);
      subjectsDropdownBtn.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
    });

    document.addEventListener('click', (e) => {
      if (!subjectsDropdownContainer.contains(e.target)) {
        subjectsDropdownContainer.classList.remove('open');
        subjectsDropdownBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ===========================================================================
  // 3. Search Icon Trigger & Expandable Search Overlay
  // ===========================================================================
  const searchToggleBtn = document.getElementById('search-toggle-btn');
  const searchOverlay = document.getElementById('search-overlay');
  const searchBackdrop = document.getElementById('search-backdrop');
  const searchCloseBtn = document.getElementById('search-close-btn');
  const searchInput = document.getElementById('global-search-input');
  const searchSuggestions = document.getElementById('search-suggestions');

  let searchIndex = null;
  let isFetchingIndex = false;
  let activeSuggestionIndex = -1;

  // Determine root path for fetching search_index.json
  function getRootPath() {
    const cssLink = document.querySelector('link[rel="stylesheet"][href*="style.css"]');
    if (cssLink) {
      const href = cssLink.getAttribute('href');
      const idx = href.indexOf('static/css/style.css');
      if (idx !== -1) {
        return href.substring(0, idx);
      }
    }
    return '/';
  }

  async function loadSearchIndex() {
    if (searchIndex || isFetchingIndex) return;
    isFetchingIndex = true;
    try {
      const rootPath = getRootPath();
      const res = await fetch(`${rootPath}search_index.json`);
      if (res.ok) {
        searchIndex = await res.json();
      }
    } catch (err) {
      console.warn('Could not load search index:', err);
    } finally {
      isFetchingIndex = false;
    }
  }

  function openSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.add('open');
    if (searchBackdrop) searchBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
    loadSearchIndex();
    setTimeout(() => {
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }, 50);
  }

  function closeSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.remove('open');
    if (searchBackdrop) searchBackdrop.classList.remove('open');
    document.body.style.overflow = '';
    activeSuggestionIndex = -1;
    if (searchSuggestions) {
      searchSuggestions.style.display = 'none';
      searchSuggestions.innerHTML = '';
    }
  }

  if (searchToggleBtn) {
    searchToggleBtn.addEventListener('click', openSearch);
  }

  if (searchCloseBtn) {
    searchCloseBtn.addEventListener('click', closeSearch);
  }

  if (searchBackdrop) {
    searchBackdrop.addEventListener('click', closeSearch);
  }

  // Global Keyboard Shortcuts (Press '/' to search, 'Esc' to close)
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      openSearch();
    } else if (e.key === 'Escape') {
      if (searchOverlay && searchOverlay.classList.contains('open')) {
        closeSearch();
      }
      if (subjectsDropdownContainer) {
        subjectsDropdownContainer.classList.remove('open');
      }
    }
  });

  // ===========================================================================
  // 4. Intelligent Live Multi-Field Auto-Suggest Engine
  // ===========================================================================
  function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function highlightMatches(text, tokens) {
    if (!tokens.length) return text;
    let safeText = text;
    tokens.forEach(tok => {
      if (!tok) return;
      const regex = new RegExp(`(${escapeRegExp(tok)})`, 'gi');
      safeText = safeText.replace(regex, '<mark>$1</mark>');
    });
    return safeText;
  }

  function performSearch(query) {
    if (!searchIndex || !query.trim()) {
      if (searchSuggestions) {
        searchSuggestions.style.display = 'none';
        searchSuggestions.innerHTML = '';
      }
      return;
    }

    const rawTokens = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const rootPath = getRootPath();

    const scored = [];

    searchIndex.forEach(item => {
      const titleLower = (item.title || '').toLowerCase();
      const subjectLower = (item.subject_name || item.subject || '').toLowerCase();
      const chapterLower = (item.chapter_name || item.chapter || '').toLowerCase();
      const excerptLower = (item.excerpt || '').toLowerCase();
      const contentLower = (item.content || '').toLowerCase();
      const tagsList = Array.isArray(item.tags) ? item.tags : [];
      const tagsLower = tagsList.map(t => String(t).toLowerCase());

      let score = 0;
      let allTokensMatch = true;

      rawTokens.forEach(token => {
        let tokenFound = false;

        if (titleLower.includes(token)) {
          score += 100;
          if (titleLower.startsWith(token)) score += 50;
          tokenFound = true;
        }

        if (tagsLower.some(t => t.includes(token))) {
          score += 60;
          tokenFound = true;
        }

        if (chapterLower.includes(token)) {
          score += 40;
          tokenFound = true;
        }

        if (subjectLower.includes(token)) {
          score += 30;
          tokenFound = true;
        }

        if (excerptLower.includes(token) || contentLower.includes(token)) {
          score += 15;
          tokenFound = true;
        }

        if (!tokenFound) {
          allTokensMatch = false;
        }
      });

      if (allTokensMatch && score > 0) {
        scored.push({ item, score });
      }
    });

    // Sort by relevance score descending
    scored.sort((a, b) => b.score - a.score);
    const topMatches = scored.slice(0, 8).map(s => s.item);

    renderSuggestions(topMatches, rawTokens, rootPath, query);
  }

  function renderSuggestions(matches, tokens, rootPath, originalQuery) {
    if (!searchSuggestions) return;

    if (matches.length === 0) {
      searchSuggestions.innerHTML = `
        <div class="search-empty">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 0.5rem; opacity: 0.6;"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/><line x1="11" x2="11" y1="8" y2="14"/></svg>
          <div>No study notes found matching "<strong>${originalQuery}</strong>".</div>
          <div style="font-size: 0.8rem; margin-top: 0.25rem;">Try searching by subject (e.g. Physics), chapter (e.g. Calculus), or concept keywords.</div>
        </div>
      `;
      searchSuggestions.style.display = 'block';
      activeSuggestionIndex = -1;
      return;
    }

    let html = '';
    matches.forEach((item, index) => {
      // Build clean URL ending with slash
      const noteRel = `${item.subject}/${item.chapter}/${item.slug}/`;
      const cleanHref = `${rootPath}${noteRel}`;
      const highlightedTitle = highlightMatches(item.title, tokens);

      const tagHtml = (item.tags || []).slice(0, 3).map(tag => {
        return `<span class="search-tag-chip">#${tag}</span>`;
      }).join('');

      html += `
        <a href="${cleanHref}" class="search-suggestion-item" data-index="${index}">
          <div class="search-suggestion-top">
            <span class="search-suggestion-crumb">
              <span>${item.subject_name}</span>
              <span>&rsaquo;</span>
              <span>${item.chapter_name}</span>
            </span>
            <span class="search-suggestion-time">${item.reading_time || 2} min read</span>
          </div>
          <div class="search-suggestion-title">${highlightedTitle}</div>
          <div class="search-suggestion-snippet">${item.excerpt || item.content || ''}</div>
          ${tagHtml ? `<div class="search-suggestion-tags">${tagHtml}</div>` : ''}
        </a>
      `;
    });

    searchSuggestions.innerHTML = html;
    searchSuggestions.style.display = 'block';
    activeSuggestionIndex = -1;
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value;
      if (!searchIndex) {
        loadSearchIndex().then(() => performSearch(query));
      } else {
        performSearch(query);
      }
    });

    // Keyboard Navigation within Suggestions
    searchInput.addEventListener('keydown', (e) => {
      const items = searchSuggestions ? searchSuggestions.querySelectorAll('.search-suggestion-item') : [];
      if (!items.length) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
        updateActiveSuggestion(items);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
        updateActiveSuggestion(items);
      } else if (e.key === 'Enter') {
        if (activeSuggestionIndex >= 0 && items[activeSuggestionIndex]) {
          e.preventDefault();
          items[activeSuggestionIndex].click();
        }
      }
    });
  }

  function updateActiveSuggestion(items) {
    items.forEach((item, idx) => {
      if (idx === activeSuggestionIndex) {
        item.classList.add('highlighted');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('highlighted');
      }
    });
  }

  // ===========================================================================
  // 5. Mobile Full Navigation Drawer
  // ===========================================================================
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const mobileNavDrawer = document.getElementById('mobile-nav-drawer');
  const mobileNavClose = document.getElementById('mobile-nav-close');

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

  // ===========================================================================
  // 6. Mobile Chapter Navigation Drawer for Notes
  // ===========================================================================
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

  // ===========================================================================
  // 7. Code Block Copy Buttons
  // ===========================================================================
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

  // ===========================================================================
  // 8. Browse All Topics Toggle & Smooth Scroll
  // ===========================================================================
  const browseAllBtn = document.getElementById('browse-all-topics-btn');
  if (browseAllBtn) {
    browseAllBtn.addEventListener('click', (e) => {
      const extraRows = document.querySelectorAll('.note-row-extra');
      if (extraRows.length > 0) {
        const firstHidden = Array.from(extraRows).some(r => r.style.display === 'none' || getComputedStyle(r).display === 'none');
        if (firstHidden) {
          extraRows.forEach(row => {
            row.style.display = 'flex';
          });
          const total = browseAllBtn.getAttribute('data-total') || 'All';
          browseAllBtn.innerHTML = `
            <span>Explore All Subjects Above &uarr;</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>
          `;
          return;
        }
      }
      // If already shown or no extra rows, smooth scroll to subjects grid
      const subjectsTarget = document.getElementById('subjects-section') || document.getElementById('subjects-grid');
      if (subjectsTarget) {
        subjectsTarget.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }
})();
