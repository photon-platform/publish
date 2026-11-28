:type: log
:date: 26.332-063100
:author: phi
:tags: cards, collections, bibliography, social-banners

Unified Page Cards, Federated Collections & HTML Social Capture (v0.5.0)
========================================================================

.. summary::

   Every Sphinx page in ``photon-platform/publish`` now resolves to one canonical ``Card``
   driving collections, searchable directories, inline ``.. card::`` embeds, cross-repo
   ``cards.json`` federation, standard scholarly citations, and ``1280×640`` HTML+CSS social
   media banner capture.

Architectural Summary
---------------------

1. **Unified Page Card Model (``cards.py``)**: Replaces duplicated metadata extraction across
   ``social_meta.py``, ``collection.py``, and ``directory.html`` with a single ``Card`` contract
   featuring hybrid curated descriptions (``:description:`` > ``.. summary::`` > ``.. enunciation::``),
   dual visual slots (small project medallion + larger hero diagram), ``:card_ref:`` inheritance,
   and automatic ``docs/cards.json`` export beside ``docs/objects.inv``.
2. **One Semantic Card Template (``components/card.html`` & ``_cards.scss``)**: A single 4-slot
   ``<article class="card">`` morphs purely via CSS into vertical cards, horizontal banners,
   compact list rows, searchable directory items, standalone ``.. card::`` embeds, and
   ``1280×640`` social banners captured locally with ``google-chrome --headless=new``.
3. **Scholarly Bibliography & Apparatus (``bibliography.py`` & ``roles/geometry.py``)**:
   Standard Chicago, MLA, APA, and BibTeX citation tabs, ``docs/bibliography.bib`` export,
   automated parallel-track passage backlinks (``LA · EN``), and cross-project ``:person:`` /
   ``:cite:`` / ``:term:`` resolution via ``cards.json``.

Verification
------------

- **72/72** tests passing (including multi-site federation, ``:card_ref:`` inheritance,
  parallel-track backlinks, and live ``1280×640`` Chrome social capture).
- ``ruff check`` clean across all new modules and tests.
- ``publish build`` clean with valid ``docs/cards.json`` output.
