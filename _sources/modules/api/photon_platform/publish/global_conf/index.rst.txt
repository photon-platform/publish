photon_platform.publish.global_conf
===================================

.. py:module:: photon_platform.publish.global_conf

.. autoapi-nested-parse::

   A global, reusable configuration file for Sphinx documentation.



Attributes
----------

.. autoapisummary::

   photon_platform.publish.global_conf.html_context
   photon_platform.publish.global_conf.year
   photon_platform.publish.global_conf.extensions
   photon_platform.publish.global_conf.current_dir
   photon_platform.publish.global_conf.project_root
   photon_platform.publish.global_conf.pyproject_path
   photon_platform.publish.global_conf.include
   photon_platform.publish.global_conf.potential_path
   photon_platform.publish.global_conf.autoapi_dirs
   photon_platform.publish.global_conf.pyproject_data
   photon_platform.publish.global_conf.autoapi_options
   photon_platform.publish.global_conf.autoapi_root
   photon_platform.publish.global_conf.autoapi_python_use_implicit_namespaces
   photon_platform.publish.global_conf.autoapi_keep_files
   photon_platform.publish.global_conf.templates_path
   photon_platform.publish.global_conf.source_suffix
   photon_platform.publish.global_conf.master_doc
   photon_platform.publish.global_conf.language
   photon_platform.publish.global_conf.exclude_patterns
   photon_platform.publish.global_conf.pygments_style
   photon_platform.publish.global_conf.todo_include_todos
   photon_platform.publish.global_conf.html_theme
   photon_platform.publish.global_conf.html_theme_path
   photon_platform.publish.global_conf.html_static_path
   photon_platform.publish.global_conf.htmlhelp_basename
   photon_platform.publish.global_conf.html_theme_options
   photon_platform.publish.global_conf.intersphinx_mapping
   photon_platform.publish.global_conf.html_logo
   photon_platform.publish.global_conf.autodoc_default_options
   photon_platform.publish.global_conf.html_permalinks


Functions
---------

.. autoapisummary::

   photon_platform.publish.global_conf.setup_globals


Module Contents
---------------

.. py:data:: html_context

.. py:function:: setup_globals(org: str, org_name: str, repo: str, repo_name: str) -> None

   Set up global variables for the Sphinx configuration.

   :param org: The GitHub organization or username.
   :param org_name: The display name of the organization.
   :param repo: The GitHub repository name.
   :param repo_name: The display name of the repository.


.. py:data:: year

.. py:data:: extensions
   :value: ['sphinx.ext.intersphinx', 'sphinx.ext.githubpages', 'sphinx.ext.graphviz',...


.. py:data:: current_dir

.. py:data:: project_root
   :value: None


.. py:data:: pyproject_path
   :value: None


.. py:data:: include
   :value: None


.. py:data:: potential_path

.. py:data:: autoapi_dirs

.. py:data:: pyproject_data

.. py:data:: autoapi_options
   :value: ['members', 'undoc-members', 'show-inheritance', 'show-module-summary', 'special-members',...


.. py:data:: autoapi_root
   :value: 'modules/api'


.. py:data:: autoapi_python_use_implicit_namespaces
   :value: True


.. py:data:: autoapi_keep_files
   :value: True


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
   :value: 'foundation'


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


