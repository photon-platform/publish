photon_platform.publish.directives.collection
=============================================

.. py:module:: photon_platform.publish.directives.collection

.. autoapi-nested-parse::

   Directive for creating content collections.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.directives.collection.picture_node


Classes
-------

.. autoapisummary::

   photon_platform.publish.directives.collection.PendingCollection
   photon_platform.publish.directives.collection.CollectionDirective


Functions
---------

.. autoapisummary::

   photon_platform.publish.directives.collection.to_numeric
   photon_platform.publish.directives.collection.safe_numeric
   photon_platform.publish.directives.collection.process_collections
   photon_platform.publish.directives.collection.collect_metadata
   photon_platform.publish.directives.collection.generate_taxonomy_pages
   photon_platform.publish.directives.collection.build_nav_links
   photon_platform.publish.directives.collection.peek_metadata
   photon_platform.publish.directives.collection.inject_root_navigation
   photon_platform.publish.directives.collection.setup


Module Contents
---------------

.. py:data:: picture_node
   :value: None


.. py:function:: to_numeric(value: Any) -> int | float | Any

   Convert a value to a numeric type if possible, trying int then float.

   :param value: The value to convert.

   :returns: The converted numeric value, or the original value if conversion fails.


.. py:function:: safe_numeric(value: Any, default: int | float = 999) -> int | float

   Safely convert a value to a numeric type for sorting.

   :param value: The value to convert.
   :param default: The default value to return if conversion fails.

   :returns: The converted numeric value or the default.


.. py:class:: PendingCollection(rawsource='', *children, **attributes)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   A placeholder node for a collection.

   This node will be rendered after all documents have been read and metadata is available.


.. py:class:: CollectionDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Directive to insert a collection of articles.


   .. py:attribute:: has_content
      :type:  bool
      :value: False


      May the directive have content?


   .. py:attribute:: option_spec
      :type:  Dict[str, Any]

      Mapping of option names to validator functions.


   .. py:method:: run() -> List[docutils.nodes.Node]

      Process the collection directive.

      Instead of rendering immediately, this method:
      1. Discovers all relevant files.
      2. Adds them to a hidden toctree so Sphinx knows about them (fixes "not in toctree" warnings).
      3. Returns a PendingCollection node to defer rendering until metadata is ready.

      :returns: A list containing the PendingCollection node and a hidden toctree node.



.. py:function:: process_collections(app: Any, doctree: docutils.nodes.document, fromdocname: str) -> None

   Resolve PendingCollection nodes into actual HTML content.

   This runs on 'doctree-resolved', when all metadata is available.

   :param app: The Sphinx application instance.
   :param doctree: The document tree.
   :param fromdocname: The document name.


.. py:function:: collect_metadata(app: Any, env: Any) -> None

   Collect all tags and categories from document metadata.

   :param app: The Sphinx application instance.
   :param env: The build environment.


.. py:function:: generate_taxonomy_pages(app: Any) -> Any

   Dynamically generate pages for each tag and category.

   :param app: The Sphinx application instance.

   :Yields: Tuple containing context, template name, and output path for each page.


.. py:function:: build_nav_links(app: Any, pagename: str, templatename: str, context: Dict[str, Any], doctree: docutils.nodes.document) -> None

   Build navigation links and add tags/categories to the context.

   :param app: The Sphinx application instance.
   :param pagename: The name of the page.
   :param templatename: The name of the template.
   :param context: The context for rendering.
   :param doctree: The document tree.


.. py:function:: peek_metadata(filepath: str) -> Dict[str, str]

   Peek at the beginning of a file to extract navigation metadata.

   This enables sorting before Sphinx has fully processed the environment.

   :param filepath: The path to the file to peek at.

   :returns: A dictionary containing the extracted metadata.


.. py:function:: inject_root_navigation(app: Any, docname: str, source: List[str]) -> None

   Automatically inject a hidden toctree into the master document (Root).

   This includes any document with :navigation: header or :navigation: footer.

   :param app: The Sphinx application instance.
   :param docname: The name of the document.
   :param source: The list of source strings (mutable).


.. py:function:: setup(app: Any) -> Dict[str, Any]

   Register directives and connect to Sphinx events.

   :param app: The Sphinx application instance.

   :returns: A dictionary containing extension metadata.


