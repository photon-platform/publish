photon_platform.publish.images.processor
========================================

.. py:module:: photon_platform.publish.images.processor


Classes
-------

.. autoapisummary::

   photon_platform.publish.images.processor.ImageProcessor


Module Contents
---------------

.. py:class:: ImageProcessor(app)

   Handles image processing including resizing, format conversion (WebP),
   and caching.


   .. py:attribute:: app


   .. py:attribute:: srcdir


   .. py:attribute:: outdir


   .. py:attribute:: cache_dir


   .. py:attribute:: final_images_dir


   .. py:method:: ensure_dirs()


   .. py:method:: get_image_hash(source_path, width, options)

      Generate a unique hash based on file content and processing options.



   .. py:method:: process_image(rel_source_path, options=None)

      Main entry point to process an image.

      :returns: Paths to the processed 'main' and 'thumb' images relative to output root.
      :rtype: dict



