photon_platform.publish.images.directive
========================================

.. py:module:: photon_platform.publish.images.directive

.. autoapi-nested-parse::

   Directives for image processing.



Classes
-------

.. autoapisummary::

   photon_platform.publish.images.directive.picture_node
   photon_platform.publish.images.directive.PictureDirective


Functions
---------

.. autoapisummary::

   photon_platform.publish.images.directive.prepare_inline_svg
   photon_platform.publish.images.directive.visit_picture_node
   photon_platform.publish.images.directive.depart_picture_node
   photon_platform.publish.images.directive.register_standalone_picture


Module Contents
---------------

.. py:function:: prepare_inline_svg(svg_path: pathlib.Path | str, as_thumbnail: bool = False) -> str | None

   Read an SVG file and prepare it for inline HTML rendering controlled by global CSS.

   Strips XML/DOCTYPE headers, embedded <style> blocks, and hardcoded background <rect>
   elements so theme CSS variables (--geom-fg, --geom-bg, etc.) govern light/dark mode.
   When as_thumbnail is True, also strips hidden highlight overlays and element IDs to
   avoid duplicate DOM IDs on collection index pages.


.. py:class:: picture_node(rawsource: str = '', *children, **attributes: Any)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   Custom node for containing responsive picture elements.


.. py:function:: visit_picture_node(self: Any, node: docutils.nodes.Element) -> None

   HTML visitor for picture_node.

   Renders a standard <figure> with nested <picture> element for raster images,
   or a clean <figure class="photon-picture photon-svg"><img .../></figure> for SVGs
   and standalone Docutils rendering.

   :param self: The translator instance.
   :param node: The picture_node being visited.


.. py:function:: depart_picture_node(self: Any, node: docutils.nodes.Element) -> None

   Departure visitor for picture_node.

   :param self: The translator instance.
   :param node: The picture_node being visited.


.. py:class:: PictureDirective(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)

   Bases: :py:obj:`docutils.parsers.rst.Directive`


   Directive for inserting responsive pictures and interactive SVG figures.


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


   .. py:property:: env
      :type: Any


      Return the Sphinx BuildEnvironment if running inside Sphinx, else None.


   .. py:method:: run() -> List[docutils.nodes.Node]

      Process the picture directive in either Sphinx or standalone Docutils mode.

      :returns: A list containing the picture_node.



.. py:function:: register_standalone_picture() -> None

   Register picture directive and HTML visitors with standalone Docutils.


