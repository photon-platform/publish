publish.global_conf
===================

.. py:module:: publish.global_conf

.. autoapi-nested-parse::

   A global, reusable configuration file for Sphinx documentation.



Attributes
----------

.. autoapisummary::

   publish.global_conf.html_context
   publish.global_conf.year
   publish.global_conf.extensions
   publish.global_conf.autoapi_dirs
   publish.global_conf.autoapi_options
   publish.global_conf.autoapi_root
   publish.global_conf.templates_path
   publish.global_conf.source_suffix
   publish.global_conf.master_doc
   publish.global_conf.language
   publish.global_conf.exclude_patterns
   publish.global_conf.pygments_style
   publish.global_conf.todo_include_todos
   publish.global_conf.html_theme
   publish.global_conf.html_theme_path
   publish.global_conf.html_static_path
   publish.global_conf.htmlhelp_basename
   publish.global_conf.html_theme_options
   publish.global_conf.intersphinx_mapping
   publish.global_conf.html_logo
   publish.global_conf.autodoc_default_options
   publish.global_conf.html_permalinks


Functions
---------

.. autoapisummary::

   publish.global_conf.setup_globals


Module Contents
---------------

.. py:data:: html_context

.. py:function:: setup_globals(org: str, org_name: str, repo: str, repo_name: str) -> None

   Set up global variables for the Sphinx configuration.

   Args:
       org: The GitHub organization or username.
       org_name: The display name of the organization.
       repo: The GitHub repository name.
       repo_name: The display name of the repository.


.. py:data:: year

.. py:data:: extensions
   :value: ['sphinx.ext.extlinks', 'sphinx.ext.intersphinx', 'sphinx.ext.githubpages',...


.. py:data:: autoapi_dirs
   :value: ['../src']


.. py:data:: autoapi_options
   :value: ['members', 'undoc-members', 'show-inheritance', 'show-module-summary', 'special-members']


.. py:data:: autoapi_root
   :value: 'modules/api'


.. py:data:: templates_path
   :value: ['_templates']


.. py:data:: source_suffix

.. py:data:: master_doc
   :value: 'index'


.. py:data:: language
   :value: 'en'


.. py:data:: exclude_patterns
   :value: ['.archive', '.docs', 'tests', '*.egg-info']


.. py:data:: pygments_style
   :value: 'gruvbox-dark'


.. py:data:: todo_include_todos
   :value: True


.. py:data:: html_theme
   :value: 'photon'


.. py:data:: html_theme_path

.. py:data:: html_static_path
   :value: ['_static']


.. py:data:: htmlhelp_basename
   :value: 'help_doc'


.. py:data:: html_theme_options

.. py:data:: intersphinx_mapping

.. py:data:: html_logo
   :value: '_static/logo.png'


.. py:data:: autodoc_default_options

.. py:data:: html_permalinks
   :value: True


