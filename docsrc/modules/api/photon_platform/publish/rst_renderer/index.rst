photon_platform.publish.rst_renderer
====================================

.. py:module:: photon_platform.publish.rst_renderer

.. autoapi-nested-parse::

   Fast, standalone in-memory Docutils RST renderer and metadata parser for Scriptorium and folio_review.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.rst_renderer.parse_rst_frontmatter
   photon_platform.publish.rst_renderer.render_rst_to_html


Functions
---------

.. autoapisummary::

   photon_platform.publish.rst_renderer.ensure_standalone_extensions
   photon_platform.publish.rst_renderer.parse_rst_metadata
   photon_platform.publish.rst_renderer.render_rst_html


Module Contents
---------------

.. py:function:: ensure_standalone_extensions() -> None

   Ensure all publish directives and roles are registered with Docutils.


.. py:function:: parse_rst_metadata(rst_text: str) -> Tuple[Dict[str, Any], str]

   Extract the top `:key: value` field list from an RST document.

   Converts standard keys (`:folio:`, `:page:`, `:volume:`, `:book:`, `:section:`,
   `:title:`, `:canonical_id:`, `:type:`, `:tags:`, `:dependencies:`) and returns
   ``(metadata_dict, body_rst)``.


.. py:function:: render_rst_html(rst_text: str) -> str

   Render extended Scriptorium RST source to an HTML5 fragment string in memory.


.. py:data:: parse_rst_frontmatter

.. py:data:: render_rst_to_html

