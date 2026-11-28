changelog
=========


0.5.1
=====
*2026-11-28*

- fix(cards,bibliography): Optimize ``build_all_cards`` with O(M) inverted label index, cached site emblem, and deferred inline SVG parsing for 1,500+ page codices; add folder-per-unit bare track pairing (``<unit>/index`` + ``<unit>/la``) and locus-prefix citation matching to ``.. backlinks::``; restrict inferred ``type="book"`` to top-level book roots; exclude directory ``index`` pages from wildcard ``prefix/*`` card queries; scope remote card IDs as ``<inventory>:<docname>``; fix Sphinx 10 ``_InventoryItem`` attribute access.


0.5.0
=====
*2026-11-28*

- feat(cards): Add unified ``Card`` engine (``cards.py``) with hybrid description precedence (``:description:`` > ``.. summary::`` > ``.. enunciation::`` > flagged fallback), dual visual slots (small project ``emblem`` medallion + larger ``image`` hero), ``:card_ref:`` canonical inheritance, automatic ``docs/cards.json`` (``photon.card.v1``) export alongside ``objects.inv``, and lazy Intersphinx-backed ``CardRegistry`` with ``register_sisters(...)`` in ``global_conf.py``.
- feat(directives & collections): Add ``.. card:: <address>``, ``.. summary::``, ``.. citation-formats::``, and ``.. backlinks::`` directives (``directives/card.py``), and extend ``.. collection::`` / directory presets to seamlessly mix local records with remote Intersphinx card addresses, wildcard queries (``euclid:books/*``, ``*:type=book``), and ``:from-roles:`` auto-collections.
- feat(theme & social): Unify card markup into one 4-slot semantic ``<article class="card">`` template (``components/card.html`` + ``_cards.scss``) driving vertical cards, horizontal banners, compact lists, directories, inline embeds, and local ``google-chrome --headless=new`` ``1280x640`` HTML+CSS social banner capture (``social_capture.py`` + ``social_card.html``).
- feat(bibliography & roles): Add ``bibliography.py`` with pure-Python Chicago, MLA, APA, and BibTeX citation formatters, ``docs/bibliography.bib`` export, and automated parallel-track Hoenen-style passage backlinks (``LA · EN``); upgrade ``:person:``, ``:cite:``, and ``:term:`` in ``roles/geometry.py`` to resolve per-record directories and cross-project ``cards.json`` Cards with rich tooltips.


0.4.13
======
*2026-11-27*

- feat(book-codex & outline): Unify Book Codex hierarchy around English-first folder-per-unit auto-detection (``index.rst`` + bare ``<lang>.rst``, ``summary.rst``, ``notes.rst``, and ``title-<lang>.rst``), auto-register bare companion tracks into hidden toctrees, fix primary English breadcrumb resolution, and add ``el``/``grc``/``fr``/``da``/``book_title`` to Prev/Next auxiliary skipping and collection filtering.
- feat(outline & nav): Auto-generate full-page searchable/collapsible ``<book>/outline.html`` and cached ``<book>/outline-data.js``, add a one-click **Outline** slide-over drawer in ``book_layout.html``, add ``.. book-outline::`` and recursive ``collection/outline.html``, and keep ``header.book-header`` and ``footer.book-footer`` at a consistent full outer-border width across all book pages with ``Prev``/``Next`` pinned to outer edges.
- feat(cli): Add ``publish audit-book`` compliance linter (``book_audit.py``).


0.4.11
======
*2026-11-16*

- fix(collections): Fix ``docsrc`` vs. ``docs`` string-prefix collision in ``_extract_direct_figure`` (``directives/collection.py``) using component-safe ``Path.is_relative_to()`` and proactively staging ``.. figure::`` / ``.. image::`` assets into ``_images/<dest_name>`` via ``env.images`` so static SVG/raster collection thumbnails never emit broken ``../docsrc/...`` URLs on clean builds; also render ``.. enunciation::`` nodes as rich math HTML inside collection cards while keeping plain-text ``excerpt`` metadata for OpenGraph descriptions.


0.4.10
======
*2026-11-16*

- feat(ingest & tracks): Add resumable 25-page ``pdftoppm -gray`` chunked rendering, MRC scan-layer filtering, and multi-PDF edition disambiguation in ``folio_ingest.py``, support explicit ``edition:<NNNN>`` prefixes in ``folio_links.py``, support ``:docs:`` and body lists in ``CollectionDirective``, parse explicit ``:tracks:`` frontmatter on collection cards in ``book.py``, and strip trailing brand suffixes in ``social_meta.py``.


0.4.9
=====
*2026-11-15*

- fix(social & collections): Resolve CSS custom properties (``var(--geom-*)``) and invert white-paper / dark-ink woodcuts to warm ivory on ``1200x630`` sharing banners in ``social_meta.py``, remove duplicate ``sphinxext.opengraph`` relative tags from ``global_conf.py``, give explicit ``:excerpt:`` metadata priority in ``directives/collection.py``, promote leading ``.. folio::`` nodes during ``doctree-resolved`` before HTML translation, and fix first-invocation hot-reload in ``mcp_server.py``.


0.4.8
=====
*2026-11-15*

- feat(masthead & breadcrumbs): Stack ``GEOMETOR / • / <repo>`` centered vertically inside the clickable sidebar Home logo link, suppress ``<header class="book-header">`` on ``master_doc`` (Home Page), remove ``.book-portal-link`` (``← <repo>``) everywhere, and unify section/book-anchored breadcrumbs (``layout/_breadcrumbs.html`` + ``resolve_page_breadcrumbs``) separated cleanly from provenance pills across all page hierarchies.
- fix(footer): Render concise ``Prev`` and ``Next`` labels (with hover title tooltips) in ``.book-footer-nav`` across ``book_layout.html`` and ``article/index.html``, eliminating long-title overlaps.
- feat(social): Add ``social_meta.py``, ``layout/_head_social.html``, ``publish social-banner``, and MCP ``publish_social_banner`` emitting ``A–Z`` bookmark-friendly ``<title>`` tags (``<Full Name> • GEOMETOR``), canonical URLs, OpenGraph, and Twitter ``summary_large_image`` metadata backed by dedicated ``1200x630`` sharing-only PNGs in ``_static/social/``.
- feat(collections & folios): Add recursive container graphic bubbling (``_resolve_representative_figure``), Hoenen-style companion track pills on collection cards, ``collection/outline.html``, masthead promotion of leading ``.. folio::`` markers with quiet marginal transitions, and ``publish folio-ingest`` / MCP ``publish_folio_ingest`` for 300-DPI ``<NNNN>.png`` rendering and embedded text/graphic extraction.


0.4.7
=====
*2026-11-15*

- style(geometor): Add first-class ``--geom-muted``, ``--geom-hyper``, and ``--geom-rose`` CSS custom properties across dark, light, book-codex, and print palettes alongside ``.geom-hyper-line``, ``.geom-rose-line``, ``.geom-polygon-hyper``, ``.geom-polygon-rose``, ``.geom-point-hyper``, ``.geom-point-rose``, and ``.geom-label-{accent,assert,hyper,rose}`` rules in ``_geometor.scss`` and compiled ``styles.css``.


0.4.6
=====
*2026-11-15*

- fix(images): Auto-inject explicit pixel ``width`` and ``height`` attributes from ``viewBox`` onto widthless inline SVGs in ``prepare_inline_svg`` (preventing ``0px`` layout collapse inside ``figure.photon-svg { width: fit-content; }``), deduplicate ``class`` attributes on ``<svg>`` thumbnails, and register ``note_dependency`` + dynamic ``svg_abs_path`` rendering on ``picture_node``.
- fix(images): Preserve custom embedded SVG ``<style>`` blocks scoped per-diagram via ``svg[data-svg-scope="..."]`` with Nocturnal / ``body.light-mode`` theme adaptation while stripping container background boxes, global theme variable overrides, and legacy light-only boilerplate styles.
- style(geometor): Add ``figure.photon-svg svg:not([width])`` fallback width and zero-specificity ``:where(...)`` fallback selectors for cross-corpus geometric classes (``.geom-segment``, ``.Line``, ``.Segment``, ``.Circle``, ``.Curve``, ``.Polygon``, ``.Point``, ``.geom-accent-line``, ``.geom-assert-line``, ``.golden-segment``, ``.geom-faint``, etc.) in ``_geometor.scss``.


0.4.5
=====
*2026-11-15*

- feat(branding): Configure ``html_favicon = "_static/favicon.ico"`` alongside ``html_logo = "_static/logo.png"`` in ``global_conf.py``, wire ``favicon_url`` fallback in the ``foundation`` theme layout, add ``publish``'s ``docsrc/_static/favicon.ico``, and serve repo-aware ``/favicon.ico`` and ``/brand/logo.png`` assets in the ``publish folio`` review web UI.


0.4.4
=====
*2026-11-14*

- feat(serve): Add standalone ``publish serve`` command (separate from ``publish test``) that serves ``docs/`` via multi-threaded HTTP without wiping ``docs/`` on exit, automatically scans for the next open port starting at ``8000`` (enabling multiple books side-by-side), auto-builds only when ``docs/index.html`` is missing (or ``-b``/``--build`` is passed), and launches automatically in Google Chrome (``--no-browser`` to suppress).


0.4.3
=====
*2026-11-14*

- perf(build): Make ``publish build`` incremental by default (retaining ``docs/.doctrees`` and mtime-gating ``sphinx-autoapi`` and SASS compilation unless ``--clean`` is passed), conditionally load non-parallel-safe ``sphinx_revealjs`` / ``sphinx_carousel`` extensions only when used so Sphinx runs 8-core parallel reads as well as writes (``-j`` / ``--jobs``), and add ``--repo`` and ``--json`` CLI flags.
- fix(collection): Add ``env-get-outdated`` hook (``check_root_navigation_outdated``) so incremental builds automatically invalidate ``master_doc`` whenever subpage ``:navigation:``, ``:order:``, or ``:nav_title:`` frontmatter changes.
- feat(mcp): Add zero-dependency JSON-RPC 2.0 stdio MCP server (``publish mcp`` / ``photon_platform.publish.mcp_server``) exposing ``publish_build``, ``publish_build_batch``, ``publish_clean``, ``publish_epub``, and ``publish_folio_links``.


0.4.2
=====
*2026-11-14*

- feat(collection): Support ``:nav_title:`` frontmatter overrides and deterministic ``(order, docname)`` sorting for ``header`` and ``footer`` navigation menus.
- feat(book): Add Greek (``-el``/``-grc``), French (``-fr``), and Danish (``-da``) companion track detection and normalize track switcher labels to English (``English``, ``Greek``, ``Latin``, ``German``, ``French``, ``Italian``, ``Danish``).
- feat(epub): Default EPUB track bar utility links to English (``Contents``, ``People``) while honoring book-root ``:toc_label:`` and ``:persons_label:`` metadata overrides (e.g. ``Conspectus`` / ``Index Nominum`` in ``geometor/hoenen``).
- style(geometor): Generalize classical Book Index Table of Contents layout to ``section#table-of-contents``, ``section#contents``, ``section#conspectus-totius-operis``, and ``section.book-toc`` using LibSass-safe direct-child selectors so ``.collection`` cards remain unclipped.


0.4.1
=====
*2026-11-13*

- fix(folio_links): Resolve repository root prior to cache lookup and cache scan/manifest indices on Sphinx/mock env regardless of caller invocation form for O(1) directive resolution during audits.


0.4.0
=====
*2026-11-13*

- feat(folio_links): Primary-source folio URL resolution, repository link auditing, and scan index caching.
- feat(book): Populate ``folio_url`` in ``resolve_book_context`` for book header badge link rendering.
- feat(directives): Track-aware folio directive and badge target resolution.
- feat(agents): Add canonical ``folio-curator`` subagent definition.


0.3.24
======

- feat(agents): Add canonical ``scriptorium-codex`` skill and ``scriptorium`` subagent with multimodal scan-vision folio ingestion mandate, 4-step Ink-to-Vector SVG calibration, and ``:layout: book`` codex standards.
- feat(book,elements): Add ``Video`` companion track support and ``∴ conclude`` step badge rendering.


0.3.23
======

- feat(geometry): Format multi-vertex subscripted ``:g:`` display labels cleanly across HTML and SVG tooltips.


0.3.22
======

- style(collection,excerpt): Unify ``.collection`` layouts (``cards``, ``banners``, ``list``), ``article.excerpt`` cards, ``.collection-controls`` buttons, and ``.meta`` badges (``date``, ``author``, ``category``, ``tags``) with the Classical Scriptorium Book Codex design tokens and typography.
- fix(article): Scope ``article/_index.scss`` to ``article:not(.excerpt)`` without legacy container-query row wrapping, and replace the hardcoded dark ``blockquote`` background in ``article/_content.scss`` with ``--book-surface-alt``.
- feat(collection,log): Infer ``:type: log`` and ``:date:`` from ``log/<stamp>/`` docnames when omitted, support ``:excerpt:`` frontmatter fallback, use ``safe_sort_key`` for mixed numeric/string collection sorting, and render ``meta.date`` / ``meta.author`` badges in ``article/index.html``.


0.3.21
======

- fix(collection): Sort tag, category, and type taxonomy page listings in ascending order by ``order`` / ``number`` / ``proposition`` instead of descending (`reverse=True`), and natural-sort Roman numeral and numeric taxonomy suffixes (e.g., ``book-i``..``book-xiii``) in sidebar navigation lists.


0.3.20
======

- style(foundation): Unify the Foundation theme palette, typography (``EB Garamond``, ``Fira Sans Condensed``, ``Fira Code``), and page templates (``article/index.html``, ``category_page.html``, ``tag_page.html``, ``type_page.html``, ``search.html``) with the Classical Scriptorium Book Codex aesthetic across all project pages.
- style(asides,header,footer): Harmonize left and right sidebar panels and menu item styling with codex pill highlights, warm recessed surfaces, and gold active accents; hide the mobile toggle checkbox on desktop (`display: none !important`).
- fix(nav): Highlight active section links in ``header/nav.html`` and ``footer/nav.html`` when viewing any child page underneath a section index (e.g., ``heath/index`` -> ``heath/...``) or book root, and mark active taxonomy/log links in right-sidebar asides.


0.3.19
======

- feat(global_conf): Propagate ``setup_globals()`` configuration to the calling ``conf.py`` frame and automatically register ``euclid`` and ``elements`` intersphinx inventories with local sibling ``objects.inv`` fallback.
- feat(elements): Resolve ``:just:`` and ``.. assertion::`` Euclid proposition/definition/postulate/common-notion references against ``intersphinx`` inventories (e.g., ``geometor/euclid``) when not defined locally, and attach Euclid enunciation tooltips to both ``:just:`` and intersphinx ``:ref:`` links.
- feat(elements,styles): Add ``.. collapse::`` and ``.. note_item::`` blocks and skip ``signature`` / ``collapse`` nodes when extracting collection card excerpts.



0.3.18
======

- feat(book): Add multi-language companion track detection (``_en``, ``_it``, ``_de``, ``_la``, ``_notes``), unit-scoped bare track resolution, and track-preserving ``Prev`` / ``Next`` navigation across Book Codex documents.
- feat(elements): Emit Sphinx ``nodes.image`` with class ``folio-initial-cap`` in ``FolioDirective`` when ``:initial:`` is specified so woodcut drop-caps are copied into ``_images/`` and styled as floated initial caps.
- feat(elements,geometry): Add ``.. signature::`` and ``.. function::`` directives, ``:sig:`` role, and step-by-step SVG playback controls in ``geometor_interactive.js``.


0.3.15
======

- fix(geometry): HTML-escape ``:g:`` display text so GEOMETOR symbolic indications (``< A B C >``, ``< B A C )``) render properly and add ``white-space: nowrap`` to ``.geom-ref``.
- feat(collection): Support both ``:categories:`` and ``:category:`` metadata, inline SVG thumbnails on taxonomy pages, and ``original_id`` / footer metadata badges in ``book_layout.html``.


0.3.12
======

- feat(geometry): Add inline ``:eq:`` equality role and ``:equal:`` / ``:assert:`` directive options for green assertion highlighting and SVG ``marker-mid`` center tick marks on equal segments and angles.
- style(geometry): Shift element reference accent highlight (``--geom-accent``) from red to warm gold.


0.3.7
=====

- fix: Support Sphinx 9+ partial rendering (`render_partial`) without `'html_body'`.


0.3.4
=====

- fix: Resolved `TemplateNotFound` errors by updating template include paths.
- refactor: Cleaned up CSS by archiving unused form styles and optimizing SCSS imports.
- fix: Corrected search input visibility ensuring proper contrast.
- fix: Removed erroneous `<main>` tag wrapping from article excerpts.
- feat: Enhanced header responsiveness with a mobile hamburger menu and improved desktop alignment.
- style: Centered breadcrumbs navigation and refined header visual details (removed bullets).

0.3.3
=====

- refactor: Major SCSS architecture cleanup, including removal of legacy files and standardization of breakpoints.
- style: Refined Blockquotes with strictly darker background, removed borders, and adjusted font size to 1.1em.
- fix: Resolved navigational responsiveness issues by reverting to standard media queries in `nav.scss`.
- style: Updated `article.scss` to use Container Queries for robust component-level layouts.

0.3.2
=====

- fix: Forced section collection headers to the top of the layout using CSS `order: -1` and `grid-column: 1 / -1`.
- refactor: Reorganized todos documentation into a dedicated `docsrc/todos` directory.
- style: Updates to foundation theme styles and mission goals.

0.3.1
=====

- fix: Removed hardcoded width from `visit_picture_node` in `images/directive.py` to allow CSS to control image sizing.

0.3.0
=====

- feat: Implemented comprehensive Featured Image System.
    - Added `.. picture::` directive for responsive, optimized WebP images with fallback.
    - Implemented automatic thumbnail generation and caching.
    - Integrated featured images with `collection` directive for rich article lists.
    - Support for "Banner", "Card", and "List" layouts with optimized thumbnails.
    - Images wrap in links to full-size originals.

0.2.35
======

- refactor: Automated root navigation injection in `collection.py`, allowing header and footer items to be automatically discovered and added to the site hierarchy.
- refactor: Removed the implicit global toctree injection in favor of proper recursive collection directives for sub-sections.
- docs: Updated root `index.rst` to be cleaner, removing manual collection directives.

0.2.34
======

- removed: Deleted the deprecated `photon` theme and legacy `build_sass.py` script.
- refactor: Standardized on the `foundation` theme, removing conditional theme logic from `collection.py`.

0.2.33
======

- fix: Updated collection card grid layout to use smaller minimum column width (16em).
- style: Refined collection figure sizing and alignment for cards, banners, and lists (enforcing square aspect ratios and centering).
- docs: Added documentation for ``safe_numeric`` function.

0.2.32
======

- fix: Added margin-bottom to highlighted code blocks to prevent visual crowding.

0.2.31
======

- fix: Implemented robust numerical sorting for collections and navigation to prevent type errors when metadata contains non-numeric values.

0.2.30
======

- style: Refined collection layouts with dedicated styles for cards, banners, and lists in ``_collection-layouts.scss``.
- style: Improved article card visual hierarchy and responsiveness.
- style: Updated main article layout to better handle flex behavior across breakpoints.

0.2.29
======

- style: Added dedicated SCSS for API documentation (`_api.scss`) to improve readability of parameters and return types.
- style: Updated code block styling in `_code.scss` for better contrast and layout.

0.2.28
======

- feat: Added favicon support to the foundation theme layout.
- style: Improved indentation in the foundation theme layout HTML.

0.2.27
======

- feat: Enabled ``sphinx.ext.viewcode`` to allow viewing source code directly from documentation.
- style: Added specific styling for ``viewcode`` links to match the foundation theme.
- conf: Updated intersphinx mapping for Python to version 3.13.

0.2.26
======

- feat: Added dynamic AutoAPI configuration in ``global_conf.py`` that reads project structure from ``pyproject.toml``.
- feat: Added ``--port`` option to the ``test`` command in the CLI to allow specifying the server port.
- feat: Enabled ``sphinx.ext.napoleon`` for better support of Google and NumPy style docstrings.
- docs: Introduced a new "Standards" section to the documentation.
- config: Removed hardcoded ``html_theme`` from local ``conf.py``, relying on global defaults.

0.2.25
======

- feat: Added interactive layout controls for collections (Cards, Banners, List).
- feat: Implemented JavaScript-based collection switching with persistence.
- style: Updated collection SCSS to support multiple layout modes.
- refactor: Migrated documentation indices to use the ``collection`` directive.

0.2.24
======

- docs: comprehensive update to documentation structure and content.
    - Added detailed usage guides for collections, taxonomy, code documentation, references, diagrams, and math.
    - Refined mission statement and goals.
    - Updated main index with key features and latest updates section.
    - Added references section with inspirations and extensions.

0.2.23
======

- refactor(theme): Massive refinements to the foundation theme, including:
    - streamlining SCSS imports and removing legacy files.
    - consolidating font and element styles for better maintainability.
    - implementing variable-based theming for consistent colors and fonts.
    - removing unused SCSS partials (reset, normalize, etc.) in favor of a cleaner base.

0.2.22
======

- fix: Correctly handle image paths in the ``collection`` directive by using ``pathto`` with ``relative_uri`` for resources, preventing unwanted ``.html`` extensions on image files.
- ci: Add Graphviz installation to the GitHub Actions workflow to support graph generation.

0.2.21
======

- fix(collection): The ``h1`` title in collection sections is now conditional and will only be rendered if a title is explicitly provided. This prevents the display of a default "Collection" title.

0.2.20
======

- refactor(theme): Replaced the broad `body > *` selector with specific rules for main layout sections, extending a common `%section-default` placeholder for improved maintainability and CSS specificity.

0.2.19
======

- feat: Introduce the new `foundation` theme, a major refactor designed for composability by co-locating SCSS styles with their corresponding HTML templates.
- feat: Generalize the SASS build process to automatically discover and compile styles for all available themes.
- fix: Make the `CollectionDirective` theme-aware, ensuring it uses the correct template path for both the new `foundation` theme and the legacy `photon` theme.

0.2.18
======

- refactor: Standardize article and excerpt layouts, converting to a consistent flexbox model and restructuring HTML for better semantic alignment.

0.2.17
======

- feat: Refine article excerpt styling for a more compact, responsive, and vertically-aligned layout.
- feat: Sort taxonomy pages by the ``:number:`` metadata field to ensure a consistent and predictable order.

0.2.16
======

- fix: Implement numerical sorting for collection items to ensure correct ordering of numbered pages.
- fix: Prevent duplicate ``toctree`` entries when using the ``collection`` directive on multiple pages, resolving warnings and ensuring correct previous/next navigation.

0.2.15
======

- feat: Generate rich excerpts for collections, including the first paragraph or blockquote and the first figure.
- feat: Apply rich excerpt logic to taxonomy pages (tags, categories, types).
- fix: Limit collection search to the current directory and immediate subdirectories to prevent duplicate ``toctree`` entries.
- fix: Correct image paths in excerpts to be root-relative and prevent an erroneous ``.html`` suffix.
- style: Move article metadata to a ``<footer>`` in the excerpt template for better semantic structure.

0.2.14
======

- fix: Add ``jquery`` as a dependency to ``pyproject.toml`` to ensure it is
  installed for the ``sphinx-carousel`` extension.
- docs: Update ``README.rst`` with current project status and details.
- chore: Update package metadata and dependencies.


0.2.13
------
*2025-11-11*

**fixed**

+ Removed redundant SASS compilation performed by `sphinxcontrib-sass`, which was creating an empty `docsrc/theme/photon/static/css` directory. The build process now relies solely on the `publish.build_sass()` function for all SASS compilation.

0.2.12
------
*2025-11-11*

**fixed**

+ Resolved an issue where tags were being split into individual characters in article excerpts.
+ Ensured that both tags and categories are consistently handled as lists, allowing for multiple values.

**changed**

+ Article excerpts now display metadata (date, category, tags) with labels for improved clarity.
+ The styling of article excerpts has been updated to be more condensed and visually consistent with the full article view.

0.2.11
------
*2025-11-11*

**added**

+ Added support for tags and categories, with dedicated pages for each.
+ Integrated tags and categories into article metadata and sidebar navigation.

0.2.10
------
*2025-11-10*

**changed**

+ The article navigation buttons have been styled to be more prominent and consistent with the theme.

0.2.9
-----
*2025-11-10*

**fixed**

+ Added `matplotlib` as an explicit dependency to resolve build warnings and ensure social card generation.
+ Disabled the `sphinx.ext.autosummary` and `sphinx.ext.autodoc` extensions, which were running unnecessarily and cluttering the build output.

0.2.8
-----
*2025-11-10*

**fixed**

+ Images within the content area are now responsive and will not exceed the width of their container.
+ Added a bottom margin to paragraphs and a top margin to headings to improve readability and spacing.

0.2.7
-----
*2025-11-09*

**changed**

+ The style of the headerlink has been changed to match the size of the heading it's in. It is now faded until hovered over, at which point it shows the link color. It also has a little left padding to separate it from the heading.

0.2.6
-----
*2025-11-09*

**added**

+ Integrated Sphinx AutoAPI for automated API documentation generation.
+ Added comprehensive docstrings and type hints to all modules for improved code clarity and maintainability.

**changed**

+ Refactored the documentation structure to place the API reference under the "Modules" section.
+ Cleaned up `global_conf.py` by removing unused configuration variables and adding a module docstring.

0.2.5
-----
*2025-11-09*

**added**

+ Admonition styling for todo, note, warning, danger, attention, caution, error, hint, important, and tip.

0.2.4
-----
*2025-11-09*

**added**

+ Added the organization and repository name to the header for better branding and context.

0.2.3
-----
*2025-11-09*

**added**

+ Added a footer navigation section, configurable via page metadata.

0.2.2
-----
*2025-11-08*

**changed**

+ Refined theme styles and templates, removing unused files and streamlining the overall structure.
+ Implemented new breadcrumbs in article headers for improved navigation.
+ Pared down font weights to reduce load times and improve performance.
+ Replaced the aggressive CSS reset with a more modern, targeted approach.

0.2.1
-----
*2025-11-08*

**changed**

+ The SCSS compilation now generates expanded, readable CSS instead of compressed CSS. This improves debuggability of the styles.

0.2.0
-----
*2025-11-08*

**changed**

+ Refactored the Sphinx theme to align with the design and functionality of the original Grav theme.
+ Replaced the `ablog` extension with a custom `collection` directive to provide more flexible, time-based content listings for any page type.
+ Introduced a hierarchical content model, allowing pages to manage and display subordinate items.
+ Updated the theme templates to use a more semantic and modular HTML structure.
+ Integrated SASS for more maintainable and flexible styling.

0.1.2
-----
*2025-11-07*

**changed**

+ Refactored the `publish` tool to use a `click`-based command-line interface with `build` and `test` commands.
+ Standardized the theme name to `photon` and the main SASS file to `styles.scss`.
+ Consolidated all theme and Sphinx configurations into `global_conf.py` to simplify project-level `conf.py` files.
+ Made the build process context-aware, allowing it to be run from any directory within a git repository.
+ Integrated SASS compilation into the build process.
+ Removed the old, unused `theme` directory.

0.1.1
-----
*2025-11-07*

**fixed**

+ Resolved build issues with the Sphinx documentation by removing outdated and conflicting files from the `docsrc/modules` directory. This ensures a clean and successful build process.

0.1.0
-----
*2025-11-07*

**removed**

+ Removed the `sphinxilator_theme` and all its associated SCSS files, streamlining the project to focus on a single, unified theme provided by the `publish` tool. This change simplifies the theming architecture and removes legacy code.

0.0.4
-----
*2025-10-26*

**changed**

+ ...

0.0.3
-----
*2025-10-26*

**added**

+ Integrated `sphinx_rtd_theme` navigation, including toctree and sticky navigation.
+ Integrated `sphinx_rtd_theme` search functionality with a custom search page.
+ Added breadcrumbs and previous/next buttons for improved navigation.

0.0.2
-----
*2025-10-26*

**added**

+ Created a new, unified `publish_theme` to consolidate documentation styling.
+ Ported the basic HTML structure and templates from `sphinx_rtd_theme`.
+ Integrated the SASS styles and structure from `grav-theme-photon`.
+ Implemented a new semantic HTML layout (`<header>`, `<main>`, `<asides>`).
+ Established a simplified, dark-theme-first color palette.
+ Added a SASS build system to compile theme assets.