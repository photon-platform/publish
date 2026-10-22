photon_platform.publish.book
============================

.. py:module:: photon_platform.publish.book

.. autoapi-nested-parse::

   Book subtree inheritance and multi-track context injection for the 'Website in a Website' Codex layout.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.book.nodes


Functions
---------

.. autoapisummary::

   photon_platform.publish.book.peek_metadata
   photon_platform.publish.book.detect_companion_tracks
   photon_platform.publish.book.resolve_book_context
   photon_platform.publish.book.setup_book_page_context
   photon_platform.publish.book.setup


Module Contents
---------------

.. py:data:: nodes
   :value: None


.. py:function:: peek_metadata(filepath: str) -> Dict[str, str]

   Peek at the beginning of an RST file to extract top field-list metadata.


.. py:function:: detect_companion_tracks(env: Any, pagename: str) -> List[Dict[str, Any]]

   Detect companion tracks for `pagename` in `env.found_docs`.

   Supports:
   - Euclid / Elements tracks: ``index`` / ``proposition``, ``commentary``, ``notes``, ``folio``
     or ``<pagename>.commentary``, ``<pagename>.notes``
   - Pacioli tracks: ``<stem>_en``, ``<stem>_it``, ``<stem>_de``, ``<stem>_notes``, ``index``
   - Hoenen tracks: ``<stem>`` (Latin), ``<stem>-en``, ``<stem>-summary``, ``translation-notes-<stem>``


.. py:function:: resolve_book_context(env: Any, pagename: str, doctree: Optional[docutils.nodes.document] = None) -> Dict[str, Any]

   Resolve book subtree inheritance and companion tracks for `pagename`.


.. py:function:: setup_book_page_context(app: Any, pagename: str, templatename: str, context: Dict[str, Any], doctree: Optional[docutils.nodes.document]) -> Optional[str]

   Sphinx `html-page-context` hook to inject Book Codex context and select `book_layout.html`.


.. py:function:: setup(app: Any) -> Dict[str, Any]

   Register the book subtree inheritance hook with Sphinx.


