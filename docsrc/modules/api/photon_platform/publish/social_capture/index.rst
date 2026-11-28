photon_platform.publish.social_capture
======================================

.. py:module:: photon_platform.publish.social_capture

.. autoapi-nested-parse::

   Local HTML+CSS Social Media Card Capture (`1280×640` PNG) via headless Chrome.

   Renders the exact same Foundation theme `<article class="card card--social">` markup
   and compiled CSS as the live website, then snaps a crisp `1280×640` PNG using the
   locally installed Chrome/Chromium binary (`--headless=new --screenshot`).

   This runs ONLY when invoked locally via `publish social-banner` (never during
   `publish build` or GitHub Actions).



Attributes
----------

.. autoapisummary::

   photon_platform.publish.social_capture.SOCIAL_WIDTH
   photon_platform.publish.social_capture.SOCIAL_HEIGHT


Functions
---------

.. autoapisummary::

   photon_platform.publish.social_capture.find_chrome_binary
   photon_platform.publish.social_capture.render_social_card_html
   photon_platform.publish.social_capture.capture_social_card_png
   photon_platform.publish.social_capture.build_social_card_from_params
   photon_platform.publish.social_capture.load_cards_manifest_for_repo


Module Contents
---------------

.. py:data:: SOCIAL_WIDTH
   :value: 1280


.. py:data:: SOCIAL_HEIGHT
   :value: 640


.. py:function:: find_chrome_binary() -> str | None

   Locate a local Chromium/Chrome binary for headless HTML+CSS capture.


.. py:function:: render_social_card_html(card: photon_platform.publish.cards.Card, *, asset_root: pathlib.Path | None = None, theme_css: str | None = None) -> str

   Render standalone `social_card.html` for `card` using the Foundation theme CSS.


.. py:function:: capture_social_card_png(card: photon_platform.publish.cards.Card, output_path: pathlib.Path, *, asset_root: pathlib.Path | None = None, force: bool = False, width: int = SOCIAL_WIDTH, height: int = SOCIAL_HEIGHT, chrome_bin: str | None = None) -> bool

   Render `card` with Foundation HTML+CSS and capture a `1280×640` PNG via headless Chrome.

   Returns `True` if a new PNG was written, `False` if skipped (unchanged cache hit).


.. py:function:: build_social_card_from_params(*, org_brand: str, repo_slug: str, title: str, overline: str = '', subtitle: str = '', emblem_path: pathlib.Path | None = None, hero_path: pathlib.Path | None = None, site_domain: str = '') -> photon_platform.publish.cards.Card

   Build a `Card` payload for `generate_social_banner` / `publish social-banner`.


.. py:function:: load_cards_manifest_for_repo(repo_root: pathlib.Path) -> dict[str, Any] | None

   Load `docs/cards.json` from `repo_root` if already built.


