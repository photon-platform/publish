# Changelog

## [0.3.6] - 2025-12-15

### Changed
- **Documentation**: enforced Google-style docstrings and added comprehensive type hints to `directives/collection.py`, `images/directive.py`, `images/processor.py` and `images/__init__.py`.
- **Workflow**: updated `code-docs-check` workflow to include separated checks for Type Hints and Docstrings with auto-fix capabilities, plus a final general check.

## [0.3.5] - 2025-12-15

### Changed
- **SCSS Modernization**: migrated all SCSS variables to CSS custom properties (variables) for better dynamic styling capability and reduced Sass dependency.
- **Refactoring**: converted `_admonitions.scss`, `_headings.scss`, and `_lists.scss` from Sass mixins/extends to standard nested CSS.
- **Cleanup**: removed unused Sass mixins, functions, and the `color/` directory. Removed legacy social color variables.
- **Admonitions**: fixed styling issue where admonition text colors were not matching borders by updating selectors to match Sphinx HTML structure.

## [0.3.4] - 2025-12-14

### Changed
- Refined header and breadcrumbs layout.
- Improved mobile navigation with hamburger menu.
- Fixed header navigation alignment on wide screens.

## [0.3.3] - 2025-12-14

### Changed
- Refined excerpt blockquote styling.

## [0.3.2] - 2025-12-13

### Changed
- Fixed section header order in collections.

## [0.3.1] - 2025-12-12

### Changed
- Renamed modules in `clerk` project to be more action-oriented.

## [0.3.0] - 2025-12-09

### Changed
- Initial release of the Publish tool.
