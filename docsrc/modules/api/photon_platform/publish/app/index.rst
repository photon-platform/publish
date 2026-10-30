photon_platform.publish.app
===========================

.. py:module:: photon_platform.publish.app

.. autoapi-nested-parse::

   Command-line interface for the publish tool.



Functions
---------

.. autoapisummary::

   photon_platform.publish.app.cli
   photon_platform.publish.app.build
   photon_platform.publish.app.test
   photon_platform.publish.app.epub
   photon_platform.publish.app.folio


Module Contents
---------------

.. py:function:: cli()

   A tool to streamline and enhance the Sphinx documentation framework.


.. py:function:: build()

   Builds the documentation.


.. py:function:: test(port)

   Builds and serves the documentation locally.


.. py:function:: epub(book, output)

   Builds an EPUB 3 edition for the book subtree in docsrc/.


.. py:function:: folio(host, port, root, title, edition, debug)

   Launches the interactive Folio Review & Vetting web application for resources/.


