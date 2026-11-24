---
name: scriptorium-codex
description: >-
  Build, transcribe, calibrate, and compile scholarly multi-track Book Codices
  (:layout: book) with photon-platform/publish, including multimodal folio scan
  vision, native publish folio review, 4-step Ink-to-Vector .euclid-graphic SVG
  calibration, and interactive :g:/:eq:/:just:/apparatus RST wiring.
---

# Digital Scriptorium & Book Codex Workflow (`scriptorium-codex`)

Authoritative runbook for ingesting archival treatises, calibrating interactive geometric diagrams, and compiling multi-track **Book Codices (`:layout: book`)** powered by `photon-platform/publish` (used across `euclid`, `pacioli`, `hoenen`, `altshiller-court`, `aristotle`, `aquinas`, `proclus`, `hilbert`, `bertrand-russell`, `walter-russell`, `elements`, `pappus`, `etc`, and `fundamentals`).

---

## 1. Iron Law of PDF & Folio Ingestion (Multimodal Scan Vision Over OCR)

> **CRITICAL MANDATE — NEVER RELY ON EMBEDDED OCR OR `pdftotext`:**
> Even when an archival PDF embeds a hidden OCR text layer, **NEVER** rely on `pdftotext`, `pypdf`, or OCR text extraction to transcribe prose, infer semantic structure, or read mathematical notation.

1. **Render High-Resolution Archival Folio Scans First**:
   - Extract pages at **300 DPI** via `pdftoppm -png -r 300 <source.pdf>` into zero-padded `<NNNN>.png` folio scans routed by `structure_map.json`.
2. **Direct Multimodal Visual Reading (`view_file` on `<NNNN>.png`)**:
   - Agents **MUST inspect the rendered `<NNNN>.png` page scan images directly using `view_file` page-by-page** to:
     - Ascertain true **semantic & rhetorical structure**: book/chapter headings, proposition/article numbers, *enunciation* (*protasis*) vs. *analysis* / *construction* / *proof* / *porism* / *scholium* / *discussion*, marginal Bekker/Friedlein/Stephanus numbers, drop-cap initials, and footnotes.
     - Verify **every formula, symbol, and glyph** with 100% visual fidelity: fractions, radicals, geometric operators ($\triangle ABC$, $\angle AOB$, $\parallel$, $\perp$, $\sim$, $\cong$), primes ($A'$, $B''$, $C_1'$), subscripts ($M_1$, $X_n$), ratios, and polytonic Greek or Renaissance Latin/Italian orthography and ligatures.
     - Measure exact diagram bounding boxes (`bbox: [x, y, w, h]`) and printed vertex/label positions directly from the scan pixels.

---

## 2. Strict Separation of Content & Code

- **Zero Embedded Python Construction Scripts in Historical Editions**:
  - Historical and philosophical codex repositories (`euclid`, `pacioli`, `hoenen`, `altshiller-court`, `aristotle`, `aquinas`, `proclus`, `hilbert`, `bertrand-russell`) preserve the faithful source treatise, calibrated archival/vector figures, folio milestones, and scholarly commentary tracks.
  - **NEVER** embed `py_file` Python construction scripts inside treatise `resources/` folders or `<NNNN>.json` graphic manifests.
  - Executable SymPy/`geometor.model` constructions belong strictly in constructive geometry packages (`geometor/elements`, `geometor/pappus`, `geometor/etc`, `geometor/fundamentals`, `geometor/wildberger`), linked across repositories via `intersphinx` and `:just:` / `:ref:` anchors.

### Universal Completeness & Drawing Capture Mandate (All Books, All Authors)
- **Complete Canonical Structure on Separate Pages**: Never stop at cherry-picked chapters or propositions. Capture every Book, Chapter, and Proposition of every treatise on its own standalone page with **concise English-first titles** (`Chapter I: ...`, `Proposition XLV: ...`), clean native-language subtitles/tracks, zero repeated translation boilerplate, and all archival witness provenance inside `*-notes.rst`.
- **Iron Law of Track Purity (Authentic Voice & Complete Transcription — Zero Meta-Commentary on Primary Tracks)**:
  - **Original-Language Track (`-la`, `-el`, `-de`, `-fr`, `-it`)**: MUST contain a faithful, complete transcription read directly from the 300-DPI primary witness scans—**NEVER** synthetic 2-sentence paraphrases or abbreviated stubs.
  - **English Track (`-en` / primary `index.rst`)**: MUST contain a faithful, direct translation (or verbatim public-domain English witness) speaking **in the author's own voice** (first-person prose, direct definitions, enunciations, constructions, and demonstrations). **STRICTLY FORBIDDEN** on English primary tracks: third-person commentary *about* the book (*"In Chapter I, Kepler states..."*, *"Here Mascheroni proves..."*, *"In this section, the author explains..."*).
  - **Summary & Notes Tracks (`-summary`, `-notes`, `commentary.rst`)**: ALL third-person synopses, structural overviews, modern symbolic notation bridges, historical context, and cross-corpus apparatus belong strictly in `summary` and `notes`—never mixed into primary text tracks.
