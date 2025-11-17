publish.publish
===============

.. py:module:: publish.publish

.. autoapi-nested-parse::

   Core publishing functions.



Functions
---------

.. autoapisummary::

   publish.publish.find_git_root
   publish.publish.build_sass
   publish.publish.build
   publish.publish.clean
   publish.publish.test


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


.. py:function:: test() -> None

   Build and serve the documentation locally.


