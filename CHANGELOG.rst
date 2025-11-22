changelog
=========

0.2.21
======

- fix(collection): The ``h1`` title in collection sections is now conditional and will only be rendered if a title is explicitly provided. This prevents the display of a default "Collection" title.

0.2.20
======

- refactor(theme): Replaced the broad `body > *` selector with specific rules for main layout sections, extending a common `%section-default` placeholder for improved maintainability and CSS specificity.

0.2.19
======

- feat: Introduce the new `foundation` theme, a major refactor designed for composability by co-locating SCSS styles with their corresponding HTML templates.
- feat: Generalize the SASS build process to automatically discover and compile styles for all available themes.
- fix: Make the `CollectionDirective` theme-aware, ensuring it uses the correct template path for both the new `foundation` theme and the legacy `photon` theme.

0.2.18
======

- refactor: Standardize article and excerpt layouts, converting to a consistent flexbox model and restructuring HTML for better semantic alignment.

0.2.17
======

- feat: Refine article excerpt styling for a more compact, responsive, and vertically-aligned layout.
- feat: Sort taxonomy pages by the ``:number:`` metadata field to ensure a consistent and predictable order.

0.2.16
======

- fix: Implement numerical sorting for collection items to ensure correct ordering of numbered pages.
- fix: Prevent duplicate ``toctree`` entries when using the ``collection`` directive on multiple pages, resolving warnings and ensuring correct previous/next navigation.

0.2.15
======

- feat: Generate rich excerpts for collections, including the first paragraph or blockquote and the first figure.
- feat: Apply rich excerpt logic to taxonomy pages (tags, categories, types).
- fix: Limit collection search to the current directory and immediate subdirectories to prevent duplicate ``toctree`` entries.
- fix: Correct image paths in excerpts to be root-relative and prevent an erroneous ``.html`` suffix.
- style: Move article metadata to a ``<footer>`` in the excerpt template for better semantic structure.

0.2.14
======

- fix: Add ``jquery`` as a dependency to ``pyproject.toml`` to ensure it is
  installed for the ``sphinx-carousel`` extension.
- docs: Update ``README.rst`` with current project status and details.
- chore: Update package metadata and dependencies.


0.2.13
------
*2025-11-11*

**fixed**

+ Removed redundant SASS compilation performed by `sphinxcontrib-sass`, which was creating an empty `docsrc/theme/photon/static/css` directory. The build process now relies solely on the `publish.build_sass()` function for all SASS compilation.

0.2.12
------
*2025-11-11*

**fixed**

+ Resolved an issue where tags were being split into individual characters in article excerpts.
+ Ensured that both tags and categories are consistently handled as lists, allowing for multiple values.

**changed**

+ Article excerpts now display metadata (date, category, tags) with labels for improved clarity.
+ The styling of article excerpts has been updated to be more condensed and visually consistent with the full article view.

0.2.11
------
*2025-11-11*

**added**

+ Added support for tags and categories, with dedicated pages for each.
+ Integrated tags and categories into article metadata and sidebar navigation.

0.2.10
------
*2025-11-10*

**changed**

+ The article navigation buttons have been styled to be more prominent and consistent with the theme.

0.2.9
-----
*2025-11-10*

**fixed**

+ Added `matplotlib` as an explicit dependency to resolve build warnings and ensure social card generation.
+ Disabled the `sphinx.ext.autosummary` and `sphinx.ext.autodoc` extensions, which were running unnecessarily and cluttering the build output.

0.2.8
-----
*2025-11-10*

**fixed**

+ Images within the content area are now responsive and will not exceed the width of their container.
+ Added a bottom margin to paragraphs and a top margin to headings to improve readability and spacing.

0.2.7
-----
*2025-11-09*

**changed**

+ The style of the headerlink has been changed to match the size of the heading it's in. It is now faded until hovered over, at which point it shows the link color. It also has a little left padding to separate it from the heading.

0.2.6
-----
*2025-11-09*

**added**

+ Integrated Sphinx AutoAPI for automated API documentation generation.
+ Added comprehensive docstrings and type hints to all modules for improved code clarity and maintainability.

**changed**

+ Refactored the documentation structure to place the API reference under the "Modules" section.
+ Cleaned up `global_conf.py` by removing unused configuration variables and adding a module docstring.

0.2.5
-----
*2025-11-09*

**added**

+ Admonition styling for todo, note, warning, danger, attention, caution, error, hint, important, and tip.

0.2.4
-----
*2025-11-09*

**added**

+ Added the organization and repository name to the header for better branding and context.

0.2.3
-----
*2025-11-09*

**added**

+ Added a footer navigation section, configurable via page metadata.

0.2.2
-----
*2025-11-08*

**changed**

+ Refined theme styles and templates, removing unused files and streamlining the overall structure.
+ Implemented new breadcrumbs in article headers for improved navigation.
+ Pared down font weights to reduce load times and improve performance.
+ Replaced the aggressive CSS reset with a more modern, targeted approach.

0.2.1
-----
*2025-11-08*

**changed**

+ The SCSS compilation now generates expanded, readable CSS instead of compressed CSS. This improves debuggability of the styles.

0.2.0
-----
*2025-11-08*

**changed**

+ Refactored the Sphinx theme to align with the design and functionality of the original Grav theme.
+ Replaced the `ablog` extension with a custom `collection` directive to provide more flexible, time-based content listings for any page type.
+ Introduced a hierarchical content model, allowing pages to manage and display subordinate items.
+ Updated the theme templates to use a more semantic and modular HTML structure.
+ Integrated SASS for more maintainable and flexible styling.

0.1.2
-----
*2025-11-07*

**changed**

+ Refactored the `publish` tool to use a `click`-based command-line interface with `build` and `test` commands.
+ Standardized the theme name to `photon` and the main SASS file to `styles.scss`.
+ Consolidated all theme and Sphinx configurations into `global_conf.py` to simplify project-level `conf.py` files.
+ Made the build process context-aware, allowing it to be run from any directory within a git repository.
+ Integrated SASS compilation into the build process.
+ Removed the old, unused `theme` directory.

0.1.1
-----
*2025-11-07*

**fixed**

+ Resolved build issues with the Sphinx documentation by removing outdated and conflicting files from the `docsrc/modules` directory. This ensures a clean and successful build process.

0.1.0
-----
*2025-11-07*

**removed**

+ Removed the `sphinxilator_theme` and all its associated SCSS files, streamlining the project to focus on a single, unified theme provided by the `publish` tool. This change simplifies the theming architecture and removes legacy code.

0.0.4
-----
*2025-10-26*

**changed**

+ ...

0.0.3
-----
*2025-10-26*

**added**

+ Integrated `sphinx_rtd_theme` navigation, including toctree and sticky navigation.
+ Integrated `sphinx_rtd_theme` search functionality with a custom search page.
+ Added breadcrumbs and previous/next buttons for improved navigation.

0.0.2
-----
*2025-10-26*

**added**

+ Created a new, unified `publish_theme` to consolidate documentation styling.
+ Ported the basic HTML structure and templates from `sphinx_rtd_theme`.
+ Integrated the SASS styles and structure from `grav-theme-photon`.
+ Implemented a new semantic HTML layout (`<header>`, `<main>`, `<asides>`).
+ Established a simplified, dark-theme-first color palette.
+ Added a SASS build system to compile theme assets.