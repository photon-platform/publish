photon_platform.publish.cards
=============================

.. py:module:: photon_platform.publish.cards

.. autoapi-nested-parse::

   Unified Page Card model, `cards.json` manifest emitter, and Intersphinx-backed CardRegistry.

   Every Sphinx document built by `photon-platform/publish` resolves to one canonical
   `Card` record with:

   - Hybrid curated description (`:description:` > `.. summary::` > `.. enunciation::` > fallback)
   - Dual visual slots: small project/org `emblem` medallion + larger `image` hero/diagram
   - Structured facets (author, dates, era, languages, tags, bibliographic metadata)
   - Record inheritance via `:card_ref:` (pulling canonical identity from another page or site)
   - Automatic export to `docs/cards.json` alongside `docs/objects.inv`
   - Lazy cross-project resolution piggybacking on `intersphinx_mapping` (local sibling first,
     cached HTTPS fallback, graceful degradation to `objects.inv`).



Attributes
----------

.. autoapisummary::

   photon_platform.publish.cards.SCHEMA_VERSION
   photon_platform.publish.cards.BIB_FIELD_KEYS


Classes
-------

.. autoapisummary::

   photon_platform.publish.cards.Card
   photon_platform.publish.cards.CardRegistry


Functions
---------

.. autoapisummary::

   photon_platform.publish.cards.resolve_site_emblem
   photon_platform.publish.cards.resolve_document_card
   photon_platform.publish.cards.get_card_registry
   photon_platform.publish.cards.build_all_cards
   photon_platform.publish.cards.emit_cards_manifest
   photon_platform.publish.cards.setup


Module Contents
---------------

.. py:data:: SCHEMA_VERSION
   :value: 'photon.card.v1'


