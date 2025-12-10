photon_platform.publish.images
==============================

.. py:module:: photon_platform.publish.images


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


   A base class for Sphinx directives.

   This class provides helper methods for Sphinx directives.

   .. versionadded:: 1.8

   .. note:: The subclasses of this class might not work with docutils.
             This class is strongly coupled with Sphinx.


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


   .. py:method:: run()


.. py:class:: picture_node(rawsource='', *children, **attributes)

   Bases: :py:obj:`docutils.nodes.General`, :py:obj:`docutils.nodes.Element`


   `Element` is the superclass to all specific elements.

   Elements contain attributes and child nodes.
   They can be described as a cross between a list and a dictionary.

   Elements emulate dictionaries for external [#]_ attributes, indexing by
   attribute name (a string). To set the attribute 'att' to 'value', do::

       element['att'] = 'value'

   .. [#] External attributes correspond to the XML element attributes.
      From its `Node` superclass, Element also inherits "internal"
      class attributes that are accessed using the standard syntax, e.g.
      ``element.parent``.

   There are two special attributes: 'ids' and 'names'.  Both are
   lists of unique identifiers: 'ids' conform to the regular expression
   ``[a-z](-?[a-z0-9]+)*`` (see the make_id() function for rationale and
   details). 'names' serve as user-friendly interfaces to IDs; they are
   case- and whitespace-normalized (see the fully_normalize_name() function).

   Elements emulate lists for child nodes (element nodes and/or text
   nodes), indexing by integer.  To get the first child node, use::

       element[0]

   to iterate over the child nodes (without descending), use::

       for child in element:
           ...

   Elements may be constructed using the ``+=`` operator.  To add one new
   child node to element, do::

       element += node

   This is equivalent to ``element.append(node)``.

   To add a list of multiple child nodes at once, use the same ``+=``
   operator::

       element += [node1, node2]

   This is equivalent to ``element.extend([node1, node2])``.


.. py:function:: visit_picture_node(self, node)

   HTML visitor for picture_node.
   Renders a standard <figure> with nested <picture> element.


.. py:function:: depart_picture_node(self, node)

.. py:function:: setup(app)

