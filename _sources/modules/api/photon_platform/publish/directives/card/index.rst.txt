photon_platform.publish.directives.card
=======================================

.. py:module:: photon_platform.publish.directives.card

.. autoapi-nested-parse::

   Directives for Page Cards, Summaries, Standard Citations, and Automated Backlinks.

   Provides:

   - ``.. summary::`` — Visible editorial lead block that also populates the page's ``Card.description``
   - ``.. card:: <address>`` — Embeds any local or cross-project (Intersphinx + ``cards.json``) Card
     with optional local contextual body note
   - ``.. citation-formats::`` — Renders auto-generated Chicago/MLA/APA/BibTeX tabs for a record
   - ``.. backlinks::`` — Renders automated Hoenen-style passage backlinks for a person or citation



Classes
-------

.. autoapisummary::

   photon_platform.publish.directives.card.PendingCard
   photon_platform.publish.directives.card.PendingCitationFormats
   photon_platform.publish.directives.card.PendingBacklinks
   photon_platform.publish.directives.card.SummaryDirective
   photon_platform.publish.directives.card.CardDirective
   photon_platform.publish.directives.card.CitationFormatsDirective
   photon_platform.publish.directives.card.BacklinksDirective


Functions
---------

.. autoapisummary::

   photon_platform.publish.directives.card.render_card_html
   photon_platform.publish.directives.card.process_cards
   photon_platform.publish.directives.card.setup


Module Contents
---------------

.. py:class:: PendingCard(rawsource: str = '', *children, **attributes: Any)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   Deferred placeholder resolved on `doctree-resolved` once all cards are built.


.. py:class:: PendingCitationFormats(rawsource: str = '', *children, **attributes: Any)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   Deferred placeholder for standard citation format tabs (Chicago/MLA/APA/BibTeX).


.. py:class:: PendingBacklinks(rawsource: str = '', *children, **attributes: Any)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   Deferred placeholder for automated bidirectional apparatus backlinks.


.. py:class:: SummaryDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Editorial summary block that renders cleanly on the page AND feeds `Card.description`.

   Use `:hidden:` if you want multi-line editorial card copy without repeating it in body prose.


   .. py:attribute:: has_content
      :value: True


      May the directive have content?


   .. py:attribute:: option_spec
      :type:  ClassVar[dict[str, Any]]

      Mapping of option names to validator functions.


   .. py:method:: run() -> list[docutils.nodes.Node]


.. py:class:: CardDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Embed a formatted Card for any local page or cross-project Intersphinx address.

   Example::

       .. card:: aristotle:analytica_posteriora/index
          :variant: banner

          Cited 5 times in Hoenen's Caput I, III, and VII.


   .. py:attribute:: required_arguments
      :value: 1


      Number of required directive arguments.


   .. py:attribute:: optional_arguments
      :value: 0


      Number of optional arguments after the required arguments.


   .. py:attribute:: final_argument_whitespace
      :value: True


      May the final argument contain whitespace?


   .. py:attribute:: has_content
      :value: True


      May the directive have content?


   .. py:attribute:: option_spec
      :type:  ClassVar[dict[str, Any]]

      Mapping of option names to validator functions.


   .. py:method:: run() -> list[docutils.nodes.Node]


.. py:class:: CitationFormatsDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Render auto-generated Chicago, MLA, APA, and BibTeX citations for the current record
   (or an optional referenced Card address).


   .. py:attribute:: required_arguments
      :value: 0


      Number of required directive arguments.


   .. py:attribute:: optional_arguments
      :value: 1


      Number of optional arguments after the required arguments.


   .. py:attribute:: final_argument_whitespace
      :value: True


      May the final argument contain whitespace?


   .. py:attribute:: has_content
      :value: False


      May the directive have content?


   .. py:attribute:: option_spec
      :type:  ClassVar[dict[str, Any]]

      Mapping of option names to validator functions.


   .. py:method:: run() -> list[docutils.nodes.Node]


.. py:class:: BacklinksDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Render automated passage backlinks (grouped by chapter & paired tracks) for a person/work.


   .. py:attribute:: required_arguments
      :value: 0


      Number of required directive arguments.


   .. py:attribute:: optional_arguments
      :value: 1


      Number of optional arguments after the required arguments.


   .. py:attribute:: final_argument_whitespace
      :value: True


      May the final argument contain whitespace?


   .. py:attribute:: has_content
      :value: False


      May the directive have content?


   .. py:attribute:: option_spec
      :type:  ClassVar[dict[str, Any]]

      Mapping of option names to validator functions.


   .. py:method:: run() -> list[docutils.nodes.Node]


.. py:function:: render_card_html(builder: Any, fromdocname: str, card: photon_platform.publish.cards.Card, *, variant: str = 'banner', extra_class: str = '', note_label: str = 'In This Work', is_directory: bool = False) -> str

   Render a `Card` using the unified `components/card.html` Jinja template.


.. py:function:: process_cards(app: Any, doctree: docutils.nodes.document, fromdocname: str) -> None

   Resolve `PendingCard` nodes on `doctree-resolved`.


.. py:function:: setup(app: Any) -> dict[str, Any]

