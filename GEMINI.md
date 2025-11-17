# Publish

A tool to streamline and enhance the Sphinx documentation framework.

## Overview

Publish integrates custom components, themes, and configurations into a unified system for easier management of Sphinx projects. It supports dynamic project-specific settings and the conversion of Grav themes, and provides custom directives for flexible content listings.

## Index

-   `publish.py`: Core logic for the Publish tool.
-   `global_conf.py`: A global `conf.py` that can be imported into local configurations.
-   `directives/collection.py`: A custom directive for creating flexible, time-based content listings.
-   `themes/photon/`: Contains the theme files for the Sphinx documentation.
-   `themes/foundation/`: A new, composable theme that co-locates templates and styles.
-   `app.py`: The main `click`-based command-line interface.
