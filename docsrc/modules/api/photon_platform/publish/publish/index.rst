photon_platform.publish.publish
===============================

.. py:module:: photon_platform.publish.publish

.. autoapi-nested-parse::

   Core publishing functions.



Functions
---------

.. autoapisummary::

   photon_platform.publish.publish.find_git_root
   photon_platform.publish.publish.build_sass
   photon_platform.publish.publish.build
   photon_platform.publish.publish.clean
   photon_platform.publish.publish.test


Module Contents
---------------

.. py:function:: find_git_root() -> str | None

   Find the git repository root.


.. py:function:: build_sass() -> None

   Compile SASS files for all themes.


.. py:function:: build() -> None

   Build the Sphinx documentation.


.. py:function:: clean() -> None

   Remove the build directory.


.. py:function:: test(port: int = 8000) -> None

   Build and serve the documentation locally.


