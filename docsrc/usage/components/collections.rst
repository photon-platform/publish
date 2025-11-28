Collections
===========

.. meta::
    :description: Documentation and examples for the collection directive.
    :keywords: collection, directive, sphinx, aggregation

The ``collection`` directive is a powerful tool for aggregating and listing content. It allows you to create dynamic indexes of your content based on metadata.

Basic Usage
-----------

To list all pages in the current directory and subdirectories:

.. code-block:: rst

    .. collection::

Filtering by Type
-----------------

You can filter content by the ``type`` metadata field. For example, to list only logs:

.. code-block:: rst

    .. collection::
        :type: log

Sorting and Limiting
--------------------

You can sort the collection by any metadata field and limit the number of items shown.

.. code-block:: rst

    .. collection::
        :sort: date
        :reverse:
        :limit: 5

Custom Templates
----------------

You can specify a custom template to render the collection.

.. code-block:: rst

    .. collection::
        :template: custom_list.html

Example
-------

Here is a live example of a collection listing the most recent logs (if any exist):

.. collection::
    :type: log
    :limit: 3
    :sort: date
    :reverse:
