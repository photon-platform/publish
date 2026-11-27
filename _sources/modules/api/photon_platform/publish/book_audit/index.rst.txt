photon_platform.publish.book_audit
==================================

.. py:module:: photon_platform.publish.book_audit

.. autoapi-nested-parse::

   Book Codex hierarchy, track, collection, and apparatus compliance linter.



Classes
-------

.. autoapisummary::

   photon_platform.publish.book_audit.BookAuditReport


Functions
---------

.. autoapisummary::

   photon_platform.publish.book_audit.audit_repo_books


Module Contents
---------------

.. py:class:: BookAuditReport

   .. py:attribute:: repo
      :type:  str


   .. py:attribute:: book_roots
      :type:  List[str]
      :value: []



   .. py:attribute:: non_english_first_tracks
      :type:  List[Dict[str, str]]
      :value: []



   .. py:attribute:: legacy_track_filenames
      :type:  List[str]
      :value: []



   .. py:attribute:: nested_book_titles
      :type:  List[str]
      :value: []



   .. py:attribute:: duplicate_collection_toctree
      :type:  List[str]
      :value: []



   .. py:attribute:: duplicated_apparatus
      :type:  List[str]
      :value: []



   .. py:attribute:: redundant_track_lists_in_body
      :type:  List[str]
      :value: []



   .. py:property:: issue_count
      :type: int



   .. py:method:: to_dict() -> Dict[str, Any]


.. py:function:: audit_repo_books(repo_root: pathlib.Path) -> BookAuditReport

   Audit a repository's docsrc/ against the canonical GEOMETOR Book Codex standard.


