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
project-specific settings.

Our mission is to create tools for gathering, processing, and publishing content,
with a vision of **"Simple HTML, State of the Art CSS"**.

Key Features
------------

- **Unified Theme**: A single, customizable theme for all PHOTON platform
  documentation, ensuring a consistent and professional look.
- **Custom Components**: Reusable Sphinx components, such as custom directives
  and roles, to simplify content creation.
- **Centralized Configuration**: A global `conf.py` that can be imported into
  local configurations, reducing boilerplate and ensuring consistency.


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

For detailed usage instructions, please refer to the full documentation in ``docsrc``
or the built HTML output.

Dependencies
------------

**publish** depends on the following Python packages:

- Sphinx
- Jinja2
- MyST-Parser
- sphinx-carousel
- sphinxcontrib-jquery
- sphinxcontrib-youtube
- sphinx-revealjs
- sphinxext-opengraph
- libsass
- click
- sphinx-autoapi
- matplotlib
- graphviz

Contributing
------------

Contributions are welcome! Please see our [GitHub issues](https://github.com/photon-platform/publish/issues) for ways to contribute.

License
-------

**publish** is licensed under the MIT License. See the `LICENSE` file for more details.
