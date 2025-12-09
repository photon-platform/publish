# Publish

A tool to streamline and enhance the Sphinx documentation framework.

## Overview

Publish integrates custom components, themes, and configurations into a unified system for easier management of Sphinx projects. It supports dynamic project-specific settings and provides custom directives for flexible content listings.

## Index

-   `publish.py`: Core logic for the Publish tool.
-   `global_conf.py`: A global `conf.py` that can be imported into local configurations.
-   `directives/collection.py`: A custom directive for creating flexible, time-based content listings.
-   `themes/foundation/`: The specialized theme for the PHOTON platform, co-locating templates and styles.
-   `docsrc/standards/`: Documentation for project standards and guidelines.
-   `app.py`: The main `click`-based command-line interface.
