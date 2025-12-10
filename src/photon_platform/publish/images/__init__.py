from .directive import PictureDirective, picture_node, visit_picture_node, depart_picture_node

def setup(app):
    app.add_node(picture_node, html=(visit_picture_node, depart_picture_node))
    app.add_directive('picture', PictureDirective)
