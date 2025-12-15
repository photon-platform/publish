photon_platform.publish.images.processor
========================================

.. py:module:: photon_platform.publish.images.processor

.. autoapi-nested-parse::

   Image processing logic.



Classes
-------

.. autoapisummary::

   photon_platform.publish.images.processor.ImageProcessor


Module Contents
---------------

.. py:class:: ImageProcessor(app: Any)

   Handles image processing including resizing, format conversion (WebP), and caching.


   .. py:attribute:: app


   .. py:attribute:: srcdir


   .. py:attribute:: outdir


   .. py:attribute:: cache_dir


   .. py:attribute:: final_images_dir


   .. py:method:: ensure_dirs() -> None

      Ensure that the cache and final image directories exist.



   .. py:method:: get_image_hash(source_path: pathlib.Path, width: int, options: str) -> str

      Generate a unique hash based on file content and processing options.

      :param source_path: Path to the source image.
      :param width: Width of the resized image.
      :param options: String representation of processing options.

      :returns: The SHA256 hash of the image and options.



   .. py:method:: process_image(rel_source_path: str, options: dict = None) -> Dict[str, str]

      Process an image generating variants.

      :returns: Paths to the processed 'main' and 'thumb' images relative to output root.
      :rtype: dict



