import os
from functools import partial
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri
from docutils.parsers.rst import directives
from docutils import nodes
from sphinx.addnodes import toctree
from typing import Dict, Any, List, Optional



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


def safe_numeric(value, default=999):
    """
    Safely converts a value to a numeric type for sorting.
    Returns default if conversion fails.
    """
    res = to_numeric(value)
    if isinstance(res, (int, float)):
        return res
    return default


class PendingCollection(nodes.General, nodes.Element):
    """
    A placeholder node for a collection that will be rendered
    after all documents have been read and metadata is available.
    """
    pass


class CollectionDirective(SphinxDirective):
    has_content: bool = False
    option_spec: Dict[str, Any] = {
        'type': directives.unchanged,
        'sort': directives.unchanged,
        'reverse': directives.flag,
        'template': directives.unchanged,
        'limit': directives.positive_int,
        'title': directives.unchanged,
        'class': directives.unchanged,
        'hidden': directives.flag,
    }

    def run(self):
        """
        Process the collection directive.
        
        Instead of rendering immediately, we:
        1. Discover all relevant files.
        2. Add them to a hidden toctree so Sphinx knows about them (fixes "not in toctree" warnings).
        3. Return a PendingCollection node to defer rendering until metadata is ready.
        """
        env = self.env
        
        collection_type = self.options.get('type')
        sort_key = self.options.get('sort')
        reverse = 'reverse' in self.options
        limit = self.options.get('limit')
        
        # Discover files automatically, but not recursively deep
        current_dir = os.path.dirname(env.docname)
        walk_path = os.path.join(env.srcdir, current_dir)
        docnames = []

        # Process current directory
        # Process current directory and subdirectories recursively
        if os.path.exists(walk_path):
            for root, dirs, files in os.walk(walk_path):
                for filename in files:
                    if filename.endswith('.rst'):
                        path = os.path.join(root, filename)
                        docname = os.path.splitext(os.path.relpath(path, env.srcdir))[0]
                        if docname != env.docname:
                            docnames.append(docname)

        # Best-effort sort for toctree (using currently available metadata)
        # This ensures that if metadata IS available (e.g. subsequent builds),
        # the navigation order is correct.
        if sort_key:
            def get_sort_val(docname):
                meta = env.metadata.get(docname, {})
                val = meta.get(sort_key)
                if val:
                    return to_numeric(val)
                return 0
            docnames.sort(key=get_sort_val, reverse=reverse)

        # Create a toctree with ALL discovered items
        # This ensures they are included in the build and not orphaned.
        if not hasattr(self.env, 'photon_publish_collection_docnames'):
            self.env.photon_publish_collection_docnames = set()

        unique_toc_docnames = []
        for docname in docnames:
            if docname not in self.env.photon_publish_collection_docnames:
                unique_toc_docnames.append(docname)
                self.env.photon_publish_collection_docnames.add(docname)

        toc = toctree()
        toc['glob'] = False
        toc['hidden'] = True
        toc['includefiles'] = unique_toc_docnames
        toc['entries'] = [(None, docname) for docname in unique_toc_docnames]

        # Create PendingCollection node
        pending = PendingCollection()
        pending['docnames'] = docnames
        pending['options'] = self.options
        
        return [pending, toc]


