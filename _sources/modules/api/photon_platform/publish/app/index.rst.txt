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
   photon_platform.publish.app.serve
   photon_platform.publish.app.epub
   photon_platform.publish.app.mcp
   photon_platform.publish.app.folio
   photon_platform.publish.app.folio_links_cmd
   photon_platform.publish.app.social_banner_cmd
   photon_platform.publish.app.folio_ingest_cmd
   photon_platform.publish.app.audit_book_cmd


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


.. py:function:: serve(repo, host, port, build_first, no_browser)

   Serves docs/ on the first open port >= 8000 and launches Chrome.


.. py:function:: epub(repo, book, output)

   Builds an EPUB 3 edition for the book subtree in docsrc/.


.. py:function:: mcp()

   Launches the Model Context Protocol (MCP) JSON-RPC stdio server for publish.


.. py:function:: folio(host, port, root, title, edition, debug)

   Launches the interactive Folio Review & Vetting web application for resources/.


.. py:function:: folio_links_cmd(repo, optimize_scans, grayscale, as_json)

   Audits primary-source .. folio:: and :folio: links (and optionally optimizes scans).


.. py:function:: social_banner_cmd(repo, force, as_json)

   Generates dedicated 1200x630 sharing-only PNG banners in docsrc/_static/social/.


.. py:function:: folio_ingest_cmd(repo, pdf, edition, dpi, preserve_color, vector_svg, first_page, last_page, force, as_json)

   Renders 300-DPI <NNNN>.png folios, extracts embedded text & graphics, and updates folio_map.json.


.. py:function:: audit_book_cmd(repo, as_json)

   Audits Book Codex hierarchy, English-first tracks, collections, and apparatus placement.


