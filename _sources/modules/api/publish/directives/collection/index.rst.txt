publish.directives.collection
=============================

.. py:module:: publish.directives.collection


Classes
-------

.. autoapisummary::

   publish.directives.collection.CollectionDirective


Functions
---------

.. autoapisummary::

   publish.directives.collection.to_numeric
   publish.directives.collection.collect_metadata
   publish.directives.collection.generate_taxonomy_pages
   publish.directives.collection.build_nav_links
   publish.directives.collection.setup


Module Contents
---------------

.. py:function:: to_numeric(value)

   Converts a value to a numeric type if possible, trying int then float.


.. py:class:: CollectionDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   A base class for Sphinx directives.

   This class provides helper methods for Sphinx directives.

   .. versionadded:: 1.8

   .. note:: The subclasses of this class might not work with docutils.
             This class is strongly coupled with Sphinx.


   .. py:attribute:: has_content
      :value: False


      May the directive have content?



   .. py:attribute:: option_spec

      Mapping of option names to validator functions.



   .. py:method:: run() -> list

      Process the collection directive, discover and sort documents,
      and render them using a Jinja2 template.



.. py:function:: collect_metadata(app, env)

   Collect all tags and categories from document metadata.


.. py:function:: generate_taxonomy_pages(app)

   Dynamically generate pages for each tag and category.


.. py:function:: build_nav_links(app, pagename: str, templatename: str, context: dict, doctree) -> None

   Build navigation links and add tags/categories to the context.


.. py:function:: setup(app) -> dict

   Register directives and connect to Sphinx events.


