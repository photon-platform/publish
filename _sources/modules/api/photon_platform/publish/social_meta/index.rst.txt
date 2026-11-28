photon_platform.publish.social_meta
===================================

.. py:module:: photon_platform.publish.social_meta

.. autoapi-nested-parse::

   Social media metadata (OpenGraph / Twitter Cards), A-Z <title> formatting, and 1280x640 sharing banners.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.social_meta.BANNER_WIDTH
   photon_platform.publish.social_meta.BANNER_HEIGHT


Functions
---------

.. autoapisummary::

   photon_platform.publish.social_meta.resolve_org_brand
   photon_platform.publish.social_meta.resolve_site_base_url
   photon_platform.publish.social_meta.resolve_site_human_title
   photon_platform.publish.social_meta.extract_page_description
   photon_platform.publish.social_meta.build_social_and_title_context
   photon_platform.publish.social_meta.generate_social_banner
   photon_platform.publish.social_meta.generate_repo_social_banners


Module Contents
---------------

.. py:data:: BANNER_WIDTH
   :value: 1280


.. py:data:: BANNER_HEIGHT
   :value: 640


.. py:function:: resolve_org_brand(env: Any, context: dict[str, Any] | None = None) -> str

   Return canonical uppercase organization brand ('GEOMETOR' or 'PHOTON').


.. py:function:: resolve_site_base_url(env: Any, project_root: pathlib.Path | None = None) -> str

   Resolve canonical HTTPS base URL from CNAME or Sphinx html_baseurl.


.. py:function:: resolve_site_human_title(env: Any, context: dict[str, Any] | None = None) -> str

   Resolve the human-first site name (e.g. 'Fra Luca Pacioli', 'Encyclopedia of Triangle Centers').


.. py:function:: extract_page_description(env: Any, pagename: str, doctree: docutils.nodes.document | None, context: dict[str, Any]) -> str

   Extract a clean 160-200 character social description for `pagename`.


.. py:function:: build_social_and_title_context(app: Any, pagename: str, context: dict[str, Any], doctree: docutils.nodes.document | None) -> dict[str, Any]

   Compute bookmark-friendly `page_browser_title` and OpenGraph/Twitter `<head>` context.


.. py:function:: generate_social_banner(output_path: pathlib.Path, *, org_brand: str, repo_slug: str, title: str, overline: str = '', subtitle: str = '', emblem_path: pathlib.Path | None = None, hero_path: pathlib.Path | None = None, site_domain: str = '', force: bool = False) -> bool

   Render a dedicated 1280x640 social sharing PNG banner from the Foundation HTML+CSS card.

   Uses local headless Chrome (`social_capture.py`) when available so the social
   card matches the live webpage's typography, tokens, and SVG rendering 1-to-1.
   Falls back to Pillow rendering only if no local Chromium/Chrome binary is present.


.. py:function:: generate_repo_social_banners(repo_root: str | pathlib.Path, force: bool = False) -> dict[str, Any]

   Generate `docsrc/_static/social/banner.png` and per-book `<book_slug>.png` for a repository.


