Taxonomy & Indexes
==================

.. meta::
    :description: Explanation of the auto-generated taxonomy system including tags, categories, and types.
    :keywords: taxonomy, tags, categories, types, index

Publish automatically generates taxonomy pages for **Tags**, **Categories**, and **Types** based on the metadata in your RST files.

Adding Metadata
---------------

To add metadata to a page, use the standard RST field list at the top of the file:

.. code-block:: rst

    :tags: sphinx, python, documentation
    :categories: development, guide
    :type: article

Auto-Generated Pages
--------------------

Based on the metadata above, Publish will generate:

*   **Tag Pages:** ``tags/sphinx.html``, ``tags/python.html``, etc.
*   **Category Pages:** ``categories/development.html``, etc.
*   **Type Pages:** ``types/article.html``

These pages list all content associated with that term.

Standard Indexes
----------------

Sphinx also provides standard indexes:

*   :ref:`genindex` (General Index)
*   :ref:`modindex` (Module Index)
*   :ref:`search` (Search Page)
