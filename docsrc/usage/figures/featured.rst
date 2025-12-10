
Featured Images
===============

The ``picture`` directive is an enhanced version of the standard image directive designed for performance and responsiveness.
It automatically generates optimized WebP variants of your images and context-aware thumbnails for use in collection listings.

Usage
-----

.. code-block:: rst

    .. picture:: /path/to/image.jpg
       :alt: Alternative text
       :caption: Image caption
       :class: custom-class

Features
--------

- **Automatic Optimization**: Converts images to WebP format.
- **Context Handling**:
    - **Main View**: High-quality lossless 800px width.
    - **Thumbnails**: 300px width for list views (referenced in metadata).
- **Responsive HTML**: Renders HTML5 ``<picture>`` elements with appropriate sources.
- **Cache System**: Efficiently caches processed images to speed up builds.

Example
-------

Using an existing wide image from this folder:

.. picture:: wide.png
   :alt: A wide example image
   :caption: An optimized wide image rendered with the picture directive.

Check the build output directory to see the generated ``.webp`` files!
