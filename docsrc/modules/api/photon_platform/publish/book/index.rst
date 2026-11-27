photon_platform.publish.book
============================

.. py:module:: photon_platform.publish.book

.. autoapi-nested-parse::

   Book subtree inheritance and multi-track context injection for the 'Website in a Website' Codex layout.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.book.nodes


Classes
-------

.. autoapisummary::

   photon_platform.publish.book.PendingBookOutline
   photon_platform.publish.book.BookOutlineDirective


Functions
---------

.. autoapisummary::

   photon_platform.publish.book.peek_metadata
   photon_platform.publish.book.detect_companion_tracks
   photon_platform.publish.book.resolve_book_context
   photon_platform.publish.book.filter_epub_book_sources
   photon_platform.publish.book.resolve_book_doctree
   photon_platform.publish.book.resolve_epub_missing_reference
   photon_platform.publish.book.resolve_page_breadcrumbs
   photon_platform.publish.book.inject_companion_tracks_toctree
   photon_platform.publish.book.discover_book_roots
   photon_platform.publish.book.build_book_outline_tree
   photon_platform.publish.book.generate_book_outline_pages
   photon_platform.publish.book.setup_book_page_context
   photon_platform.publish.book.setup


Module Contents
---------------

.. py:data:: nodes
   :value: None


.. py:function:: peek_metadata(filepath: str) -> Dict[str, str]

   Peek at the beginning of an RST file to extract top field-list metadata.


.. py:function:: detect_companion_tracks(env: Any, pagename: str) -> List[Dict[str, Any]]

   Detect companion tracks for ``pagename`` in ``env.found_docs``.

   Supports:

   - Elements 2.0 tracks: ``index`` (Pseudocode), ``video`` (Video), ``code`` (Code), ``heath`` (Heath)
   - Euclid tracks: ``index`` / ``proposition``, ``commentary``, ``notes``, ``folio``
     or ``<pagename>.commentary``, ``<pagename>.notes``
   - Multilingual tracks: ``<stem>_en`` / ``-en``, ``-el`` (Greek), ``-la`` (Latin),
     ``-de`` (German), ``-fr`` (French), ``-it`` (Italian), ``-da`` (Danish),
     ``-summary``, ``-notes``
   - Hoenen tracks: ``<stem>`` (Latin), ``<stem>-en``, ``<stem>-summary``, ``translation-notes-<stem>``


.. py:function:: resolve_book_context(env: Any, pagename: str, doctree: Optional[docutils.nodes.document] = None) -> Dict[str, Any]

   Resolve book subtree inheritance and companion tracks for `pagename`.


.. py:function:: filter_epub_book_sources(app: Any, docname: str, source: List[str]) -> None

   Clean up non-book editorial references in source RST when building an EPUB.


.. py:function:: resolve_book_doctree(app: Any, doctree: Any, fromdocname: str) -> None

   Consolidate footnote targets and apply EPUB 3 doctree transformations.


.. py:function:: resolve_epub_missing_reference(app: Any, env: Any, node: Any, contnode: Any) -> Optional[Any]

   Gracefully degrade excluded website references (e.g. about-*) to plain text in EPUB builds.


.. py:function:: resolve_page_breadcrumbs(app: Any, env: Any, pagename: str, context: Dict[str, Any]) -> Dict[str, Any]

   Build unified section/book-anchored `page_breadcrumbs` and separate `provenance_badges` across all page types.


.. py:function:: inject_companion_tracks_toctree(app: Any, docname: str, source: List[str]) -> None

   Automatically register bare sibling companion tracks into a hidden toctree on book `index.rst` files.

   Eliminates manual hidden `.. toctree::` boilerplate for `la.rst`, `el.rst`, `de.rst`,
   `fr.rst`, `it.rst`, `da.rst`, `summary.rst`, `notes.rst`, `commentary.rst`, `folio.rst`,
   and `title-<lang>.rst` files inside `:layout: book` directories.


.. py:function:: discover_book_roots(env: Any) -> List[str]

   Return sorted outermost Book Root docnames in `env.found_docs`.


.. py:function:: build_book_outline_tree(env: Any, book_root: str) -> List[Dict[str, Any]]

   Build a recursive structural outline tree starting from `book_root` via Sphinx toctree_includes.


.. py:class:: PendingBookOutline(rawsource: str = '', *children, **attributes: Any)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   Placeholder resolved on `doctree-resolved` into a full nested Book Outline.


.. py:class:: BookOutlineDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Directive `.. book-outline::` embedding the full nested outline of the current book.


   .. py:attribute:: has_content
      :value: False


      May the directive have content?


   .. py:attribute:: option_spec

      Mapping of option names to validator functions.


   .. py:method:: run() -> List[Any]


.. py:function:: generate_book_outline_pages(app: Any) -> Any

   Dynamically generate `<book>/outline.html` and `<book>/outline-data.js` for every Book Codex.


.. py:function:: setup_book_page_context(app: Any, pagename: str, templatename: str, context: Dict[str, Any], doctree: Optional[docutils.nodes.document]) -> Optional[str]

   Sphinx `html-page-context` hook to inject Book Codex, breadcrumbs, and social `<head>` context.


.. py:function:: setup(app: Any) -> Dict[str, Any]

   Register the book subtree inheritance, full-book outline, and EPUB 3 hooks with Sphinx.