- **Paired Archival Bitmaps (`<NNNN>.g<k>.png`) + Calibrated Interactive Vectorizations (`<NNNN>.g<k>.svg`)**: Every original woodcut, copperplate, folding plate, and geometric figure MUST be extracted as a tightly cropped, contrast-normalized archival bitmap (`<NNNN>.g<k>.png`) embedded via `.. picture::` AND—for every geometric/mathematical diagram—paired with a calibrated theme-adaptive `.euclid-graphic` interactive SVG (`<NNNN>.g<k>.svg`) wired with `:g:` / `:eq:` highlighting (plus interactive 3D models for spatial polyhedra treatises).
---

## 3. Canonical Directory & Apparatus Architecture

```text
<repo>/
├── resources/<edition>/
│   ├── pdfs/<source>.pdf               # Archival source PDF(s)
│   ├── structure_map.json              # Deterministic Folio <-> Printed Page map, Roman frontmatter, blank versos, unit routing
│   ├── persons.json                    # Biographical registry powering :person: hover cards & persons.rst
│   ├── citations.json                  # Bibliographic registry powering :cite: hover cards & bibliography.rst
│   ├── glossary.json                   # Defined technical vocabulary powering :term: hover cards & glossary.rst
│   ├── folio_reviews.json              # Vetting status managed natively by publish folio (ReviewManager)
│   └── <unit_dir>/                     # e.g., volume_I/book_i/propositions/ or 01_geometric_constructions/
│       ├── <NNNN>.png                  # 300 DPI page scan
│       ├── <NNNN>.rst                  # Visually verified folio transcription (:folio:, :page:, :section:, :title:)
│       ├── <NNNN>.notes.rst            # Optional companion commentary / translation notes
│       ├── <NNNN>.json                 # Calibrated figure manifest (bbox, white_point, svg_file, geometry — NO py_file)
│       ├── <NNNN>.g1.png               # Cropped & normalized archival figure plate (+ .inverted.png if raster)
│       └── <NNNN>.g1.svg               # Calibrated Ink-to-Vector interactive .euclid-graphic SVG
└── docsrc/<edition>/                   # Compiled de-paginated multi-track Book Codex (:layout: book)
    ├── index.rst
    ├── <unit>/<item>/                  # Parallel companion tracks auto-linked by photon_platform.publish.book:
    │   ├── index.rst (or <stem>_en.rst / <stem>_la.rst / <stem>_grc.rst)
    │   └── commentary.rst (or <stem>_notes.rst)
    ├── bibliography.rst
    ├── persons.rst
    └── glossary.rst
```

### Native `publish folio` Workstation (Never Duplicate Flask Apps!)
- Always inspect and vet `resources/<edition>/` with the shared `photon-platform/publish` workstation (`FolioScanner` + `ReviewManager`):
  ```bash
  publish folio --root resources/<edition> --port 5050
  ```
- **Never** create custom per-repository Flask apps for folio review.

---

## 4. 4-Step Ink-to-Vector `.euclid-graphic` SVG Calibration

When vectorizing historical diagrams into interactive `<NNNN>.g<k>.svg` plates:

1. **Step 1 — Scan Crop & Ink Centroid Extraction**:
   - Crop `[x, y, w, h]` from `<NNNN>.png` and threshold paper background (`white_point`) to isolate historical ink pixels.
   - Locate exact pixel coordinates of printed line intersections, circle centers/radii, and letter labels directly in scan coordinates.
2. **Step 2 — `<svg class="euclid-graphic">` Contract & `<defs>` Tick Infrastructure**:
   - Root attributes: `class="euclid-graphic"`, `data-graphic-id="<NNNN>.g<k>"`, `data-folio="<NNNN>"`, `data-graphic="g<k>"`, tight `viewBox` + matching `width`/`height`.
   - Embed theme-adaptive CSS variables (`--geom-fg`, `--geom-bg`, `--geom-accent`, `--geom-assert` with `@media (prefers-color-scheme: dark)`).
   - Include `<defs>` with midpoint equality markers `#geom-tick-1`, `#geom-tick-2`, and `#geom-tick-3` (`viewBox="-6 -6 12 12"`, `orient="auto"`, `markerUnits="userSpaceOnUse"`).
   - Organize elements into ordered groups: `<g id="elements">`, `<g id="graphics">`, `<g id="highlights" style="pointer-events: none;">`, `<g id="points">`, `<g id="labels">`.
