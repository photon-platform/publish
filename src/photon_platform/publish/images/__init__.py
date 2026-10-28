"""Image processing and directive registration."""

from .directive import (
    PictureDirective,
    picture_node,
    visit_picture_node,
    depart_picture_node,
    prepare_inline_svg,
)
from typing import Any, Dict


def setup(app: Any) -> Dict[str, Any]:
    """Register directives and nodes.

    Args:
        app: The Sphinx application instance.

    Returns:
        Extension metadata.

    """
    app.add_node(
        picture_node,
        html=(visit_picture_node, depart_picture_node),
        epub=(visit_picture_node, depart_picture_node),
        override=True,
    )
    app.add_directive('picture', PictureDirective, override=True)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
