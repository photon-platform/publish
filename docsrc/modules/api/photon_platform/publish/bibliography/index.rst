photon_platform.publish.bibliography
====================================

.. py:module:: photon_platform.publish.bibliography

.. autoapi-nested-parse::

   Scholarly Bibliography formatting (Chicago, MLA, APA, BibTeX) and automated
   bidirectional passage backlinks (`.. citation-formats::` and `.. backlinks::`).

   Works directly from unified `Card` objects (local or inherited via `:card_ref:`)
   and Sphinx's `:cite:`, `:person:`, and `:term:` inline role occurrences, grouping
   parallel companion tracks (e.g., `LA · EN`, `EL · EN`) automatically.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.bibliography.TRACK_SUFFIX_RE
   photon_platform.publish.bibliography.BARE_TRACK_STEMS


Classes
-------

.. autoapisummary::

   photon_platform.publish.bibliography.RoleOccurrence


Functions
---------

.. autoapisummary::

   photon_platform.publish.bibliography.format_chicago
   photon_platform.publish.bibliography.format_mla
   photon_platform.publish.bibliography.format_apa
   photon_platform.publish.bibliography.format_bibtex
   photon_platform.publish.bibliography.format_all_citations
   photon_platform.publish.bibliography.render_citation_formats_html
   photon_platform.publish.bibliography.collect_apparatus_occurrences
   photon_platform.publish.bibliography.render_backlinks_html
   photon_platform.publish.bibliography.process_bibliography_nodes
   photon_platform.publish.bibliography.emit_bibliography_bib
   photon_platform.publish.bibliography.setup


Module Contents
---------------

.. py:function:: format_chicago(card: photon_platform.publish.cards.Card) -> str

   Format a Chicago Notes & Bibliography entry from `card`.


.. py:function:: format_mla(card: photon_platform.publish.cards.Card) -> str

   Format an MLA 9th-edition citation entry from `card`.


.. py:function:: format_apa(card: photon_platform.publish.cards.Card) -> str

   Format an APA 7th-edition citation entry from `card`.


.. py:function:: format_bibtex(card: photon_platform.publish.cards.Card) -> str

   Format a standards-compliant BibTeX entry from `card`.


.. py:function:: format_all_citations(card: photon_platform.publish.cards.Card) -> dict[str, str]

.. py:function:: render_citation_formats_html(card: photon_platform.publish.cards.Card, *, title: str = 'Cite This Work', extra_class: str = '') -> str

   Render interactive Chicago / MLA / APA / BibTeX tabs for a detail record.


.. py:data:: TRACK_SUFFIX_RE

.. py:class:: RoleOccurrence

   .. py:attribute:: role_type
      :type:  str


   .. py:attribute:: target
      :type:  str


   .. py:attribute:: slug
      :type:  str


   .. py:attribute:: docname
      :type:  str


   .. py:attribute:: doc_title
      :type:  str


   .. py:attribute:: section_title
      :type:  str


   .. py:attribute:: base_group
      :type:  str


   .. py:attribute:: track_label
      :type:  str


   .. py:attribute:: occ_id
      :type:  str


   .. py:attribute:: index_in_doc
      :type:  int


.. py:data:: BARE_TRACK_STEMS

.. py:function:: collect_apparatus_occurrences(app: Any, env: Any) -> None

   Scan all doctrees on `env-updated` to build the automated bidirectional backlink index.


.. py:function:: render_backlinks_html(builder: Any, fromdocname: str, occurrences: list[RoleOccurrence], *, title: str = 'Occurrences in This Work', extra_class: str = '') -> str

   Render Hoenen-style passage backlinks grouped by `(base_group, index_in_doc)` with paired tracks.


.. py:function:: process_bibliography_nodes(app: Any, doctree: docutils.nodes.document, fromdocname: str) -> None

   Resolve `PendingCitationFormats` and `PendingBacklinks` nodes on `doctree-resolved`.


.. py:function:: emit_bibliography_bib(app: Any, exception: Exception | None) -> None

   Export `docs/bibliography.bib` when the build contains bibliographic work records.


.. py:function:: setup(app: Any) -> dict[str, Any]

