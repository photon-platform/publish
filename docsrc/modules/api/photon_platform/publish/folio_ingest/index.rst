photon_platform.publish.folio_ingest
====================================

.. py:module:: photon_platform.publish.folio_ingest

.. autoapi-nested-parse::

   Deterministic archival PDF ingestion: 300-DPI folio PNG scans, text streams, embedded graphics, and folio_map.json.



Functions
---------

.. autoapisummary::

   photon_platform.publish.folio_ingest.ingest_single_pdf
   photon_platform.publish.folio_ingest.ingest_repo_pdfs


Module Contents
---------------

.. py:function:: ingest_single_pdf(repo_root: pathlib.Path, pdf_path: pathlib.Path, *, edition_slug: str, dpi: int = 300, preserve_color: bool = False, extract_text: bool = True, extract_graphics: bool = True, extract_vector_svg: bool = False, first_page: int | None = None, last_page: int | None = None, force: bool = False) -> dict[str, Any]

   Render 4-digit `<NNNN>.png` folio scans, harvest text/graphics, and update `folio_map.json`.


.. py:function:: ingest_repo_pdfs(repo_root: str | pathlib.Path, *, pdf: str | pathlib.Path | None = None, edition: str | None = None, dpi: int = 300, preserve_color: bool = False, extract_text: bool = True, extract_graphics: bool = True, extract_vector_svg: bool = False, first_page: int | None = None, last_page: int | None = None, force: bool = False) -> dict[str, Any]

   Ingest one or all archival PDFs under `repo_root/resources/`.


