Code Documentation
==================

.. meta::
    :description: Best practices for code documentation and docstrings.
    :keywords: autodoc, docstrings, python, api

Publish integrates with ``sphinx.ext.autodoc`` and ``sphinx-autoapi`` to automatically generate documentation from your code.

Docstring Best Practices
------------------------

We recommend using the **Google Style** docstrings for clarity and readability.

Example:

.. code-block:: python

    def connect_to_database(host: str, port: int) -> bool:
        """
        Connects to the database server.

        Args:
            host (str): The hostname or IP address.
            port (int): The port number.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        pass

Live Example
------------

Here is the documentation for the ``CollectionDirective`` class in this project, automatically extracted from the source code:

.. autoclass:: photon_platform.publish.directives.collection.CollectionDirective
    :members:
    :noindex:
