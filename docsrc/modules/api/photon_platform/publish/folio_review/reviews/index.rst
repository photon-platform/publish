photon_platform.publish.folio_review.reviews
============================================

.. py:module:: photon_platform.publish.folio_review.reviews

.. autoapi-nested-parse::

   Persistent review and vetting status tracker for folios.

   Stores vetting checklist, review status, and notes in `folio_reviews.json`
   inside the edition's `resources/<edition>/` directory.



Classes
-------

.. autoapisummary::

   photon_platform.publish.folio_review.reviews.ReviewManager


Module Contents
---------------

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