3. **Step 3 — 3-Vertex Midpoint `<path>` & Canonical `data-ref` Attributes**:
   - **3-Vertex Straight Paths**: Write every segment and `#highlights` `.geom-overlay` segment as `d="M x1 y1 L mx my L x2 y2"` where `(mx, my) = ((x1+x2)/2, (y1+y2)/2)` — never 2-point `<line>` — so CSS `marker-mid: url(#geom-tick-1..3)` places equality ticks at the exact midpoint.
   - **3-Vertex Angle Arcs**: Pair every angle `.wedge` with a `.geom-ang-arc.geom-overlay` open 2-arc `<path d="M x1 y1 A r r 0 0 sf mx my A r r 0 0 sf x2 y2">` split at the exact angular midpoint.
   - **Canonical `data-ref` Identifiers**: Use clean alphanumeric point IDs without underscores (`A`, `B`, `M1`, `A0`) and canonical GEOMETOR tokens:
     - Point: `data-ref="A"`
     - Segment: `data-ref="/ A B /"`
     - Line: `data-ref="[ A B ]"`
     - Circle: `data-ref="( A B )"` (center `A`, radius point `B`) with `data-aliases="( B C D )"` for 3-letter classical circle names
     - Angle: `data-ref="< B A C )"` (vertex `A` in middle)
     - Polygon: `data-ref="< A B C >"`
4. **Step 4 — `>= 95%` Pixel-Overlap & Visual Verification**:
   - Rasterize `<NNNN>.g<k>.svg` at 1:1 scale against the thresholded `<NNNN>.g<k>.png` ink mask (masking out printed letter bounding boxes) and verify **`>= 95%` stroke-to-ink pixel overlap**.
   - Visually inspect the rendered SVG alongside `<NNNN>.g<k>.png` via `view_file` to confirm zero flipped arcs, zero label-stroke collisions, and clean dark-mode contrast.

---

## 5. Interactive Text & Apparatus Wiring in RST

Wire de-paginated and folio `.rst` files using `photon-platform/publish` semantic directives and inline roles:

```rst
:layout: book

PROPOSITION 1.
==============

.. folio:: 0255
   :page: 241

.. enunciation::

   On a given finite straight line to construct an equilateral triangle.

.. picture:: 0255.g1.svg
   :alt: Proposition 1 figure

With centre :g:`A <0255.g1:A>` and distance :g:`AB <0255.g1:/ A B />` let the circle
:g:`BCD <0255.g1:( B C D )>` be described; :just:`[Post. 3] <I.post.3>`

.. assertion:: [Def. 15] <I.def.15>

   :g:`AC <0255.g1:/ A C />` is :eq:`equal <0255.g1:/ A C / = 0255.g1:/ A B />` to :g:`AB <0255.g1:/ A B />`.
```

- **Geometric Roles**:
  - `:g:` — Bidirectional text $\leftrightarrow$ SVG hover/click highlight (use display mapping ``:g:`A' <0042.g1:A1>` `` or ``:g:`M_{01} <g1:M01>` `` for primes and subscripts).
  - `:eq:` — Highlights equal segments or angles in `--geom-assert` green and activates `#geom-tick-1..3` midpoint tick markers across `=` chains.
  - `:just:` — Renders right-aligned/inline justification pills resolved locally or via `intersphinx` (`euclid`, `elements`).
- **Structural Directives**: `.. enunciation::`, `.. assertion:: [just]`, `.. subclause:: [just]`, `.. step:: <kind> [just]`, `.. signature:: <kind>`, `.. porism::`, `.. lemma::`, `.. scholium::`, `.. qed::`, `.. folio:: <id>`, `.. collapse:: <title>`.
- **Scholarly Apparatus Roles**: `:person:` (backed by `persons.json`), `:cite:` (backed by `citations.json`), `:term:` (backed by `glossary.json`).
- **Canonical Book Publication Year Standard (`:year:`, `:year_label:`, `:edition_year:`)**:
  - **`:year:`** MUST ALWAYS be a **pure signed integer** representing the **author's original composition or first-publication year** (NOT a modern translator/critical-edition year—e.g. Euclid's *Elements* and *Data* use `-300`, not Heath's `1926` or Menge's `1896`; Apollonius's *Conics* uses `-200`, not Heath's `1896`). Negative integers represent BCE (`-300` = 300 BCE); positive integers represent CE (`60`, `1509`, `1952`).
  - **`:year_label:`** *(optional)*: Clean, Docutils-safe human display string when distinct from the bare integer (e.g. `ca. 300 BCE`, `ca. 60 CE`, `ca. 1257–1259`, `1950–1952`, `1994–present`). **NEVER** begin `:year:` or `:year_label:` with `c. ` (Docutils parses single-letter `c. ` as a lower-alpha enumerated list `<ol start="3">`)—always use `ca. `, `BCE` (never `BC`), and `CE` (never `AD`).
  - **`:edition_year:`** *(optional)*: Signed/positive integer year of the modern critical edition, translation, or facsimile witness (e.g. `1926` for Heath's *Elements*, `1896` for Menge's *Data* and Heath's *Conics*, `1897` for Heath's *Archimedes*). Never mix modern edition years into `:year:` with `/`.

---

## 6. Build & Verification Gate

Compile and verify the Sphinx HTML (and optional EPUB 3) codex inside the sandbox:

```bash
publish build
```

Confirm zero Sphinx errors, intact companion-track tabs (`.book-reading-pane`), live `geometor_interactive.js` highlighting, and populated `persons.rst`, `bibliography.rst`, and `glossary.rst` indices.
