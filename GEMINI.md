# Publish

Unified Sphinx publishing engine, **Book Codex (`:layout: book`)** Digital Scriptorium platform, interactive SVG geometry apparatus, and archival folio review workstation for the PHOTON and GEOMETOR ecosystems.

## Overview

`photon_platform.publish` streamlines and extends Sphinx under **"Simple HTML, State of the Art CSS"**, pairing centralized global configuration (`global_conf.py`) with the **Foundation / Book Codex** three-column theme, bidirectional `:g:` / `:eq:` $\leftrightarrow$ `svg.euclid-graphic` highlighting, scholarly apparatus registries (`persons.json`, `citations.json`, `glossary.json`), and the native `publish folio` review workstation.

## Key Modules (`src/photon_platform/publish/`)

- `app.py` & `publish.py`: Click CLI (`publish build`, `publish test`, `publish epub`, `publish folio`).
- `global_conf.py`: Shared Sphinx configuration, dynamic `sphinx-autoapi`, and automatic cross-repository `intersphinx` wiring.
- `book.py`: Multi-track `:layout: book` codex engine (outline tree, parallel language/commentary/code tracks, Prev/Next unit navigation).
- `directives/elements.py` & `roles/geometry.py`: Semantic directives (`.. enunciation::`, `.. assertion::`, `.. subclause::`, `.. step::`, `.. signature::`, `.. folio::`, `.. porism::`, `.. lemma::`, `.. scholium::`, `.. qed::`, `.. collapse::`) and inline roles (`:g:`, `:eq:`, `:just:`, `:person:`, `:cite:`, `:term:`).
- `directives/collection.py`: Taxonomic and chronological `.. collection::` cards with inline SVG thumbnails and enunciation excerpts.
- `themes/foundation/` & `static/js/geometor_interactive.js`: Classical Scriptorium CSS Grid theme and interactive SVG highlight/tick/step-playback controller.
- `folio_review/`: Native Flask workstation (`FolioScanner`, `ReviewManager`) for side-by-side 300 DPI folio inspection and RST vetting.

## Canonical Agent Customizations (`skills/` & `agents/`)

- `skills/scriptorium-codex/SKILL.md`: Authoritative runbook for multimodal scan-image transcription (never relying on embedded PDF OCR), strict content/code separation (zero `py_file` in historical treatises), `publish folio`, 4-step Ink-to-Vector `.euclid-graphic` SVG calibration (`>= 95%` pixel overlap), and interactive `:layout: book` wiring.
- `agents/scriptorium.md`: Digital Scriptorium philologist & geometric draughtsman subagent persona.
