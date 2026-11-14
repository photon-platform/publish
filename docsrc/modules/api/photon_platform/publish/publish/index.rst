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

.. py:function:: find_git_root(start_dir: str | None = None) -> str | None

   Find the git repository root from start_dir (or current working directory).


.. py:function:: build_sass(force: bool = False, quiet: bool = False) -> None

   Compile SASS files for themes only when .scss sources are newer than compiled .css.


.. py:function:: build(repo: str | None = None, clean: bool = False, jobs: int | None = None, quiet: bool = False) -> dict[str, Any]

   Build the Sphinx HTML documentation (incremental by default; full wipe when clean=True).


.. py:function:: clean(repo: str | None = None, quiet: bool = False) -> dict[str, Any]

   Remove the docs/ build directory and generated autoapi files.


.. py:function:: test(port: int = 8000) -> None

   Build and serve the documentation locally.


.. py:function:: discover_books(docsrc_dir: str) -> list[dict[str, str]]

   Discover book subtrees (marked with :layout: book or :book_title:) inside docsrc.


.. py:function:: build_epub(book: str | None = None, output: str | None = None, repo: str | None = None, quiet: bool = False) -> list[str]

   Build an EPUB 3 edition for a book subtree in docsrc.


