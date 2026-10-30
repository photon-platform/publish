PHOTON • publish
================

.. picture:: _static/logo.png

**Unified Sphinx publishing engine, Book Codex reader, and interactive geometry/apparatus toolkit for the PHOTON and GEOMETOR ecosystems.**

``photon_platform.publish`` streamlines and extends the Sphinx documentation framework into a cohesive scholarly and technical publishing platform. Guided by the principle of **"Simple HTML, State of the Art CSS"**, ``publish`` provides a single global configuration, the **Foundation / Book Codex (Classical Scriptorium)** theme, custom geometric and structural directives, semantic inline roles, and an interactive folio transcription workstation.

----

Core Capabilities
-----------------

- **Unified Classical Scriptorium Theme**: Responsive three-column layout (``EB Garamond``, ``Fira Sans Condensed``, ``Fira Code``) with warm parchment light mode, deep obsidian dark mode, subtree-aware navigation highlighting, and unified left/right sidebars.
- **Multi-Track Book Codex (``:layout: book``)**: Hierarchical book outline, sticky reading-pane header, and automatic companion-track switching (``Pseudocode`` / ``Code`` / ``Heath``, or multi-language ``English`` / ``Italiano`` / ``Deutsch`` / ``Latin`` / ``Notes``) with track-preserving ``Prev`` / ``Next`` navigation.
- **Interactive Geometric Directives & Roles**:
  - Formal blocks: ``.. enunciation::``, ``.. signature::``, ``.. step::``, ``.. function::``, ``.. folio::``, and ``.. collapse::``.
  - Semantic roles: ``:g:`` (bidirectional SVG primitive highlighting), ``:eq:`` (equality assertions with dynamic SVG tick marks), ``:just:`` (justifications with enunciation tooltips), ``:fn:`` (composable function calls), and ``:term:`` / ``:person:`` / ``:cite:`` scholarly apparatus cards.
  - Step-by-step interactive SVG construction playback (``All``, ``|<``, ``<``, ``>``, ``>|``).
- **Container-Aware Collections & Taxonomies**: ``.. collection::`` directive with inline SVG thumbnails, enunciation excerpts, and ascending-ordered ``Categories``, ``Tags``, and ``Types`` index pages.
- **Folio Review Workstation (``publish folio``)**: Side-by-side archival scan inspection, graphic bounding-box calibration, and semantic RST transcription review.

----

Ecosystem Coordination
----------------------

All GEOMETOR digital editions and libraries build through ``publish`` via ``setup_globals()`` in ``docsrc/conf.py`` and deploy automatically via ``photon-platform/action-deploy-sphinx-gh-pages@v20``:

- `GEOMETOR • euclid <https://geometor.github.io/euclid>`_: The 3-volume Heath Edition of Euclid's *Elements* (831 recalibrated SVGs, folio apparatus, and companion commentary tracks).
- `GEOMETOR • elements <https://geometor.github.io/elements>`_: The 525-node G-Index dependency graph and 3-track Book Codex (*Pseudocode*, *Code*, *Heath*).
- `GEOMETOR • etc <https://geometor.github.io/etc>`_: Clark Kimberling's *Encyclopedia of Triangle Centers* with 2-track Book Codex (*Overview*, *Code*), ``geometor.model`` constructions, and 4 reference triangle SVGs per center.
- `GEOMETOR • pacioli <https://geometor.github.io/pacioli>`_: Fra Luca Pacioli's *De Divina Proportione* (1509 Venice / 1889 Vienna) 5-track edition with 482 recalibrated woodcuts and Leonardo da Vinci polyhedra plates.
- `GEOMETOR • hoenen <https://geometor.github.io/hoenen>`_: Fr. Peter Hoenen's *De Noetica Geometriae* (1954) bilingual Latin/English critical edition.
- `GEOMETOR • model <https://geometor.github.io/model>`_ & `GEOMETOR • explorer <https://geometor.github.io/explorer>`_: Symbolic constructive geometry engine and interactive web workbench.

----

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
