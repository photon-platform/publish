/* Interactive Full-Book Outline (standalone outline.html + slide-over drawer) */
(function () {
  'use strict';

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function resolveDocHref(docname) {
    var root = document.documentElement.getAttribute('data-content_root') || '';
    if (root && !root.endsWith('/')) root += '/';
    return root + docname + '.html';
  }

  function matchesCurrent(nodeDoc, activePage) {
    if (!activePage) return false;
    if (nodeDoc === activePage) return true;
    // Highlight primary unit row when viewing one of its sibling tracks (e.g. sec_01/de -> sec_01/index)
    if (nodeDoc.endsWith('/index')) {
      var dir = nodeDoc.slice(0, -6);
      if (activePage.startsWith(dir + '/') && activePage.slice(dir.length + 1).indexOf('/') === -1) {
        return true;
      }
    }
    return false;
  }

  function renderTreeHtml(nodes, activePage, depth) {
    if (!nodes || !nodes.length) return '';
    var cls = depth === 0 ? 'book-outline-list' : 'book-outline-sublist';
    var html = '<ul class="' + cls + '" data-depth="' + depth + '">';
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var hasKids = n.children && n.children.length > 0;
      var isCurrent = matchesCurrent(n.docname, activePage);
      var liCls = 'book-outline-item ' + (hasKids ? 'has-children' : 'is-leaf') + (isCurrent ? ' is-current' : '');
      var searchVal = ((n.title || '') + ' ' + (n.canonical_id || '') + ' ' + (n.folio || '')).toLowerCase();
      html += '<li class="' + liCls + '" data-docname="' + escapeHtml(n.docname) + '" data-search="' + escapeHtml(searchVal) + '">';
      html += '<div class="book-outline-row">';
      if (hasKids) {
        html += '<button type="button" class="book-outline-toggle" aria-expanded="true" aria-label="Toggle section">&#9662;</button>';
      } else {
        html += '<span class="book-outline-dot" aria-hidden="true">&middot;</span>';
      }
      html += '<a class="book-outline-title" href="' + escapeHtml(resolveDocHref(n.docname)) + '"' + (isCurrent ? ' aria-current="page"' : '') + '>' + escapeHtml(n.title || n.docname) + '</a>';
      if (n.tracks && n.tracks.length > 1) {
        html += '<span class="excerpt-tracks">';
        for (var j = 0; j < n.tracks.length; j++) {
          if (j > 0) html += '<span class="excerpt-track-sep">&middot;</span>';
          var tr = n.tracks[j];
          var trActive = tr.docname === activePage ? ' is-active' : '';
          html += '<a class="excerpt-track-link' + trActive + '" href="' + escapeHtml(resolveDocHref(tr.docname)) + '">' + escapeHtml(tr.label) + '</a>';
        }
        html += '</span>';
      }
      html += '</div>';
      if (hasKids) {
        html += renderTreeHtml(n.children, activePage, depth + 1);
      }
      html += '</li>';
    }
    html += '</ul>';
    return html;
  }

  function wireOutlineControls(container) {
    if (!container || container.dataset.outlineWired) return;
    container.dataset.outlineWired = '1';

    container.addEventListener('click', function (ev) {
      var btn = ev.target.closest('.book-outline-toggle');
      if (!btn) return;
      var li = btn.closest('.book-outline-item');
      if (!li) return;
      var collapsed = li.classList.toggle('is-collapsed');
      btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    });

    var expandBtn = container.querySelector('[data-outline-expand]');
    if (expandBtn) {
      expandBtn.addEventListener('click', function () {
        container.querySelectorAll('.book-outline-item.has-children').forEach(function (li) {
          li.classList.remove('is-collapsed');
          var b = li.querySelector(':scope > .book-outline-row > .book-outline-toggle');
          if (b) b.setAttribute('aria-expanded', 'true');
        });
      });
    }

    var collapseBtn = container.querySelector('[data-outline-collapse]');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        container.querySelectorAll('.book-outline-item.has-children').forEach(function (li) {
          li.classList.add('is-collapsed');
          var b = li.querySelector(':scope > .book-outline-row > .book-outline-toggle');
          if (b) b.setAttribute('aria-expanded', 'false');
        });
      });
    }

    var searchInput = container.querySelector('.book-outline-search');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        var q = searchInput.value.trim().toLowerCase();
        var items = container.querySelectorAll('.book-outline-item');
        if (!q) {
          items.forEach(function (li) {
            li.hidden = false;
          });
          return;
        }
        items.forEach(function (li) {
          li.hidden = true;
        });
        items.forEach(function (li) {
          var hay = li.getAttribute('data-search') || li.textContent.toLowerCase();
          if (hay.indexOf(q) !== -1) {
            li.hidden = false;
            var cur = li.parentElement;
            while (cur && cur !== container) {
              if (cur.classList && cur.classList.contains('book-outline-item')) {
                cur.hidden = false;
                cur.classList.remove('is-collapsed');
              }
              cur = cur.parentElement;
            }
          }
        });
      });
    }
  }

  function loadOutlineData(src, callback) {
    if (window.PHOTON_BOOK_OUTLINE && window.PHOTON_BOOK_OUTLINE.tree) {
      callback(window.PHOTON_BOOK_OUTLINE);
      return;
    }
    var script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = function () {
      callback(window.PHOTON_BOOK_OUTLINE || null);
    };
    script.onerror = function () {
      callback(null);
    };
    document.head.appendChild(script);
  }

  document.addEventListener('DOMContentLoaded', function () {
    // 1. Wire any standalone or embedded full-page outline
    document.querySelectorAll('[data-book-outline-root], .book-outline-embedded').forEach(wireOutlineControls);

    // 2. Wire slide-over Outline Drawer on Book Codex reading pages
    var article = document.querySelector('article.book-reading-pane[data-outline-src]');
    var drawer = document.getElementById('book-outline-drawer');
    if (!article || !drawer) return;

    var backdrop = article.querySelector('.book-outline-backdrop');
    var bodyEl = drawer.querySelector('.book-outline-drawer-body');
    var outlineSrc = article.getAttribute('data-outline-src');
    var activePage = article.getAttribute('data-pagename') || '';
    var loaded = false;

    function openDrawer() {
      drawer.hidden = false;
      if (backdrop) backdrop.hidden = false;
      document.body.classList.add('is-outline-open');
      article.querySelectorAll('[data-outline-toggle]').forEach(function (el) {
        el.setAttribute('aria-expanded', 'true');
      });

      if (!loaded) {
        bodyEl.innerHTML = '<p class="book-outline-loading">Loading outline&hellip;</p>';
        loadOutlineData(outlineSrc, function (data) {
          if (!data || !data.tree) {
            var fallback = article.getAttribute('data-outline-url') || '#';
            bodyEl.innerHTML = '<p class="book-outline-loading"><a href="' + escapeHtml(fallback) + '">Open full book outline &rarr;</a></p>';
            return;
          }
          loaded = true;
          bodyEl.innerHTML = renderTreeHtml(data.tree, activePage, 0);
          wireOutlineControls(drawer);
          var currentEl = bodyEl.querySelector('.book-outline-item.is-current');
          if (currentEl) {
            currentEl.scrollIntoView({ block: 'center', behavior: 'instant' });
          }
        });
      }
      var search = drawer.querySelector('.book-outline-search');
      if (search) {
        setTimeout(function () { search.focus(); }, 40);
      }
    }

    function closeDrawer() {
      drawer.hidden = true;
      if (backdrop) backdrop.hidden = true;
      document.body.classList.remove('is-outline-open');
      article.querySelectorAll('[data-outline-toggle]').forEach(function (el) {
        el.setAttribute('aria-expanded', 'false');
      });
    }

    article.querySelectorAll('[data-outline-toggle]').forEach(function (trigger) {
      trigger.addEventListener('click', function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button === 1) return;
        ev.preventDefault();
        if (drawer.hidden) {
          openDrawer();
        } else {
          closeDrawer();
        }
      });
    });

    article.querySelectorAll('[data-outline-close]').forEach(function (el) {
      el.addEventListener('click', closeDrawer);
    });

    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && !drawer.hidden) {
        closeDrawer();
      }
    });
  });
})();
