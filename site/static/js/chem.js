/**
 * shrtnotes - Universal Chemical Structure & SMILES Vector Renderer
 * =================================================================
 * Uses SmilesDrawer to render high-contrast, theme-aware vector SVGs
 * for chemical molecules and skeletal structures.
 */

(function () {
  'use strict';

  function getCurrentTheme() {
    var theme = document.documentElement.getAttribute('data-theme') || 'dark';
    return theme === 'light' ? 'light' : 'dark';
  }

  function getDrawerOptions(theme) {
    var isDark = theme === 'dark';
    return {
      width: 280,
      height: 190,
      bondThickness: 1.6,
      bondLength: 20,
      shortBondLength: 0.85,
      bondSpacing: 3.5,
      atomVisualization: 'default',
      isomeric: true,
      explicitHydrogens: true,
      terminalCarbons: true,
      padding: 12,
      themes: {
        dark: {
          C: '#f1f5f9',
          O: '#f87171',
          N: '#60a5fa',
          F: '#34d399',
          CL: '#4ade80',
          BR: '#fb923c',
          I: '#c084fc',
          P: '#facc15',
          S: '#f59e0b',
          B: '#f472b6',
          SI: '#a78bfa',
          H: '#94a3b8',
          BACKGROUND: 'transparent'
        },
        light: {
          C: '#0f172a',
          O: '#dc2626',
          N: '#1d4ed8',
          F: '#059669',
          CL: '#15803d',
          BR: '#c2410c',
          I: '#7e22ce',
          P: '#b45309',
          S: '#b45309',
          B: '#be185d',
          SI: '#6d28d9',
          H: '#475569',
          BACKGROUND: 'transparent'
        }
      }
    };
  }

  function renderAllMolecules() {
    if (typeof SmilesDrawer === 'undefined') {
      return;
    }

    var targets = document.querySelectorAll('.molecule-render');
    if (!targets.length) return;

    var theme = getCurrentTheme();
    var options = getDrawerOptions(theme);
    var svgDrawer = new SmilesDrawer.SvgDrawer(options);

    targets.forEach(function (container) {
      var smiles = container.getAttribute('data-smiles');
      if (!smiles) return;

      container.innerHTML = '';
      var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgEl.setAttribute('viewBox', '0 0 280 190');
      svgEl.style.width = '100%';
      svgEl.style.height = 'auto';
      svgEl.style.maxHeight = '200px';
      svgEl.style.display = 'block';
      container.appendChild(svgEl);

      SmilesDrawer.parse(
        smiles,
        function (tree) {
          try {
            svgDrawer.draw(tree, svgEl, theme, false);
          } catch (e) {
            console.warn('Smiles draw error:', e);
          }
        },
        function (err) {
          console.warn('Smiles syntax error for:', smiles, err);
          container.innerHTML = '<span style="color:var(--text-muted); font-size:0.8rem; font-family:monospace; padding:0.5rem; display:block;">[Structure: ' + smiles + ']</span>';
        }
      );
    });
  }

  // Initial draw when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderAllMolecules);
  } else {
    renderAllMolecules();
  }

  // Redraw automatically on dark/light mode toggle
  var themeObserver = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      if (m.type === 'attributes' && m.attributeName === 'data-theme') {
        renderAllMolecules();
      }
    });
  });
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  window.renderAllMolecules = renderAllMolecules;
})();
