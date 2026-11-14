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
   photon_platform.publish.app.clean
   photon_platform.publish.app.test
   photon_platform.publish.app.epub
   photon_platform.publish.app.mcp
   photon_platform.publish.app.folio
   photon_platform.publish.app.folio_links_cmd


Module Contents
---------------

.. py:function:: cli()

   A tool to streamline and enhance the Sphinx documentation framework.


.. py:function:: build(repo, clean_build, jobs, as_json)

   Builds the documentation (incremental by default; pass --clean for full rebuild).


.. py:function:: clean(repo)

   Removes the docs/ build directory and generated autoapi files.


.. py:function:: test(port)

   Builds and serves the documentation locally.


.. py:function:: epub(repo, book, output)

   Builds an EPUB 3 edition for the book subtree in docsrc/.


.. py:function:: mcp()

   Launches the Model Context Protocol (MCP) JSON-RPC stdio server for publish.


.. py:function:: folio(host, port, root, title, edition, debug)

   Launches the interactive Folio Review & Vetting web application for resources/.


.. py:function:: folio_links_cmd(repo, optimize_scans, grayscale, as_json)

   Audits primary-source .. folio:: and :folio: links (and optionally optimizes scans).


