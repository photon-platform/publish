photon_platform.publish.directives.collection
=============================================

.. py:module:: photon_platform.publish.directives.collection


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

.. py:function:: to_numeric(value)

   Converts a value to a numeric type if possible, trying int then float.


.. py:function:: safe_numeric(value, default=999)

   Safely converts a value to a numeric type for sorting.
   Returns default if conversion fails.


.. py:class:: PendingCollection(rawsource='', *children, **attributes)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   A placeholder node for a collection that will be rendered
   after all documents have been read and metadata is available.


.. py:class:: CollectionDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   A base class for Sphinx directives.

   This class provides helper methods for Sphinx directives.

   .. versionadded:: 1.8

   .. note:: The subclasses of this class might not work with docutils.
             This class is strongly coupled with Sphinx.


   .. py:attribute:: has_content
      :type:  bool
      :value: False


      May the directive have content?


   .. py:attribute:: option_spec
      :type:  Dict[str, Any]

      Mapping of option names to validator functions.


   .. py:method:: run()

      Process the collection directive.

      Instead of rendering immediately, we:
      1. Discover all relevant files.
      2. Add them to a hidden toctree so Sphinx knows about them (fixes "not in toctree" warnings).
      3. Return a PendingCollection node to defer rendering until metadata is ready.



.. py:function:: process_collections(app, doctree, fromdocname)

   Resolve PendingCollection nodes into actual HTML content.
   This runs on 'doctree-resolved', when all metadata is available.


.. py:function:: collect_metadata(app, env)

   Collect all tags and categories from document metadata.


.. py:function:: generate_taxonomy_pages(app)

   Dynamically generate pages for each tag and category.


.. py:function:: build_nav_links(app, pagename, templatename, context, doctree)

   Build navigation links and add tags/categories to the context.


.. py:function:: peek_metadata(filepath)

   Peek at the beginning of a file to extract navigation metadata.
   This enables sorting before Sphinx has fully processed the environment.


.. py:function:: inject_root_navigation(app, docname, source)

   Automatically inject a hidden toctree into the master document (Root).
   This includes any document with :navigation: header or :navigation: footer.


.. py:function:: setup(app)

   Register directives and connect to Sphinx events.


