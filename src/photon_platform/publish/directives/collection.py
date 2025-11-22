import os
from functools import partial
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri
from docutils.parsers.rst import directives
from docutils import nodes
from sphinx.addnodes import toctree


def to_numeric(value):
    """
    Converts a value to a numeric type if possible, trying int then float.
    """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value


class CollectionDirective(SphinxDirective):
    has_content = False
    option_spec = {
        'type': directives.unchanged,
        'sort': directives.unchanged,
        'reverse': directives.flag,
        'template': directives.unchanged,
        'limit': directives.positive_int,
        'title': directives.unchanged,
        'class': directives.unchanged,
    }

    def run(self) -> list:
        """
        Process the collection directive, discover and sort documents,
        and render them using a Jinja2 template.
        """
        env = self.env
        
        # Determine the template path based on the current theme
        if env.app.config.html_theme == 'foundation':
            default_template = 'components/collection/collection.html'
        else:
            default_template = '_macros/collection.html'

        collection_type = self.options.get('type')
        sort_key = self.options.get('sort')
        reverse = 'reverse' in self.options
        template_name = self.options.get('template', default_template)
        limit = self.options.get('limit')
        title = self.options.get('title')
        collection_class = self.options.get('class', '')

        # Discover files automatically, but not recursively deep
        current_dir = os.path.dirname(env.docname)
        walk_path = os.path.join(env.srcdir, current_dir)
        docnames = []

        # Process current directory
        for filename in os.listdir(walk_path):
            path = os.path.join(walk_path, filename)
            if os.path.isfile(path) and filename.endswith('.rst'):
                docname = os.path.splitext(os.path.relpath(path, env.srcdir))[0]
                if docname != env.docname:
                    docnames.append(docname)

        # Process immediate subdirectories
        for item in os.listdir(walk_path):
            path = os.path.join(walk_path, item)
            if os.path.isdir(path):
                for sub_filename in os.listdir(path):
                    sub_path = os.path.join(path, sub_filename)
                    if os.path.isfile(sub_path) and sub_filename.endswith('.rst'):
                        docname = os.path.splitext(os.path.relpath(sub_path, env.srcdir))[0]
                        if docname != env.docname:
                            docnames.append(docname)

        collection_items = []
        for docname in docnames:
            meta = env.metadata.get(docname, {})
            if not collection_type or meta.get('type') == collection_type:
                title_node = env.titles.get(docname)
                if title_node:
                    item = {
                        'title': title_node.astext(),
                        'docname': docname,
                        'excerpt_text': '',
                        'excerpt_figure_filename': None,
                    }
                    item.update(meta)

                    doctree = env.get_doctree(docname)
                    
                    # Find first paragraph or blockquote
                    first_text = None
                    for node in doctree.traverse(lambda n: isinstance(n, (nodes.paragraph, nodes.block_quote))):
                        first_text = node
                        break
                    
                    if first_text:
                        item['excerpt_text'] = self.env.app.builder.render_partial(first_text)['html_body']

                    # Find first figure
                    for node in doctree.traverse(nodes.figure):
                        image_node = next(iter(node.traverse(nodes.image)), None)
                        if image_node:
                            item['excerpt_figure_filename'] = os.path.basename(image_node['uri'])
                            item['excerpt_figure_alt'] = image_node.get('alt', '')
                            item['excerpt_figure_width'] = node.get('width')
                            break

                    if 'tags' in item and isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',')]
                    if 'categories' in item and isinstance(item['categories'], str):
                        item['categories'] = [cat.strip() for cat in item['categories'].split(',')]
                    collection_items.append(item)

        if sort_key:
            collection_items.sort(key=lambda x: to_numeric(x.get(sort_key, 0)), reverse=reverse)

        if limit:
            collection_items = collection_items[:limit]

        def pathto(otheruri, resource=False, baseuri=None):
            if resource:
                return relative_uri(self.env.app.builder.get_target_uri(self.env.docname), otheruri)
            return self.env.app.builder.get_relative_uri(self.env.docname, otheruri)
        context = {
            'collection': {
                'title': title,
                'articles': collection_items,
                'class': collection_class,
            },
            'pathto': pathto,
        }

        jinja_env = self.env.app.builder.templates.environment
        template = jinja_env.get_template(template_name)
        html = template.render(context)

        # Create a toctree with the sorted and limited items
        # to ensure correct prev/next navigation.
        # Also, ensure we don't add duplicate entries to the toctree
        # across multiple collection directives.
        if not hasattr(self.env, 'photon_publish_collection_docnames'):
            self.env.photon_publish_collection_docnames = set()

        toc_docnames = [item['docname'] for item in collection_items]

        unique_toc_docnames = []
        for docname in toc_docnames:
            if docname not in self.env.photon_publish_collection_docnames:
                unique_toc_docnames.append(docname)
                self.env.photon_publish_collection_docnames.add(docname)

        if not unique_toc_docnames:
            return [nodes.raw('', html, format='html')]

        toc = toctree()
        toc['glob'] = False
        toc['hidden'] = True
        toc['includefiles'] = unique_toc_docnames
        toc['entries'] = [(None, docname) for docname in unique_toc_docnames]

        return [nodes.raw('', html, format='html'), toc]

