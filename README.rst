PHOTON • publish
================

.. image:: https://img.shields.io/pypi/v/photon-platform-publish.svg
   :target: https://pypi.python.org/pypi/photon-platform-publish

**Unified Sphinx publishing engine, Book Codex reader, and interactive geometry/apparatus toolkit for the PHOTON and GEOMETOR ecosystems.**

Overview
--------

``photon_platform.publish`` streamlines and extends the Sphinx documentation framework into a cohesive scholarly and technical publishing platform. Guided by the principle of **"Simple HTML, State of the Art CSS"**, ``publish`` provides a single global configuration, the **Foundation / Book Codex (Classical Scriptorium)** theme, custom geometric and structural directives, semantic inline roles, and an interactive folio transcription workstation.

All GEOMETOR digital editions and technical repositories—including ``euclid``, ``elements``, ``etc``, ``pacioli``, ``hoenen``, ``model``, and ``explorer``—build and deploy through ``publish``.

Architecture & Process
----------------------

1. **Centralized Global Configuration (``global_conf.py``)**:
   Every repository's ``docsrc/conf.py`` imports ``photon_platform.publish.global_conf`` and calls ``setup_globals(org, org_name, repo, repo_name)``, which automatically configures:

   - Project identity, metadata, and GitHub links.
   - Dynamic ``sphinx-autoapi`` discovery from ``pyproject.toml``.
   - Sister-repository ``intersphinx`` inventories (e.g., automatic cross-linking between ``geometor/euclid`` and ``geometor/elements`` with local ``docs/objects.inv`` fallback).
   - Fixed RST section heading hierarchy (``=``, ``-``, ``~``, ``^``, ``"``, ``'`` $\rightarrow$ ``h1``–``h6``).

2. **Unified Book Codex Theme (``themes/foundation/``)**:
   A responsive, CSS-Grid three-column layout styled in the **Classical Scriptorium** aesthetic (``EB Garamond`` display and body typography, ``Fira Sans Condensed`` navigation and metadata chrome, ``Fira Code`` symbolic and code blocks, warm parchment light mode and deep obsidian dark mode):

   - **Left Sidebar**: Site brand identity, subtree-aware primary navigation (highlighting active top-level sections across all child pages), and hierarchical Book Codex outline (``.book-outline``).
   - **Center Reading Pane (``.book-reading-pane``)**: Sticky multi-track header bar, synchronized companion tracks, Prev/Next unit navigation, and ornamental colophon footer.
   - **Right Sidebar (``.asides``)**: Local table of contents, recent logs, and naturally sorted taxonomy menus (``Categories``, ``Tags``, ``Types``).

3. **Multi-Track Book Codex Engine (``book.py``)**:
   Documents marked with ``:layout: book`` participate in a hierarchical codex with automatic companion-track detection:

   - **Language & Commentary Tracks**: Automatically links parallel tracks within a unit (``_en``, ``_it``, ``_de``, ``_la``, ``_notes``) or named tracks (e.g., ``index.rst`` *Pseudocode*, ``code.rst`` *Code*, ``heath.rst`` *Heath*) while preserving the user's selected track across ``Prev`` / ``Next`` navigation.

4. **Geometric & Scholarly Directives and Roles**:

   - **Structural Directives (``directives/elements.py``)**:
     - ``.. enunciation::`` — Primary proposition, definition, or center statement (automatically extracted for collection cards and hover tooltips).
     - ``.. signature:: <kind>`` — Formal ``given`` / ``construct`` / ``prove`` or ``center`` coordinate blocks.
     - ``.. step:: <kind>`` — Formal proof/construction steps (``given``, ``construct``, ``intersect``, ``assert``, ``conclude``) with right-aligned ``:just:`` justification pills and SVG step-playback attributes.
     - ``.. function:: <name>(<params>)`` — Composable geometric subroutine headers.
     - ``.. folio:: <id>`` — Marginal folio markers and floated Renaissance woodcut initial drop-caps (``:initial:``).
     - ``.. collapse::`` & ``.. note_item::`` — Collapsible technical sections (coordinates, incidence loci, commentary notes).
   - **Semantic Inline Roles (``roles/geometry.py``, ``directives/elements.py``)**:
     - ``:g:`` — Interactive geometric primitive references (points ``A``, lines ``[ A B ]``, segments ``/ A B /``, circles ``( A B C )``, angles ``< B A C )``, polygons ``< A B C >``) with bidirectional SVG hover/click highlighting.
     - ``:eq:`` — Equality assertions rendered with green assertion styling and dynamic SVG ``marker-mid`` center tick marks on equal segments and angles.
     - ``:just:``, ``:fn:``, ``:sig:`` — Cross-referenced rule justifications (with enunciation hover tooltips), callable geometric function links, and signature type badges.
     - ``:term:``, ``:person:``, ``:cite:`` — Scholarly apparatus roles backed by ``resources/glossary.json``, ``resources/persons.json``, and ``resources/citations.json`` with rich hover cards.
   - **Collections & Taxonomies (``directives/collection.py``)**:
     - ``.. collection::`` directive respecting container boundaries, rendering inline theme-aware SVG thumbnails and enunciation excerpts, and generating ascending-sorted ``tags/<tag>``, ``categories/<category>``, and ``types/<type>`` pages.

5. **Interactive SVG Controller (``static/js/geometor_interactive.js``)**:
   Powers bidirectional highlighting between ``:g:`` / ``:eq:`` text tokens and SVG primitives, plus an interactive step-by-step construction playback bar (``All``, ``|<``, ``<``, ``>``, ``>|``) driven by ``.. step::`` directives.

6. **Folio Review Workstation (``folio_review/``)**:
   A Flask web application (``publish folio``) for side-by-side archival folio image inspection, woodcut/SVG bounding-box calibration, and semantic RST transcription editing.

Installation & Usage
--------------------

.. code-block:: bash

   pip install photon-platform-publish

Command-line interface:

.. code-block:: bash

   publish build   # Compile SCSS and build Sphinx HTML documentation into docs/
   publish test    # Build and serve documentation locally with live reload
   publish folio   # Launch the side-by-side Folio Review web UI

Continuous Deployment
---------------------

All repositories coordinate with `photon-platform/action-deploy-sphinx-gh-pages <https://github.com/photon-platform/action-deploy-sphinx-gh-pages>`_ (``@v20``) in ``.github/workflows/action.yml`` to build ``docsrc/`` with Python 3.13 and deploy to GitHub Pages on every push to ``main``.

Resources
---------

- **Documentation**: https://photon-platform.github.io/publish
- **Source Code**: https://github.com/photon-platform/publish
- **Issues**: https://github.com/photon-platform/publish/issues
- **License**: MIT
