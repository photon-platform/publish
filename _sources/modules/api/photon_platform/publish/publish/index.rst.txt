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
   photon_platform.publish.publish.discover_books
   photon_platform.publish.publish.build_epub


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


.. py:function:: discover_books(docsrc_dir: str) -> list[dict[str, str]]

   Discover book subtrees (marked with :layout: book or :book_title:) inside docsrc.


.. py:function:: build_epub(book: str | None = None, output: str | None = None) -> list[str]

   Build an EPUB 3 edition for a book subtree in docsrc.


