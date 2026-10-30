:date: 26.302-183000
:author: phi ARCHITECT
:type: log
:categories: theme, architecture
:tags: codex, navigation, collection, taxonomy

=========================================================
Unified Classical Scriptorium Theme & Collection Redesign
=========================================================

Unified the visual design, navigation architecture, and collection/log templates of ``photon-platform.publish`` around the **Classical Scriptorium** Book Codex aesthetic across all PHOTON and GEOMETOR sites.

Highlights
----------

- **Unified Classical Scriptorium Palette & Typography**: Standardized all pages, sidebars, headers, footers, blockquotes, and cards around ``--book-*`` design tokens, ``EB Garamond`` display/body typography, and ``Fira Sans Condensed`` metadata badges in both Nocturnal Parchment (dark) and Warm Ivory (light) modes.
- **Subtree-Aware Navigation Active States**: Updated ``layout/header/nav.html`` and ``layout/footer/nav.html`` so section links remain highlighted when browsing any nested document inside a Book Codex or documentation subtree, with exact matching for ``master_doc``.
- **Natural Roman & Numeric Taxonomy Sorting**: Added ``_natural_taxonomy_sort_key`` and ``_sort_taxonomy_articles`` in ``directives/collection.py`` so ``book-i``..``book-xiii`` and numbered propositions sort in natural ascending order.
- **Redesigned Collections & Progress Logs**: Restyled ``.collection`` (``cards``, ``banners``, ``list``), ``article.excerpt``, and ``.meta`` badges, added type-safe sorting for mixed date/numeric keys, and enabled automatic ``:type: log`` and ``:date:`` inference for entries under ``docsrc/log/``.