.. py:data:: BIB_FIELD_KEYS
   :value: ('work_type', 'editors', 'editor', 'translators', 'translator', 'publisher', 'place', 'series',...


.. py:class:: Card

   Canonical representation of any page or entity record across publish.


   .. py:attribute:: id
      :type:  str


   .. py:attribute:: docname
      :type:  str


   .. py:attribute:: title
      :type:  str


   .. py:attribute:: type
      :type:  str
      :value: 'article'



   .. py:attribute:: inventory
      :type:  str
      :value: ''



   .. py:attribute:: is_remote
      :type:  bool
      :value: False



   .. py:attribute:: url
      :type:  str
      :value: ''



   .. py:attribute:: subtitle
      :type:  str
      :value: ''



   .. py:attribute:: kicker
      :type:  str
      :value: ''



   .. py:attribute:: description
      :type:  str
      :value: ''



   .. py:attribute:: description_html
      :type:  str
      :value: ''



   .. py:attribute:: description_source
      :type:  str
      :value: 'empty'



   .. py:attribute:: emblem
      :type:  str
      :value: ''



   .. py:attribute:: emblem_svg
      :type:  str
      :value: ''



   .. py:attribute:: image
      :type:  str
      :value: ''



   .. py:attribute:: image_alt
      :type:  str
      :value: ''



   .. py:attribute:: image_width
      :type:  str
      :value: ''



   .. py:attribute:: image_svg
      :type:  str
      :value: ''



   .. py:attribute:: social_image
      :type:  str
      :value: ''



   .. py:attribute:: author
      :type:  str
      :value: ''



   .. py:attribute:: author_doc
      :type:  str
      :value: ''



   .. py:attribute:: author_ref
      :type:  str
      :value: ''



   .. py:attribute:: year
      :type:  Any
      :value: None



   .. py:attribute:: year_sort
      :type:  int | None
      :value: None



   .. py:attribute:: year_label
      :type:  str
      :value: ''



   .. py:attribute:: year_display
      :type:  str
      :value: ''



   .. py:attribute:: death_year
      :type:  Any
      :value: None



   .. py:attribute:: death_year_sort
      :type:  int | None
      :value: None



   .. py:attribute:: death_label
      :type:  str
      :value: ''



   .. py:attribute:: lifespan
      :type:  str
      :value: ''



   .. py:attribute:: edition_year
      :type:  Any
      :value: None



   .. py:attribute:: era
      :type:  str
      :value: ''



   .. py:attribute:: series
      :type:  str
      :value: ''



   .. py:attribute:: native_title
      :type:  str
      :value: ''



   .. py:attribute:: languages
      :type:  list[str]
      :value: []



   .. py:attribute:: tags
      :type:  list[str]
      :value: []



   .. py:attribute:: categories
      :type:  list[str]
      :value: []



   .. py:attribute:: date
      :type:  str
      :value: ''



   .. py:attribute:: published_at
      :type:  str
      :value: ''



   .. py:attribute:: site_url
      :type:  str
      :value: ''



   .. py:attribute:: github_url
      :type:  str
      :value: ''



   .. py:attribute:: companion_tracks
      :type:  list[dict[str, Any]]
      :value: []



   .. py:attribute:: bib
      :type:  dict[str, Any]


   .. py:attribute:: labels
      :type:  list[str]
      :value: []



   .. py:attribute:: card_ref
      :type:  str
      :value: ''



   .. py:attribute:: local_note_html
      :type:  str
      :value: ''



   .. py:attribute:: meta
      :type:  dict[str, Any]


   .. py:method:: to_manifest_dict(base_url: str = '') -> dict[str, Any]

      Serialize for `docs/cards.json` (compact, portable, absolute URLs).



   .. py:method:: from_manifest_dict(raw: dict[str, Any], *, inventory: str = '', site_info: dict[str, Any] | None = None) -> Card
      :classmethod:


      Hydrate a remote `Card` from a `cards.json` entry.



   .. py:method:: to_template_dict() -> dict[str, Any]

      Produce a Jinja-friendly dictionary compatible with both `components/card.html`
      and legacy `collection/index.html` / `collection/directory.html` templates.



   .. py:method:: tooltip_text() -> str

      Concise hover tooltip summary for inline `:person:`, `:cite:`, `:term:` links.



.. py:function:: resolve_site_emblem(env: Any, meta: dict[str, Any] | None = None) -> tuple[str, str]

   Resolve the small project/org medallion `(rel_uri, inline_svg)`.


.. py:function:: resolve_document_card(env: Any, builder: Any, docname: str, doctree: docutils.nodes.document | None = None, *, registry: CardRegistry | None = None) -> Card

   Resolve a single canonical `Card` for local document `docname`.


.. py:class:: CardRegistry(app: Any)

   Lazy, Intersphinx-backed Card resolver across local docs and sister sites.


   .. py:attribute:: app


   .. py:attribute:: env


   .. py:attribute:: builder


   .. py:method:: load_manifest(inventory: str) -> dict[str, Any] | None

      Lazily load `cards.json` for `inventory` (local sibling first, HTTPS cached fallback).



   .. py:method:: resolve(address: str, *, fromdocname: str = '') -> Card | None

      Resolve a local or cross-project (`inventory:target`) card address.



   .. py:method:: query(pattern: str) -> list[Card]

      Query multiple remote cards using `inv:*`, `inv:prefix/*`, or `inv:type=book`.



   .. py:method:: resolve_by_role(role_type: str, key: str) -> Card | None

      Resolve an apparatus role (`person`, `cite`, `term`) across configured inventories.



.. py:function:: get_card_registry(app: Any) -> CardRegistry

   Get or create the per-build `CardRegistry` instance (stored on `app`, never pickled in `env`).


.. py:function:: build_all_cards(app: Any, env: Any) -> None

   Resolve `Card` objects for every document in `env.found_docs` on `env-updated`.


.. py:function:: emit_cards_manifest(app: Any, exception: Exception | None) -> None

   Write `docs/cards.json` right beside `docs/objects.inv` after HTML builds.


.. py:function:: setup(app: Any) -> dict[str, Any]

   Register unified Card resolution and `cards.json` export with Sphinx.


