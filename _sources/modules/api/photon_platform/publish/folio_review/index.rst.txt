photon_platform.publish.folio_review
====================================

.. py:module:: photon_platform.publish.folio_review

.. autoapi-nested-parse::

   Folio Review & Vetting Web Application for PHOTON Publish.

   Provides an interactive local web interface (`publish folio`) to inspect folio scans,
   read and edit side-by-side RST/Markdown transcriptions and notes, verify graphic
   bounding boxes on full-page scans, and track folio-by-folio vetting status
   exclusively within a repository's `resources/` directory.



Submodules
----------

.. toctree::
   :maxdepth: 1

   /modules/api/photon_platform/publish/folio_review/app/index
   /modules/api/photon_platform/publish/folio_review/reviews/index
   /modules/api/photon_platform/publish/folio_review/rst_utils/index
   /modules/api/photon_platform/publish/folio_review/scanner/index


Classes
-------

.. autoapisummary::

   photon_platform.publish.folio_review.ReviewManager
   photon_platform.publish.folio_review.FolioScanner


Functions
---------

.. autoapisummary::

   photon_platform.publish.folio_review.create_app
   photon_platform.publish.folio_review.main
   photon_platform.publish.folio_review.discover_edition_root
   photon_platform.publish.folio_review.infer_project_and_edition


Package Contents
----------------

.. py:function:: create_app(root_dir: Optional[pathlib.Path] = None, project_title: Optional[str] = None, edition_label: Optional[str] = None) -> flask.Flask

   Create and configure the Flask review application.


.. py:function:: main() -> None

   CLI entry point for launching the Folio Review web application.


.. py:class:: ReviewManager(storage_path: Optional[pathlib.Path] = None)

   Manages reading and writing vetting / review records for folios.


   .. py:method:: get_review(volume: str, folio: str) -> Dict[str, Any]

      Get review record for a specific folio, returning default if unreviewed.



   .. py:method:: set_review(volume: str, folio: str, status: str, checklist: Optional[Dict[str, bool]] = None, notes: str = '', reviewer: Optional[str] = 'phi') -> Dict[str, Any]

      Save or update review record for a specific folio.



   .. py:method:: get_all_reviews() -> Dict[str, Dict[str, Any]]

      Return all stored reviews.



   .. py:method:: get_review_stats() -> Dict[str, int]

      Return count breakdown of review statuses.



.. py:class:: FolioScanner(root_dir: Optional[pathlib.Path] = None)

   Scans `volume_*` or book directories under an edition root and indexes all folio assets.


   .. py:attribute:: root_dir


   .. py:property:: volumes
      :type: List[Dict[str, str]]


      Discover `volume_*` directories dynamically, or treat the book directory itself as the unit.


   .. py:method:: scan(force: bool = False) -> List[Dict[str, Any]]

      Scan all volumes/books and return sorted list of folio metadata dicts.



   .. py:method:: get_folio_detail(volume: str, folio: str) -> Optional[Dict[str, Any]]

      Get full details for a single folio, including rendered RST/Markdown and Notes.



   .. py:attribute:: get_folio


   .. py:method:: get_apparatus(force: bool = False) -> Dict[str, Dict[str, Any]]

      Load or build the edition's citations, glossary, and persons registries.



   .. py:method:: get_neighbors(volume: str, folio: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]

      Return (prev_folio, next_folio) in the ordered sequence.



   .. py:method:: get_summary_stats() -> Dict[str, Any]

      Compute aggregate statistics per volume and across the entire edition.



.. py:function:: discover_edition_root(root_path: Optional[pathlib.Path] = None) -> pathlib.Path

   Locate the edition or book root directory inside `resources/`.

   Never inspects `docsrc/`. Supports both multi-volume editions (`volume_*`)
   and single-volume book directories (`resources/<book>/`) containing folio PNGs.


.. py:function:: infer_project_and_edition(edition_root: pathlib.Path, project_title: Optional[str] = None, edition_label: Optional[str] = None) -> Tuple[str, str]

   Infer `(project_title, edition_label)` from the `resources/` path without reading `docsrc/`.


