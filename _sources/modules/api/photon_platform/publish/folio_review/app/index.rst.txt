photon_platform.publish.folio_review.app
========================================

.. py:module:: photon_platform.publish.folio_review.app

.. autoapi-nested-parse::

   Flask web application for Folio Review & Vetting.

   Run via CLI:
       publish folio
       publish folio --port 5050



Attributes
----------

.. autoapisummary::

   photon_platform.publish.folio_review.app.Flask


Functions
---------

.. autoapisummary::

   photon_platform.publish.folio_review.app.create_app
   photon_platform.publish.folio_review.app.main


Module Contents
---------------

.. py:data:: Flask
   :value: None


.. py:function:: create_app(root_dir: Optional[pathlib.Path] = None, project_title: Optional[str] = None, edition_label: Optional[str] = None) -> flask.Flask

   Create and configure the Flask review application.


.. py:function:: main() -> None

   CLI entry point for launching the Folio Review web application.


