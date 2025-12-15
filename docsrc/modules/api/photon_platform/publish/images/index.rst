photon_platform.publish.images
==============================

.. py:module:: photon_platform.publish.images

.. autoapi-nested-parse::

   Image processing and directive registration.



Submodules
----------

.. toctree::
   :maxdepth: 1

   /modules/api/photon_platform/publish/images/directive/index
   /modules/api/photon_platform/publish/images/processor/index


Classes
-------

.. autoapisummary::

   photon_platform.publish.images.PictureDirective
   photon_platform.publish.images.picture_node


Functions
---------

.. autoapisummary::

   photon_platform.publish.images.visit_picture_node
   photon_platform.publish.images.depart_picture_node
   photon_platform.publish.images.setup


Package Contents
----------------

.. py:class:: PictureDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`sphinx.util.docutils.SphinxDirective`


   Directive for inserting responsive pictures.


   .. py:attribute:: required_arguments
      :value: 1


      Number of required directive arguments.


   .. py:attribute:: optional_arguments
      :value: 0


      Number of optional arguments after the required arguments.


   .. py:attribute:: final_argument_whitespace
      :value: True


      May the final argument contain whitespace?


   .. py:attribute:: option_spec

      Mapping of option names to validator functions.


   .. py:method:: run() -> List[docutils.nodes.Node]

      Process the picture directive.

      :returns: A list containing the picture_node.



.. py:class:: picture_node(rawsource='', *children, **attributes)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   Custom node for containing responsive picture elements.


.. py:function:: visit_picture_node(self: Any, node: docutils.nodes.Element) -> None

   HTML visitor for picture_node.

   Renders a standard <figure> with nested <picture> element.

   :param self: The translator instance.
   :param node: The picture_node being visited.


.. py:function:: depart_picture_node(self: Any, node: docutils.nodes.Element) -> None

   Departure visitor for picture_node.

   :param self: The translator instance.
   :param node: The picture_node being visited.


.. py:function:: setup(app: Any) -> Dict[str, Any]

   Register directives and nodes.

   :param app: The Sphinx application instance.

   :returns: Extension metadata.


