photon_platform.publish.folio_review.scanner
============================================

.. py:module:: photon_platform.publish.folio_review.scanner

.. autoapi-nested-parse::

   Folio discovery, metadata parsing, and statistics aggregation.

   Operates exclusively on `resources/` directories containing `volume_*` folders.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.folio_review.scanner.PYGMENTS_STYLE
   photon_platform.publish.folio_review.scanner.ROMAN_ORDER


Classes
-------

.. autoapisummary::

   photon_platform.publish.folio_review.scanner.FolioScanner


Functions
---------

.. autoapisummary::

   photon_platform.publish.folio_review.scanner.highlight_code_html
   photon_platform.publish.folio_review.scanner.parse_frontmatter
   photon_platform.publish.folio_review.scanner.protect_math_for_markdown
   photon_platform.publish.folio_review.scanner.restore_math_placeholders
   photon_platform.publish.folio_review.scanner.fix_relative_media_urls
   photon_platform.publish.folio_review.scanner.render_markdown_with_math
   photon_platform.publish.folio_review.scanner.render_rst_with_media
   photon_platform.publish.folio_review.scanner.discover_edition_root
   photon_platform.publish.folio_review.scanner.infer_project_and_edition


Module Contents
---------------

.. py:data:: PYGMENTS_STYLE
   :value: 'gruvbox-dark'


.. py:data:: ROMAN_ORDER

.. py:function:: highlight_code_html(code: str, lang: str = 'python') -> str

   Render code to syntax-highlighted HTML using Pygments (`gruvbox-dark`).


.. py:function:: parse_frontmatter(md_text: str) -> Tuple[Dict[str, Any], str]

   Extract YAML frontmatter and body from markdown content.


.. py:function:: protect_math_for_markdown(text: str) -> Tuple[str, Dict[str, str]]

   Replace LaTeX math spans with placeholders so Markdown doesn't mangle underscores or asterisks.


.. py:function:: restore_math_placeholders(html_str: str, placeholders: Dict[str, str]) -> str

   Restore LaTeX math spans into rendered HTML.


.. py:function:: fix_relative_media_urls(html_str: str, volume: str, rel_dir: str) -> str

   Rewrite relative image src attributes in rendered HTML to point to /media/.


.. py:function:: render_markdown_with_math(md_body: str, volume: str = '', rel_dir: str = '') -> str

   Render Markdown to HTML while preserving KaTeX math expressions and fixing image paths.


.. py:function:: render_rst_with_media(rst_body: str, volume: str = '', rel_dir: str = '') -> str

   Render reStructuredText to HTML and rewrite relative media URLs.


.. py:function:: discover_edition_root(root_path: Optional[pathlib.Path] = None) -> pathlib.Path

   Locate the edition or book root directory inside `resources/`.

   Never inspects `docsrc/`. Supports both multi-volume editions (`volume_*`)
   and single-volume book directories (`resources/<book>/`) containing folio PNGs.


.. py:function:: infer_project_and_edition(edition_root: pathlib.Path, project_title: Optional[str] = None, edition_label: Optional[str] = None) -> Tuple[str, str]

   Infer `(project_title, edition_label)` from the `resources/` path without reading `docsrc/`.


.. py:class:: FolioScanner(root_dir: Optional[pathlib.Path] = None)

   Scans `volume_*` or book directories under an edition root and indexes all folio assets.


   .. py:attribute:: root_dir


   .. py:property:: volumes
      :type: List[Dict[str, str]]


      Discover `volume_*` directories dynamically, or treat the book directory itself as the unit.


   .. py:method:: scan(force: bool = False) -> List[Dict[str, Any]]

      Scan all volumes/books and return sorted list of folio metadata dicts.



   .. py:method:: get_folio_detail(volume: str, folio: str) -> Optional[Dict[str, Any]]

      Get full details for a single folio, including rendered RST/Markdown and Notes.



   .. py:attribute:: get_folio


   .. py:method:: get_apparatus(force: bool = False) -> Dict[str, Dict[str, Any]]

      Load or build the edition's citations, glossary, and persons registries.



   .. py:method:: get_neighbors(volume: str, folio: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]

      Return (prev_folio, next_folio) in the ordered sequence.



   .. py:method:: get_summary_stats() -> Dict[str, Any]

      Compute aggregate statistics per volume and across the entire edition.



