publish
=======

.. image:: https://img.shields.io/pypi/v/photon-platform-publish.svg
   :target: https://pypi.python.org/pypi/photon-platform-publish

publish is a consolidated repository designed to streamline and enhance
the Sphinx documentation framework.

Overview
--------

This project integrates custom components, themes, and configurations into a
unified system, making it easier to manage Sphinx projects. It supports
project-specific settings, conversion of Grav themes into Jinja templates, and
extends Ablog to support diverse content types.

Key Features
------------

- **Unified Theme**: A single, customizable theme for all PHOTON platform
  documentation, ensuring a consistent and professional look.
- **Custom Components**: Reusable Sphinx components, such as custom directives
  and roles, to simplify content creation.
- **Centralized Configuration**: A global `conf.py` that can be imported into
  local configurations, reducing boilerplate and ensuring consistency.
- **Grav Theme Conversion**: Tools to convert Grav themes into Jinja templates
  compatible with Sphinx.
- **Extended Ablog Support**: Enhanced Ablog functionality to support different
  content types, such as events, tasks, and updates.
- **Interactive Collection Layouts**: Users can dynamically switch between Cards, Banners, and List views for content collections, with persistent preferences.
- **Streamlined Project Integration**: Provides a structured approach for integrating `publish` into existing and new Sphinx projects, ensuring consistency and efficiency in documentation deployment.
- **Enhanced Article Navigation**: Styled article navigation buttons for improved prominence and theme consistency.

Installation
------------

You can install **publish** using pip:

.. code-block:: bash

   pip install photon-platform-publish

Usage
-----

After installation, you can use the ``publish`` command to manage your documentation projects:

.. code-block:: bash

   publish build  # build the documentation for a project
   publish test  # build and serve the documentation locally

Dependencies
------------

**publish** depends on the following Python packages:

- Sphinx
- Ablog
- click
- libsass

Contributing
------------

Contributions are welcome! Please see our [GitHub issues](https://github.com/photon-platform/publish/issues) for ways to contribute.

License
-------

**publish** is licensed under the MIT License. See the `LICENSE` file for more details.