def collect_metadata(app, env):
    """Collect all tags and categories from document metadata."""
    env.all_tags = set()
    env.all_categories = set()
    env.all_types = set()
    
    for docname in env.found_docs:
        meta = env.metadata.get(docname, {})
        if 'tags' in meta:
            tags_meta = meta['tags']
            if isinstance(tags_meta, str):
                tags = [tag.strip() for tag in tags_meta.split(',')]
            else:
                tags = tags_meta
            env.all_tags.update(tags)
        if 'categories' in meta:
            categories_meta = meta['categories']
            if isinstance(categories_meta, str):
                categories = [cat.strip() for cat in categories_meta.split(',')]
            else:
                categories = categories_meta
            env.all_categories.update(categories)
        if 'type' in meta:
            env.all_types.add(meta['type'])

def generate_taxonomy_pages(app):
    """Dynamically generate pages for each tag and category."""
    env = app.env
    if hasattr(env, 'all_tags'):
        for tag in env.all_tags:
            articles = []
            for docname in env.found_docs:
                meta = env.metadata.get(docname, {})
                if 'tags' in meta:
                    tags_meta = meta['tags']
                    if isinstance(tags_meta, str):
                        tags = [t.strip() for t in tags_meta.split(',')]
                    else:
                        tags = tags_meta
                    if tag in tags:
                        title_node = env.titles.get(docname)
                        if title_node:
                            item = {
                                'title': title_node.astext(),
                                'docname': docname,
                                'excerpt_text': '',
                                'excerpt_figure_filename': None,
                            }
                            item.update(meta)

                            doctree = env.get_doctree(docname)
                            
                            # Find first paragraph or blockquote
                            first_text = None
                            for node in doctree.traverse(lambda n: isinstance(n, (nodes.paragraph, nodes.block_quote))):
                                first_text = node
                                break
                            
                            if first_text:
                                item['excerpt_text'] = app.builder.render_partial(first_text)['html_body']

                            # Find first figure
                            for node in doctree.traverse(nodes.figure):
                                image_node = next(iter(node.traverse(nodes.image)), None)
                                if image_node:
                                    item['excerpt_figure_filename'] = os.path.basename(image_node['uri'])
                                    item['excerpt_figure_alt'] = image_node.get('alt', '')
                                    item['excerpt_figure_width'] = node.get('width')
                                    break
                            
                            articles.append(item)
            
            articles.sort(key=lambda x: to_numeric(x.get('number', 0)), reverse=True) # Sort by 'number' descending

            context = {
                'collection': {
                    'title': f"Posts tagged '{tag}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                }
            }
            yield (f'tags/{tag}', context, 'tag_page.html')

    if hasattr(env, 'all_categories'):
        for category in env.all_categories:
            articles = []
            for docname in env.found_docs:
                meta = env.metadata.get(docname, {})
                if 'categories' in meta:
                    categories_meta = meta['categories']
                    if isinstance(categories_meta, str):
                        categories = [c.strip() for c in categories_meta.split(',')]
                    else:
                        categories = categories_meta
                    if category in categories:
                        title_node = env.titles.get(docname)
                        if title_node:
                            item = {
                                'title': title_node.astext(),
                                'docname': docname,
                                'excerpt_text': '',
                                'excerpt_figure_filename': None,
                            }
                            item.update(meta)

                            doctree = env.get_doctree(docname)
                            
                            # Find first paragraph or blockquote
                            first_text = None
                            for node in doctree.traverse(lambda n: isinstance(n, (nodes.paragraph, nodes.block_quote))):
                                first_text = node
                                break
                            
                            if first_text:
                                item['excerpt_text'] = app.builder.render_partial(first_text)['html_body']

                            # Find first figure
                            for node in doctree.traverse(nodes.figure):
                                image_node = next(iter(node.traverse(nodes.image)), None)
                                if image_node:
                                    item['excerpt_figure_filename'] = os.path.basename(image_node['uri'])
                                    item['excerpt_figure_alt'] = image_node.get('alt', '')
                                    item['excerpt_figure_width'] = node.get('width')
                                    break
                            
                            articles.append(item)
            
            articles.sort(key=lambda x: to_numeric(x.get('number', 0)), reverse=True) # Sort by 'number' descending

            context = {
                'collection': {
                    'title': f"Posts in category '{category}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                }
            }
            yield (f'categories/{category}', context, 'category_page.html')

    if hasattr(env, 'all_types'):
        for type_ in env.all_types:
            articles = []
            for docname in env.found_docs:
                meta = env.metadata.get(docname, {})
                if 'type' in meta and meta['type'] == type_:
                    title_node = env.titles.get(docname)
                    if title_node:
                        item = {
                            'title': title_node.astext(),
                            'docname': docname,
                            'excerpt_text': '',
                            'excerpt_figure': '',
                        }
                        item.update(meta)

                        doctree = env.get_doctree(docname)
                        
                        # Find first paragraph or blockquote
                        first_text = None
                        for node in doctree.traverse(lambda n: isinstance(n, (nodes.paragraph, nodes.block_quote))):
                            first_text = node
                            break
                        
                        if first_text:
                            item['excerpt_text'] = app.builder.render_partial(first_text)['html_body']

                        # Find first figure
                        first_figure = None
                        for node in doctree.traverse(nodes.figure):
                            # Adjust image URI to be relative to the document
                            for img in node.traverse(nodes.image):
                                img['uri'] = os.path.relpath(os.path.join(env.srcdir, img['uri']), os.path.join(env.srcdir, os.path.dirname(docname)))
                            first_figure = node
                            break

                        if first_figure:
                            item['excerpt_figure'] = app.builder.render_partial(first_figure)['html_body']
                        
                        articles.append(item)
            
            articles.sort(key=lambda x: to_numeric(x.get('number', 0)), reverse=True) # Sort by 'number' descending

            context = {
                'collection': {
                    'title': f"Content of type '{type_}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                }
            }
            yield (f'types/{type_}', context, 'type_page.html')

def build_nav_links(app, pagename: str, templatename: str, context: dict, doctree) -> None:
    """Build navigation links and add tags/categories to the context."""
    context['tags'] = sorted(list(app.env.all_tags)) if hasattr(app.env, 'all_tags') else []
    context['categories'] = sorted(list(app.env.all_categories)) if hasattr(app.env, 'all_categories') else []
    context['types'] = sorted(list(app.env.all_types)) if hasattr(app.env, 'all_types') else []

    if 'meta' in context and context['meta']:
        if 'tags' in context['meta'] and isinstance(context['meta']['tags'], str):
            context['meta']['tags'] = [tag.strip() for tag in context['meta']['tags'].split(',')]
        if 'categories' in context['meta'] and isinstance(context['meta']['categories'], str):
            context['meta']['categories'] = [cat.strip() for cat in context['meta']['categories'].split(',')]

    header_nav_list = []
    footer_nav_list = []
    recent_logs = []
    for docname in app.env.found_docs:
        meta = app.env.metadata.get(docname, {})
        if meta.get('navigation') == 'header':
            title = app.env.titles.get(docname)
            if title:
                header_nav_list.append({
                    'docname': docname,
                    'title': title.astext(),
                    'order': meta.get('order', 0),
                })
        if meta.get('navigation') == 'footer':
            title = app.env.titles.get(docname)
            if title:
                footer_nav_list.append({
                    'docname': docname,
                    'title': title.astext(),
                    'order': meta.get('order', 0),
                })
        if meta.get('type') == 'log':
            title = app.env.titles.get(docname)
            if title:
                recent_logs.append({
                    'docname': docname,
                    'title': title.astext(),
                    'date': meta.get('date', ''),
                })

    header_nav_list.sort(key=lambda x: to_numeric(x['order']))
    context['header_nav_list'] = header_nav_list

    footer_nav_list.sort(key=lambda x: to_numeric(x['order']))
    context['footer_nav_list'] = footer_nav_list

    recent_logs.sort(key=lambda x: x['date'], reverse=True)
    context['recent_logs'] = recent_logs[:5]

def setup(app) -> dict:
    """Register directives and connect to Sphinx events."""
    app.add_directive("collection", CollectionDirective)
    app.connect('env-updated', collect_metadata)
    app.connect('html-collect-pages', generate_taxonomy_pages)
    app.connect('html-page-context', build_nav_links)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