def process_collections(app, doctree, fromdocname):
    """
    Resolve PendingCollection nodes into actual HTML content.
    This runs on 'doctree-resolved', when all metadata is available.
    """
    env = app.env
    builder = app.builder
    
    for node in doctree.traverse(PendingCollection):
        options = node['options']
        docnames = node['docnames']
        
        # Determine the template path based on the current theme
        # Determine the template path based on the current theme
        default_template = 'components/collection/collection.html'

        collection_type = options.get('type')
        sort_key = options.get('sort')
        reverse = 'reverse' in options
        template_name = options.get('template', default_template)
        limit = options.get('limit')
        title = options.get('title')
        collection_class = options.get('class', '')
        hidden = 'hidden' in options

        if hidden:
            node.replace_self([])
            return

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

                    # We need to load the doctree to get excerpt/figure
                    # Since we are in doctree-resolved, the pickle should exist/be up to date
                    try:
                        item_doctree = env.get_doctree(docname)
                    except Exception:
                        # Fallback if doctree cannot be loaded
                        item_doctree = None

                    if item_doctree:
                        # Find first paragraph or blockquote
                        first_text = None
                        for n in item_doctree.traverse(lambda n: isinstance(n, (nodes.paragraph, nodes.block_quote))):
                            first_text = n
                            break
                        
                        if first_text:
                            item['excerpt_text'] = builder.render_partial(first_text)['html_body']

                        # Find first figure
                        for n in item_doctree.traverse(nodes.figure):
                            image_node = next(iter(n.traverse(nodes.image)), None)
                            if image_node:
                                item['excerpt_figure_filename'] = os.path.basename(image_node['uri'])
                                item['excerpt_figure_alt'] = image_node.get('alt', '')
                                item['excerpt_figure_width'] = n.get('width')
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
                return relative_uri(builder.get_target_uri(fromdocname), otheruri)
            return builder.get_relative_uri(fromdocname, otheruri)
            
        context = {
            'collection': {
                'title': title,
                'articles': collection_items,
                'class': collection_class,
            },
            'pathto': pathto,
        }

        jinja_env = builder.templates.environment
        template = jinja_env.get_template(template_name)
        html = template.render(context)
        
        node.replace_self(nodes.raw('', html, format='html'))


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
            
            articles.sort(key=lambda x: safe_numeric(x.get('number', 0)), reverse=True) # Sort by 'number' descending

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
            
            articles.sort(key=lambda x: safe_numeric(x.get('number', 0)), reverse=True) # Sort by 'number' descending

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
            
            articles.sort(key=lambda x: safe_numeric(x.get('number', 0)), reverse=True) # Sort by 'number' descending

            context = {
                'collection': {
                    'title': f"Content of type '{type_}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                }
            }
            yield (f'types/{type_}', context, 'type_page.html')

def build_nav_links(app, pagename, templatename, context, doctree):
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

    header_nav_list.sort(key=lambda x: safe_numeric(x['order']))
    context['header_nav_list'] = header_nav_list

    footer_nav_list.sort(key=lambda x: safe_numeric(x['order']))
    context['footer_nav_list'] = footer_nav_list

    recent_logs.sort(key=lambda x: x['date'], reverse=True)
    context['recent_logs'] = recent_logs[:5]

def peek_metadata(filepath):
    """
    Peek at the beginning of a file to extract navigation metadata.
    This enables sorting before Sphinx has fully processed the environment.
    """
    meta = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Read first 20 lines or 2KB, whichever comes first
            # We only care about the initial field list.
            head = f.read(2048)
            lines = head.split('\n')[:20]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Simple field list parsing (e.g. :navigation: header)
                if line.startswith(':') and ':' in line[1:]:
                    parts = line[1:].split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip()
                        meta[key] = val
                # Stop if we hit a section title or non-field-list content
                # (A very rough heuristic: if it doesn't start with :, isn't a comment .., and isn't empty)
                elif not line.startswith('..') and len(line) > 0:
                    break
    except Exception:
        pass
    return meta

def inject_implicit_toctree(app, docname, source):
    """
    Inject a hidden toctree into the master document via source modification.
    This runs before parsing, ensuring Sphinx correctly processes the toctree.
    """
    if docname != app.config.master_doc:
        return

    env = app.env
    
    header_docs = []
    footer_docs = []
    other_docs = []
    
    found_docs = set()
    
    # Recursively scan for all .rst files to include
    for root, dirs, files in os.walk(env.srcdir):
        for filename in files:
            if filename.endswith('.rst'):
                path = os.path.join(root, filename)
                # relpath generally works relative to srcdir for source filenames
                found_docname = os.path.splitext(os.path.relpath(path, env.srcdir))[0]
                
                # Exclude master doc to avoid circular inclusion
                if found_docname == docname:
                    continue
                    
                if found_docname not in found_docs:
                    found_docs.add(found_docname)
                    
                    # Peek at metadata for sorting
                    meta = peek_metadata(path)
                    nav = meta.get('navigation')
                    order_val = safe_numeric(meta.get('order', 999))
                    
                    item = {'docname': found_docname, 'order': order_val}
                    
                    if nav == 'header':
                        header_docs.append(item)
                    elif nav == 'footer':
                        footer_docs.append(item)
                    else:
                        other_docs.append(item)

    # Sort buckets
    header_docs.sort(key=lambda x: x['order'])
    footer_docs.sort(key=lambda x: x['order'])
    other_docs.sort(key=lambda x: x['docname']) # Alphabetical for others

    # Combine all docs
    # Order: Header -> Footer -> Others
    final_docnames = [x['docname'] for x in header_docs] + \
                     [x['docname'] for x in footer_docs] + \
                     [x['docname'] for x in other_docs]

    if final_docnames:
        # Inject ReST for a hidden toctree
        toctree_rst = "\n\n.. toctree::\n   :hidden:\n\n"
        for d in final_docnames:
            toctree_rst += f"   {d}\n"
        
        source[0] += toctree_rst

def setup(app):
    """Register directives and connect to Sphinx events."""
    app.add_node(PendingCollection)
    app.add_directive("collection", CollectionDirective)
    app.connect('env-updated', collect_metadata)
    app.connect('html-collect-pages', generate_taxonomy_pages)
    app.connect('html-page-context', build_nav_links)
    app.connect('source-read', inject_implicit_toctree)
    app.connect('doctree-resolved', process_collections)
    app.add_js_file('js/collection_controls.js')
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
