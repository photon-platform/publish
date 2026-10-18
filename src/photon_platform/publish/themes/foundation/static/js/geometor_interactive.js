/**
 * GeometorInteractive / EuclidInteractive
 * Shared interactive SVG inlining and graphic-scoped Geometor highlighting engine
 * for both folio_review and Sphinx foundation book pages.
 */
(function (window, document) {
  'use strict';

  const EuclidInteractive = {
    activeHighlights: new Set(),
    svgRefMap: new Map(), // key ("<folio>.<gid>:<canonical_geometor_id>") -> Set of SVG elements

    getDefaultFolioId() {
      if (typeof window.FOLIO_ID === 'string' && window.FOLIO_ID) {
        return window.FOLIO_ID;
      }
      const milestone = document.querySelector('[data-folio]');
      if (milestone) {
        return milestone.getAttribute('data-folio') || '0000';
      }
      return '0000';
    },

    getRootContainer() {
      return (
        document.getElementById('mdView-rendered') ||
        document.querySelector('.folio-book-page') ||
        document.querySelector('article .content') ||
        document.querySelector('main') ||
        document.body
      );
    },

    init() {
      this.inlineFiguresInTranscription();
      this.buildSvgIndex();
      this.bindTextElements();
      this.bindSvgElements();
    },

    // Normalize graphic ID to "<folio>.<gid>" (e.g. "g1" -> "0255.g1")
    normalizeGraphicId(gid) {
      const raw = (gid || '').trim();
      const folioId = this.getDefaultFolioId();
      if (!raw) return `${folioId}.g1`;
      if (raw.includes('.')) return raw;
      return `${folioId}.${raw}`;
    },

    // Parse a Geometor typed expression (with optional "<gid>:" prefix) into:
    // { graphicId, type, points, keys: [scopedKey, ...], pointKeys: [scopedPtKey, ...] }
    parseGeometorRef(rawStr, defaultGraphicId) {
      let str = (rawStr || '').trim();
      if (!str) return null;

      let graphicId = this.normalizeGraphicId(defaultGraphicId);
      const colonIdx = str.indexOf(':');
      if (colonIdx !== -1) {
        const prefix = str.slice(0, colonIdx).trim();
        str = str.slice(colonIdx + 1).trim();
        if (prefix) graphicId = this.normalizeGraphicId(prefix);
      }

      if (!str) return null;

      const extractPts = (inner) => {
        const tokens = inner.trim().split(/[\s,]+/).filter(Boolean);
        if (tokens.length === 1 && /^[A-Z]{2,}$/.test(tokens[0])) {
          return tokens[0].split('');
        }
        return tokens;
      };

      const makeScoped = (expr) => `${graphicId}:${expr}`;
      const keys = new Set();
      let points = [];
      let type = 'unknown';

      // 1. Wedge / Angle with circle prefix: ( A B )< B A C >
      const fullWedgeMatch = str.match(/^\(([^)]+)\)\s*<([^>]+)>$/);
      // 2. Wedge / Angle / Arc shorthand: < B A C )
      const shortWedgeMatch = !fullWedgeMatch && str.match(/^<([^)]+)\)$/);
      // 3. Line: [ A B ]
      const lineMatch = str.match(/^\[([^\]]+)\]$/);
      // 4. Segment / Section: / A B / or } A C B {
      const segMatch = str.match(/^\/([^/]+)\/$/) || str.match(/^\}([^{]+)\{$/);
      // 5. Circle: ( A B ) or ( B C D )
      const circleMatch = !fullWedgeMatch && str.match(/^\(([^)]+)\)$/);
      // 6. Polygon: < A B C >
      const polyMatch = !fullWedgeMatch && !shortWedgeMatch && str.match(/^<([^>]+)>$/);

      if (fullWedgeMatch) {
        type = 'wedge';
        const cPts = extractPts(fullWedgeMatch[1]);
        const aPts = extractPts(fullWedgeMatch[2]);
        points = Array.from(new Set([...cPts, ...aPts]));
        const cPart = `( ${cPts.join(' ')} )`;
        keys.add(makeScoped(`${cPart}< ${aPts.join(' ')} >`));
        keys.add(makeScoped(`< ${aPts.join(' ')} )`));
        if (aPts.length === 3) {
          const revA = [aPts[2], aPts[1], aPts[0]];
          keys.add(makeScoped(`${cPart}< ${revA.join(' ')} >`));
          keys.add(makeScoped(`< ${revA.join(' ')} )`));
        }
      } else if (shortWedgeMatch) {
        type = 'wedge';
        points = extractPts(shortWedgeMatch[1]);
        keys.add(makeScoped(`< ${points.join(' ')} )`));
        if (points.length === 3) {
          const rev = [points[2], points[1], points[0]];
          keys.add(makeScoped(`< ${rev.join(' ')} )`));
        } else if (points.length === 2) {
          keys.add(makeScoped(`< ${[points[1], points[0]].join(' ')} )`));
        }
      } else if (lineMatch) {
        type = 'line';
        points = extractPts(lineMatch[1]);
        keys.add(makeScoped(`[ ${points.join(' ')} ]`));
        keys.add(makeScoped(`[ ${[...points].reverse().join(' ')} ]`));
      } else if (segMatch) {
        points = extractPts(segMatch[1]);
        type = points.length >= 3 ? 'section' : 'segment';
        keys.add(makeScoped(`/ ${points.join(' ')} /`));
        keys.add(makeScoped(`/ ${[...points].reverse().join(' ')} /`));
      } else if (circleMatch) {
        type = 'circle';
        points = extractPts(circleMatch[1]);
        if (points.length === 2) {
          keys.add(makeScoped(`( ${points.join(' ')} )`));
        } else if (points.length === 3) {
          const [a, b, c] = points;
          [
            [a, b, c], [a, c, b], [b, a, c], [b, c, a], [c, a, b], [c, b, a]
          ].forEach((p) => keys.add(makeScoped(`( ${p.join(' ')} )`)));
        } else {
          keys.add(makeScoped(`( ${points.join(' ')} )`));
          keys.add(makeScoped(`( ${[...points].reverse().join(' ')} )`));
        }
      } else if (polyMatch) {
        type = 'polygon';
        points = extractPts(polyMatch[1]);
        if (points.length === 3) {
          const [a, b, c] = points;
          [
            [a, b, c], [a, c, b], [b, a, c], [b, c, a], [c, a, b], [c, b, a]
          ].forEach((p) => keys.add(makeScoped(`< ${p.join(' ')} >`)));
        } else if (points.length > 3) {
          const n = points.length;
          for (let i = 0; i < n; i++) {
            const rot = [...points.slice(i), ...points.slice(0, i)];
            keys.add(makeScoped(`< ${rot.join(' ')} >`));
            const rev = [...rot].reverse();
            keys.add(makeScoped(`< ${rev.join(' ')} >`));
          }
        } else {
          keys.add(makeScoped(`< ${points.join(' ')} >`));
          keys.add(makeScoped(`< ${[...points].reverse().join(' ')} >`));
        }
      } else {
        const clean = str.replace(/[^A-Za-z0-9]/g, '').trim();
        if (!clean) return null;
        if (clean.length === 1 || /^[A-Z]\d+$/.test(clean)) {
          type = 'point';
          points = [clean];
          keys.add(makeScoped(clean));
        } else if (clean.length === 2) {
          type = 'legacy2';
          points = [clean[0], clean[1]];
          keys.add(makeScoped(clean));
          keys.add(makeScoped(clean[1] + clean[0]));
          keys.add(makeScoped(`/ ${clean[0]} ${clean[1]} /`));
          keys.add(makeScoped(`/ ${clean[1]} ${clean[0]} /`));
        } else if (clean.length === 3) {
          type = 'legacy3';
          points = clean.split('');
          const [a, b, c] = points;
          [a + b + c, a + c + b, b + a + c, b + c + a, c + a + b, c + b + a].forEach((p) =>
            keys.add(makeScoped(p))
          );
        } else {
          type = 'legacyN';
          points = clean.split('');
          keys.add(makeScoped(clean));
        }
      }

      const pointKeys = points.map((pt) => makeScoped(pt));
      return {
        graphicId,
        type,
        points,
        keys: Array.from(keys),
        pointKeys,
      };
    },

    // Inlines Vector SVGs in transcription / book page container
    inlineFiguresInTranscription() {
      const container = this.getRootContainer();
      const folioGraphics = window.FOLIO_GRAPHICS;
      if (!container || !Array.isArray(folioGraphics) || folioGraphics.length === 0) return;

      const imgs = Array.from(container.querySelectorAll('img:not(.woodcut-img)'));
      const volumeId = window.VOLUME_ID || '';
      const sectionPath = window.FOLIO_SECTION_PATH || '';

      folioGraphics.forEach((g) => {
        if (!g.svg_exists || !g.svg_content) return;

        let targetImg = imgs.find((img) => {
          const src = img.getAttribute('src') || '';
          return src.includes(g.file) || (g.svg_file && src.includes(g.svg_file)) || src.includes(g.id);
        });

        if (!targetImg && imgs.length === 1 && folioGraphics.length === 1) {
          targetImg = imgs[0];
        }

        if (targetImg) {
          const fullGid = this.normalizeGraphicId(g.id);
          const parentBlock = targetImg.closest('figure.photon-picture, figure, p');
          const figureDiv = document.createElement('div');
          figureDiv.className = 'euclid-figure-container';
          figureDiv.setAttribute('data-graphic-id', g.id);
          figureDiv.setAttribute('data-full-graphic-id', fullGid);
          figureDiv.innerHTML = `
            <div class="figure-svg-wrapper" id="fig-view-svg-${g.id}">
              ${g.svg_content}
            </div>
            ${g.caption ? `<div class="figure-caption">${g.caption}</div>` : ''}
          `;

          const svgEl = figureDiv.querySelector('svg');
          if (svgEl) {
            svgEl.classList.add('euclid-graphic');
            svgEl.setAttribute('data-graphic-id', fullGid);
            svgEl.setAttribute('data-short-gid', g.id);
          }

          if (parentBlock && parentBlock.querySelectorAll('img').length === 1) {
            parentBlock.replaceWith(figureDiv);
          } else {
            targetImg.replaceWith(figureDiv);
          }
        }
      });
    },

    // Indexes all SVG elements by their graphic-scoped Geometor ID and aliases
    buildSvgIndex() {
      this.svgRefMap.clear();
      const svgs = document.querySelectorAll('svg.euclid-graphic, figure.photon-svg svg');

      svgs.forEach((svg) => {
        svg.classList.add('euclid-graphic');
        const fullGid = this.normalizeGraphicId(
          svg.getAttribute('data-graphic-id') ||
            svg.closest('.euclid-figure-container')?.getAttribute('data-full-graphic-id') ||
            'g1'
        );
        svg.setAttribute('data-graphic-id', fullGid);

        const candidates = svg.querySelectorAll('[data-ref], [id]');
        candidates.forEach((el) => {
          if (el.tagName.toLowerCase() === 'g' && !el.hasAttribute('data-ref')) return;
          if (el.tagName.toLowerCase() === 'defs' || el.closest('defs')) return;

          const rawRef = (el.getAttribute('data-ref') || el.getAttribute('id') || '').trim();
          if (!rawRef) return;
          if (
            [
              'elements',
              'graphics',
              'highlights',
              'points',
              'labels',
              'construction',
              'geometry',
            ].includes(rawRef)
          ) {
            return;
          }

          const refsToIndex = [rawRef];
          const aliases = (el.getAttribute('data-aliases') || '').trim();
          if (aliases) {
            aliases
              .split(/[|;]/)
              .map((s) => s.trim())
              .filter(Boolean)
              .forEach((a) => refsToIndex.push(a));
          }

          refsToIndex.forEach((r) => {
            const parsed = this.parseGeometorRef(r, fullGid);
            if (parsed) {
              parsed.keys.forEach((k) => this.registerRef(k, el));
            }
          });
        });
      });
    },

    registerRef(key, element) {
      if (!this.svgRefMap.has(key)) {
        this.svgRefMap.set(key, new Set());
      }
      this.svgRefMap.get(key).add(element);
    },

    // Find matching SVG elements for a graphic-scoped Geometor reference
    getSvgElementsForRef(rawRef, defaultGraphicId) {
      const parsed = this.parseGeometorRef(rawRef, defaultGraphicId);
      if (!parsed) return { primary: [], secondary: [] };

      const rawMatches = [];
      parsed.keys.forEach((k) => {
        if (this.svgRefMap.has(k)) {
          this.svgRefMap.get(k).forEach((el) => rawMatches.push(el));
        }
      });

      const hasVisiblePrimary = rawMatches.some(
        (el) => !el.closest('#highlights') && !el.classList.contains('geom-overlay')
      );
      const matches = new Set();
      rawMatches.forEach((el) => {
        if (
          hasVisiblePrimary &&
          (el.closest('#highlights') || el.classList.contains('geom-overlay'))
        ) {
          const tag = el.tagName.toLowerCase();
          const isRegionOrWedge =
            tag === 'polygon' ||
            el.classList.contains('wedge') ||
            el.classList.contains('angle') ||
            el.classList.contains('geom-polygon');
          if (!isRegionOrWedge) return;
        }
        matches.add(el);
      });

      // Secondary highlight for constituent points/labels within the same graphic
      const secondary = new Set();
      if (parsed.type !== 'point' && parsed.pointKeys.length > 0) {
        parsed.pointKeys.forEach((pk) => {
          if (this.svgRefMap.has(pk)) {
            this.svgRefMap.get(pk).forEach((el) => {
              if (!matches.has(el) && !el.closest('#highlights')) secondary.add(el);
            });
          }
        });
      }

      return {
        primary: Array.from(matches),
        secondary: Array.from(secondary),
      };
    },

    // Infer target graphic ID and Geometor type for untagged KaTeX math from surrounding context
    inferContextualRef(kel, token) {
      const folioId = this.getDefaultFolioId();
      const explicitScope = kel.closest('[data-graphic]')?.getAttribute('data-graphic');
      const targetGid = explicitScope ? this.normalizeGraphicId(explicitScope) : `${folioId}.g1`;

      let prevText = '';
      let node = kel.previousSibling;
      while (node && prevText.length < 60) {
        prevText = (node.textContent || '') + ' ' + prevText;
        node = node.previousSibling;
      }
      prevText = prevText.toLowerCase();

      const pts = token.split('').join(' ');
      const candidates = [];

      if (token.length === 1) {
        candidates.push(`${targetGid}:${token}`);
      } else if (token.length === 2) {
        if (/\b(produced)\b/.test(prevText)) {
          candidates.push(`${targetGid}:[ ${pts} ]`);
        }
        candidates.push(`${targetGid}:/ ${pts} /`);
        candidates.push(`${targetGid}:${token}`);
      } else if (token.length === 3) {
        if (/\b(angle|angles)\b/.test(prevText)) {
          candidates.push(`${targetGid}:< ${pts} )`);
        } else if (/\b(circle|circles|semicircle)\b/.test(prevText)) {
          candidates.push(`${targetGid}:( ${pts} )`);
        } else if (/\b(circumference|arc)\b/.test(prevText)) {
          candidates.push(`${targetGid}:< ${pts} )`);
          candidates.push(`${targetGid}:( ${pts} )`);
        } else if (/\b(triangle|triangles)\b/.test(prevText)) {
          candidates.push(`${targetGid}:< ${pts} >`);
        }
        candidates.push(`${targetGid}:< ${pts} >`);
        candidates.push(`${targetGid}:( ${pts} )`);
        candidates.push(`${targetGid}:< ${pts} )`);
        candidates.push(`${targetGid}:/ ${pts} /`);
        candidates.push(`${targetGid}:${token}`);
      } else if (token.length >= 4) {
        candidates.push(`${targetGid}:< ${pts} >`);
        candidates.push(`${targetGid}:( ${pts} )`);
        candidates.push(`${targetGid}:${token}`);
      }

      for (const cand of candidates) {
        const { primary } = this.getSvgElementsForRef(cand, targetGid);
        if (primary.length > 0) return cand;
      }
      return null;
    },

    // Binds explicit <span data-ref="..."> elements and contextual KaTeX fallback
    bindTextElements() {
      const container = this.getRootContainer();
      if (!container) return;

      const folioId = this.getDefaultFolioId();

      // 1. Bind explicit <span data-ref="<folio>.<gid>:<geometor_id>"> wrappers
      const explicitSpans = container.querySelectorAll('[data-ref]');
      explicitSpans.forEach((span) => {
        if (span.closest('svg') || span.closest('.euclid-figure-container')) return;

        const rawRefAttr = (span.getAttribute('data-ref') || '').trim();
        if (!rawRefAttr) return;

        const defaultGid =
          span.closest('[data-graphic]')?.getAttribute('data-graphic') || `${folioId}.g1`;
        const refList = rawRefAttr
          .split(';')
          .map((s) => s.trim())
          .filter(Boolean);

        const allCanonicalKeys = [];
        refList.forEach((r) => {
          const parsed = this.parseGeometorRef(r, defaultGid);
          if (parsed) {
            parsed.keys.forEach((k) => allCanonicalKeys.push(k));
          }
        });

        span.classList.add('geom-interactive-ref');
        span.setAttribute('data-geom-keys', allCanonicalKeys.join('||'));

        span.addEventListener('mouseenter', () => {
          this.highlightFromText(refList, span, defaultGid);
        });

        span.addEventListener('mouseleave', () => {
          this.clearHighlights();
        });
      });

      // 2. Contextual fallback for untagged KaTeX math elements
      const katexEls = container.querySelectorAll('.katex');
      katexEls.forEach((kel) => {
        if (kel.closest('[data-ref]') || kel.closest('.euclid-figure-container')) return;

        const annot = kel.querySelector('annotation');
        const rawTex = annot ? annot.textContent.trim() : kel.innerText.trim();
        const tokens = rawTex
          .split(/[,;\s]+/)
          .map((t) => t.replace(/[^A-Za-z0-9]/g, ''))
          .filter(Boolean);

        const resolvedRefs = tokens.map((t) => this.inferContextualRef(kel, t)).filter(Boolean);
        if (resolvedRefs.length > 0) {
          const allCanonicalKeys = [];
          resolvedRefs.forEach((r) => {
            const parsed = this.parseGeometorRef(r, `${folioId}.g1`);
            if (parsed) parsed.keys.forEach((k) => allCanonicalKeys.push(k));
          });

          kel.classList.add('geom-interactive-ref');
          kel.setAttribute('data-geom-keys', allCanonicalKeys.join('||'));

          kel.addEventListener('mouseenter', () => {
            this.highlightFromText(resolvedRefs, kel, `${folioId}.g1`);
          });

          kel.addEventListener('mouseleave', () => {
            this.clearHighlights();
          });
        }
      });
    },

    // Binds hover events on SVG elements (bidirectional: SVG -> Text)
    bindSvgElements() {
      const svgs = document.querySelectorAll('svg.euclid-graphic');
      svgs.forEach((svg) => {
        const fullGid = this.normalizeGraphicId(svg.getAttribute('data-graphic-id') || 'g1');
        const refElements = svg.querySelectorAll('[data-ref], [id]');
        refElements.forEach((el) => {
          if (el.tagName.toLowerCase() === 'g' && !el.hasAttribute('data-ref')) return;
          if (el.tagName.toLowerCase() === 'defs' || el.closest('defs')) return;

          const rawRef = (el.getAttribute('data-ref') || el.getAttribute('id') || '').trim();
          if (
            !rawRef ||
            [
              'elements',
              'graphics',
              'highlights',
              'points',
              'labels',
              'construction',
              'geometry',
            ].includes(rawRef)
          ) {
            return;
          }

          el.style.cursor = 'pointer';

          el.addEventListener('mouseenter', () => {
            this.highlightFromSvg(rawRef, el, fullGid);
          });

          el.addEventListener('mouseleave', () => {
            this.clearHighlights();
          });
        });
      });
    },

    // Highlight trigger from Text hover
    highlightFromText(refs, textElement, defaultGraphicId) {
      this.clearHighlights();

      textElement.classList.add('geom-highlight-text');
      this.activeHighlights.add(textElement);

      refs.forEach((ref) => {
        const { primary, secondary } = this.getSvgElementsForRef(ref, defaultGraphicId);

        primary.forEach((svgEl) => {
          svgEl.classList.add('geom-highlight-active');
          this.activeHighlights.add(svgEl);
        });

        secondary.forEach((svgEl) => {
          svgEl.classList.add('geom-highlight-secondary');
          this.activeHighlights.add(svgEl);
        });
      });
    },

    // Highlight trigger from SVG hover (strictly scoped to the hovered SVG's graphicId)
    highlightFromSvg(rawRef, svgElement, fullGid) {
      this.clearHighlights();

      svgElement.classList.add('geom-highlight-active');
      this.activeHighlights.add(svgElement);

      const { primary, secondary } = this.getSvgElementsForRef(rawRef, fullGid);
      primary.forEach((svgEl) => {
        svgEl.classList.add('geom-highlight-active');
        this.activeHighlights.add(svgEl);
      });
      secondary.forEach((svgEl) => {
        svgEl.classList.add('geom-highlight-secondary');
        this.activeHighlights.add(svgEl);
      });

      const targetKeys = new Set();
      const parsed = this.parseGeometorRef(rawRef, fullGid);
      if (parsed) parsed.keys.forEach((k) => targetKeys.add(k));

      const aliases = (svgElement.getAttribute('data-aliases') || '').trim();
      if (aliases) {
        aliases
          .split(/[|;]/)
          .map((s) => s.trim())
          .filter(Boolean)
          .forEach((a) => {
            const pa = this.parseGeometorRef(a, fullGid);
            if (pa) pa.keys.forEach((k) => targetKeys.add(k));
          });
      }

      const container = this.getRootContainer();
      if (!container) return;

      const interactiveTexts = container.querySelectorAll('.geom-interactive-ref');
      interactiveTexts.forEach((txtEl) => {
        const elKeys = (txtEl.getAttribute('data-geom-keys') || '').split('||').filter(Boolean);
        const matches = elKeys.some((k) => targetKeys.has(k));

        if (matches) {
          txtEl.classList.add('geom-highlight-text');
          this.activeHighlights.add(txtEl);
        }
      });
    },

    // Clear all active highlights
    clearHighlights() {
      this.activeHighlights.forEach((el) => {
        el.classList.remove(
          'geom-highlight-text',
          'geom-highlight-active',
          'geom-highlight-secondary'
        );
      });
      this.activeHighlights.clear();
    },
  };

  window.EuclidInteractive = EuclidInteractive;
  window.GeometorInteractive = EuclidInteractive;

  document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('mdView-rendered')) {
      EuclidInteractive.init();
    }
  });
})(window, document);
