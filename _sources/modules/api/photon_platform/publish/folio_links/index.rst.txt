photon_platform.publish.folio_links
===================================

.. py:module:: photon_platform.publish.folio_links

.. autoapi-nested-parse::

   Primary-source folio URL resolution, repository link auditing, and lossless scan optimization.



Classes
-------

.. autoapisummary::

   photon_platform.publish.folio_links.FolioAuditReport


Functions
---------

.. autoapisummary::

   photon_platform.publish.folio_links.load_folio_scan_index
   photon_platform.publish.folio_links.load_folio_map_index
   photon_platform.publish.folio_links.resolve_folio_url
   photon_platform.publish.folio_links.audit_repo_folio_links
   photon_platform.publish.folio_links.optimize_repo_folio_scans


Module Contents
---------------

.. py:function:: load_folio_scan_index(env: Any, project_root: pathlib.Path | None = None) -> dict[tuple[str, str], str]

   Index non-ignored 4-digit `.png`/`.jpg` scan files under `resources/` by `(scope_key, stem)`.

   :param env: Sphinx BuildEnvironment (optional when invoked from CLI).
   :param project_root: Explicit repository root override.

   :returns: Mapping of `(scope_key, 4_digit_stem)` to repo-relative POSIX path.


.. py:function:: load_folio_map_index(env: Any, project_root: pathlib.Path | None = None) -> dict[str, Any]

   Load and merge all non-ignored `resources/**/folio_map.json` manifests.


.. py:function:: resolve_folio_url(env: Any, current_docname: str, folio_id: str, project_root: pathlib.Path | None = None) -> str | None

   Resolve `folio_id` to a verified primary-source scan or text-locus URL.

   Resolution order:
   1. Non-gitignored 4-digit `.png` or `.jpg` scan in `resources/` -> GitHub raw URL (or `folio_base_url`).
   2. Track-aware `resources/**/folio_map.json` entry -> GitHub `blob/...#L<line>` or external facsimile URL.


.. py:class:: FolioAuditReport

   Structured audit summary of primary-source folio links in a repository.


   .. py:attribute:: repo
      :type:  str


   .. py:attribute:: tracked_scans
      :type:  int


   .. py:attribute:: ignored_scans
      :type:  int


   .. py:attribute:: folio_map_entries
      :type:  int


   .. py:attribute:: directives_total
      :type:  int


   .. py:attribute:: directives_resolved
      :type:  int


   .. py:attribute:: badges_total
      :type:  int


   .. py:attribute:: badges_resolved
      :type:  int


   .. py:attribute:: unresolved_directives
      :type:  list[str]
      :value: []



   .. py:attribute:: unresolved_badges
      :type:  list[str]
      :value: []



   .. py:attribute:: sample_links
      :type:  list[str]
      :value: []



   .. py:attribute:: env
      :type:  Any
      :value: None



.. py:function:: audit_repo_folio_links(repo_root: pathlib.Path, env: Any = None) -> FolioAuditReport

   Deterministically audit all `.. folio::` directives and `:folio:` badges in `repo_root`.


.. py:function:: optimize_repo_folio_scans(repo_root: pathlib.Path, force_grayscale: bool = False) -> dict[str, Any]

   Losslessly optimize 4-digit `.png` folio scans in `resources/` (converting near-grayscale RGB to `L`).


