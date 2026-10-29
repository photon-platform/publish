"""Directive for creating content collections."""

import os
import re
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri
from docutils.parsers.rst import directives
from docutils import nodes
from sphinx.addnodes import toctree
from typing import Dict, Any, List
try:
    from photon_platform.publish.images import picture_node, prepare_inline_svg
except ImportError:
    picture_node = None
    prepare_inline_svg = None



def to_numeric(value: Any) -> int | float | Any:
    """Convert a value to a numeric type if possible, trying int then float.

    Args:
        value: The value to convert.

    Returns:
        The converted numeric value, or the original value if conversion fails.

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


def safe_numeric(value: Any, default: int | float = 999) -> int | float:
    """Safely convert a value to a numeric type for sorting.

    Args:
        value: The value to convert.
        default: The default value to return if conversion fails.

    Returns:
        The converted numeric value or the default.

    """
    res = to_numeric(value)
    if isinstance(res, (int, float)):
        return res
    return default


class PendingCollection(nodes.General, nodes.Element):
    """A placeholder node for a collection.

    This node will be rendered after all documents have been read and metadata is available.
    """

    pass


class CollectionDirective(SphinxDirective):
    """Directive to insert a collection of articles."""

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
        'depth': directives.positive_int,
        'recursive': directives.flag,
    }


    def run(self) -> List[nodes.Node]:
        """Process the collection directive.

        Instead of rendering immediately, this method:
        1. Discovers all relevant files respecting the Container Boundary Rule.
        2. Filters by :type: early before claiming documents in the toctree.
        3. Adds them to a hidden toctree so Sphinx knows about them (fixes "not in toctree" warnings).
        4. Returns a PendingCollection node to defer rendering until metadata is ready.

        Returns:
            A list containing the PendingCollection node and a hidden toctree node.

        """
        env = self.env
        
        collection_type = self.options.get('type')
        sort_key = self.options.get('sort')
        reverse = 'reverse' in self.options
        max_depth = self.options.get('depth', 1)
        recursive = 'recursive' in self.options
        
        docnames = []
        excluded_dirs = {'.git', '__pycache__', '.doctrees', '_static', '_templates'}

        def get_early_meta(docname: str) -> Dict[str, Any]:
            meta = dict(env.metadata.get(docname, {}))
            path = os.path.join(env.srcdir, docname + '.rst')
            if os.path.exists(path):
                early_meta = peek_metadata(path)
                for k, v in early_meta.items():
                    meta.setdefault(k, v)
            return meta

        if collection_type == 'header':
            # Scan GLOBAL source directory for header items
            # We must use peek_metadata because env.metadata might not be populated yet
            # for files we haven't read.
            for root, dirs, files in os.walk(env.srcdir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith('.')]
                
                for filename in files:
                    if filename.endswith('.rst'):
                        path = os.path.join(root, filename)
                        docname = os.path.splitext(os.path.relpath(path, env.srcdir))[0]
                        
                        if docname == env.docname:
                            continue

                        meta = peek_metadata(path)
                        if meta.get('navigation') == 'header':
                            order = safe_numeric(meta.get('order', 999))
                            docnames.append((docname, order))
            
            # Sort by order
            docnames.sort(key=lambda x: x[1])
            docnames = [d[0] for d in docnames]

        else:
            # Standard behavior: Scan LOCAL directory respecting the Container Boundary Rule
            current_dir = os.path.dirname(env.docname)
            walk_path = os.path.join(env.srcdir, current_dir)
            
            if os.path.exists(walk_path):
                # Track container depth (number of index.rst container boundaries from walk_path)
                container_depths: Dict[str, int] = {os.path.abspath(walk_path): 1}

                for root, dirs, files in os.walk(walk_path):
                    abs_root = os.path.abspath(root)
                    cur_depth = container_depths.get(abs_root, 1)

                    dirs[:] = sorted(
                        d for d in dirs if d not in excluded_dirs and not d.startswith('.')
                    )

                    # Include direct .rst files in current directory
                    for filename in sorted(files):
                        if filename.endswith('.rst'):
                            path = os.path.join(root, filename)
                            docname = os.path.splitext(os.path.relpath(path, env.srcdir))[0]
                            if docname != env.docname and docname not in docnames:
                                docnames.append(docname)

                    # Inspect subdirectories for sub-container boundaries (index.rst)
                    for d in list(dirs):
                        sub_dir_path = os.path.abspath(os.path.join(root, d))
                        sub_index_path = os.path.join(sub_dir_path, 'index.rst')
                        if os.path.exists(sub_index_path):
                            if not recursive and cur_depth >= max_depth:
                                sub_docname = os.path.splitext(
                                    os.path.relpath(sub_index_path, env.srcdir)
                                )[0]
                                if sub_docname != env.docname and sub_docname not in docnames:
                                    docnames.append(sub_docname)
                                # Prune sub-container so os.walk does not bleed its children into parent
                                dirs.remove(d)
                            else:
                                container_depths[sub_dir_path] = cur_depth + 1
                        else:
                            container_depths[sub_dir_path] = cur_depth

            # Filter by :type: early before claiming docnames in toctree
            if collection_type:
                docnames = [
                    d for d in docnames
                    if get_early_meta(d).get('type') == collection_type
                ]

            # Best-effort sort for toctree
            if sort_key:
                def get_sort_val(docname: str) -> Any:
                    meta = get_early_meta(docname)
                    if sort_key in meta and meta[sort_key] is not None:
                        return to_numeric(meta[sort_key])
                    return 0
                docnames.sort(key=get_sort_val, reverse=reverse)

        # Create a toctree with discovered items matching this collection
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


def render_node_html(builder: Any, node: nodes.Node) -> str:
    """Render a docutils node to an HTML fragment string.

    Compatible with Sphinx <9 (which included 'html_body' and 'fragment')
    and Sphinx >=9 (which returns only 'fragment' and 'title').

    Args:
        builder: The Sphinx HTML builder instance.
        node: The docutils node to render.

    Returns:
        The rendered HTML string.

    """
    from sphinx.addnodes import pending_xref

    node_copy = node.deepcopy()
    for xref in list(node_copy.findall(pending_xref)):
        xref.replace_self(list(xref.children))
    for fn_ref in list(node_copy.findall(nodes.footnote_reference)):
        if fn_ref.parent is not None:
            fn_ref.parent.remove(fn_ref)
    try:
        from .elements import folio_node

        for fn_node in list(node_copy.findall(folio_node)):
            if fn_node.parent is not None:
                fn_node.parent.remove(fn_node)
    except ImportError:
        pass

    parts = builder.render_partial(node_copy)
    html = parts.get('fragment') or parts.get('html_body', '')
    html = re.sub(r'<main[^>]*>', '', html)
    html = re.sub(r'</main>', '', html)
    html = re.sub(r'<sup class="line-num">.*?</sup>\s*', '', html)
    html = re.sub(
        r'<a\s+class="((?:term-ref|person-ref|citation-ref|reference)[^"]*)"[^>]*>(.*?)</a>',
        r'<span class="\1">\2</span>',
        html,
    )
    return html.strip()


def _find_first_excerpt_node(doctree: nodes.document) -> nodes.Node | None:
    """Return the enunciation node if present, otherwise the first paragraph or block_quote node not nested inside an admonition, figure, signature, or collapse."""
    skip_types: tuple[type, ...] = (nodes.Admonition, nodes.figure)
    try:
        from .elements import collapse_node, enunciation_node, signature_node

        for enun in doctree.findall(enunciation_node):
            return enun
        skip_types = (nodes.Admonition, nodes.figure, signature_node, collapse_node)
    except ImportError:
        pass
    for n in doctree.findall(lambda node: isinstance(node, (nodes.paragraph, nodes.block_quote))):
        curr = n.parent
        in_skip = False
        while curr is not None:
            if isinstance(curr, skip_types):
                in_skip = True
                break
            curr = curr.parent
        if not in_skip:
            return n
    return None


def process_collections(app: Any, doctree: nodes.document, fromdocname: str) -> None:
    """Resolve PendingCollection nodes into actual HTML content.

    This runs on 'doctree-resolved', when all metadata is available.

    Args:
        app: The Sphinx application instance.
        doctree: The document tree.
        fromdocname: The document name.

    """
    env = app.env
    builder = app.builder
    
    for node in doctree.traverse(PendingCollection):
        options = node['options']
        docnames = node['docnames']
        
        # Determine the template path based on the current theme
        # Determine the template path based on the current theme
        default_template = 'collection/index.html'

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
                        # Find first paragraph or blockquote outside admonitions
                        first_text = _find_first_excerpt_node(item_doctree)
                        
                        if first_text:
                            item['excerpt_text'] = render_node_html(builder, first_text)

                        # Check for explicitly set featured image (from .. picture::)
                        if 'featured_image' in meta:
                             item['excerpt_figure_filename'] = meta['featured_image']
                             item['excerpt_figure_alt'] = meta.get('featured_image_alt') or item['title']
                        
                        # Fallback: Find first figure/picture if no featured image
                        if not item['excerpt_figure_filename']:
                            # Check for picture_node first (custom)
                            if picture_node:
                                for n in item_doctree.traverse(picture_node):
                                    if 'main_src' in n:
                                        item['excerpt_figure_filename'] = n['main_src']
                                        item['excerpt_figure_alt'] = n.get('alt', '')
                                        # picture_node doesn't enforce width in the same way, or it's implicitly 800
                                        break
                            
                            # Check for standard figure if still not found
                            if not item['excerpt_figure_filename']:
                                for n in item_doctree.traverse(nodes.figure):
                                    image_node = next(iter(n.traverse(nodes.image)), None)
                                    if image_node:
                                        item['excerpt_figure_filename'] = os.path.join(
                                            builder.imagedir, os.path.basename(image_node['uri'])
                                        )
                                        item['excerpt_figure_alt'] = image_node.get('alt', '')
                                        item['excerpt_figure_width'] = n.get('width')
                                        break

                    fig_file = item.get('excerpt_figure_filename')
                    if (
                        prepare_inline_svg
                        and isinstance(fig_file, str)
                        and fig_file.lower().endswith('.svg')
                    ):
                        rel_fig = fig_file.lstrip('/')
                        svg_src_path = os.path.join(env.srcdir, rel_fig)
                        if not os.path.isfile(svg_src_path):
                            svg_src_path = os.path.join(builder.outdir, rel_fig)
                        item['excerpt_svg_content'] = prepare_inline_svg(
                            svg_src_path, as_thumbnail=True
                        )

                    if 'tags' in item and isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    if 'categories' in item and isinstance(item['categories'], str):
                        item['categories'] = [cat.strip() for cat in item['categories'].split(',') if cat.strip()]
                    if 'category' in item and isinstance(item['category'], str):
                        item['category'] = [cat.strip() for cat in item['category'].split(',') if cat.strip()]
                        item.setdefault('categories', item['category'])
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

        if 'class="math' in html and 'math' in env.domains:
            env.domains['math'].data.setdefault('has_equations', {})[fromdocname] = True
        
        node.replace_self(nodes.raw('', html, format='html'))


def _split_meta_list(val: Any) -> List[str]:
    if not val:
        return []
    if isinstance(val, str):
        return [v.strip() for v in val.split(',') if v.strip()]
    if isinstance(val, (list, tuple, set)):
        return [str(v).strip() for v in val if str(v).strip()]
    return []


def _build_taxonomy_article_item(app: Any, env: Any, docname: str, meta: Dict[str, Any], title_node: nodes.Node) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        'title': title_node.astext(),
        'docname': docname,
        'excerpt_text': '',
        'excerpt_figure_filename': None,
    }
    item.update(meta)
    if 'tags' in item:
        item['tags'] = _split_meta_list(item['tags'])
    if 'categories' in item:
        item['categories'] = _split_meta_list(item['categories'])
    if 'category' in item:
        item['category'] = _split_meta_list(item['category'])
        item.setdefault('categories', item['category'])

    try:
        doctree = env.get_doctree(docname)
    except Exception:
        doctree = None

    if doctree:
        first_text = _find_first_excerpt_node(doctree)
        if first_text:
            item['excerpt_text'] = render_node_html(app.builder, first_text)

        if 'featured_image' in meta:
            item['excerpt_figure_filename'] = meta['featured_image']
            item['excerpt_figure_alt'] = meta.get('featured_image_alt') or item['title']

        if not item['excerpt_figure_filename'] and picture_node:
            for n in doctree.traverse(picture_node):
                if 'main_src' in n:
                    item['excerpt_figure_filename'] = n['main_src']
                    item['excerpt_figure_alt'] = n.get('alt', '')
                    break

        if not item['excerpt_figure_filename']:
            for node in doctree.traverse(nodes.figure):
                image_node = next(iter(node.traverse(nodes.image)), None)
                if image_node:
                    item['excerpt_figure_filename'] = os.path.join(
                        app.builder.imagedir, os.path.basename(image_node['uri'])
                    )
                    item['excerpt_figure_alt'] = image_node.get('alt', '')
                    item['excerpt_figure_width'] = node.get('width')
                    break

    fig_file = item.get('excerpt_figure_filename')
    if (
        prepare_inline_svg
        and isinstance(fig_file, str)
        and fig_file.lower().endswith('.svg')
    ):
        rel_fig = fig_file.lstrip('/')
        svg_src_path = os.path.join(env.srcdir, rel_fig)
        if not os.path.isfile(svg_src_path):
            svg_src_path = os.path.join(app.builder.outdir, rel_fig)
        item['excerpt_svg_content'] = prepare_inline_svg(
            svg_src_path, as_thumbnail=True
        )
    return item


def _sort_taxonomy_articles(articles: List[Dict[str, Any]]) -> None:
    if any('number' in a for a in articles):
        articles.sort(key=lambda x: safe_numeric(x.get('number', 0)), reverse=True)
    elif any('order' in a for a in articles):
        articles.sort(key=lambda x: safe_numeric(x.get('order', 999999)))
    else:
        articles.sort(key=lambda x: str(x.get('title', '')))


def collect_metadata(app: Any, env: Any) -> None:
    """Collect all tags and categories from document metadata.

    Args:
        app: The Sphinx application instance.
        env: The build environment.

    """
    env.all_tags = set()
    env.all_categories = set()
    env.all_types = set()
    
    for docname in env.found_docs:
        meta = env.metadata.get(docname, {})
        if 'tags' in meta:
            env.all_tags.update(_split_meta_list(meta['tags']))
        if 'categories' in meta:
            env.all_categories.update(_split_meta_list(meta['categories']))
        if 'category' in meta:
            env.all_categories.update(_split_meta_list(meta['category']))
        if 'type' in meta and meta['type']:
            env.all_types.add(str(meta['type']).strip())

def generate_taxonomy_pages(app: Any) -> Any:
    """Dynamically generate pages for each tag and category.

    Args:
        app: The Sphinx application instance.

    Yields:
        Tuple containing context, template name, and output path for each page.

    """
    if getattr(getattr(app, "builder", None), "name", "") == "epub":
        return
    env = app.env
    if hasattr(env, 'all_tags'):
        for tag in env.all_tags:
            articles = []
            for docname in env.found_docs:
                meta = env.metadata.get(docname, {})
                if 'tags' in meta and tag in _split_meta_list(meta['tags']):
                    title_node = env.titles.get(docname)
                    if title_node:
                        articles.append(_build_taxonomy_article_item(app, env, docname, meta, title_node))
            
            _sort_taxonomy_articles(articles)

            context = {
                'collection': {
                    'title': f"Posts tagged '{tag}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                },
                'has_maths_elements': any('class="math' in a.get('excerpt_text', '') for a in articles),
            }
            yield (f'tags/{tag}', context, 'tag_page.html')

    if hasattr(env, 'all_categories'):
        for category in env.all_categories:
            articles = []
            for docname in env.found_docs:
                meta = env.metadata.get(docname, {})
                cats = _split_meta_list(meta.get('categories')) or _split_meta_list(meta.get('category'))
                if category in cats:
                    title_node = env.titles.get(docname)
                    if title_node:
                        articles.append(_build_taxonomy_article_item(app, env, docname, meta, title_node))
            
            _sort_taxonomy_articles(articles)

            context = {
                'collection': {
                    'title': f"Posts in category '{category}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                },
                'has_maths_elements': any('class="math' in a.get('excerpt_text', '') for a in articles),
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
                        articles.append(_build_taxonomy_article_item(app, env, docname, meta, title_node))
            
            _sort_taxonomy_articles(articles)

            context = {
                'collection': {
                    'title': f"Content of type '{type_}'",
                    'articles': articles,
                    'sort_key': 'number',
                    'reverse': True,
                },
                'has_maths_elements': any('class="math' in a.get('excerpt_text', '') for a in articles),
            }
            yield (f'types/{type_}', context, 'type_page.html')

def build_nav_links(
    app: Any, pagename: str, templatename: str, context: Dict[str, Any], doctree: nodes.document
) -> None:
    """Build navigation links and add tags/categories to the context.

    Args:
        app: The Sphinx application instance.
        pagename: The name of the page.
        templatename: The name of the template.
        context: The context for rendering.
        doctree: The document tree.

    """
    if not context.get('has_maths_elements') and doctree is not None:
        for raw_node in doctree.findall(nodes.raw):
            if 'class="math' in raw_node.astext():
                context['has_maths_elements'] = True
                break

    context['tags'] = sorted(list(app.env.all_tags)) if hasattr(app.env, 'all_tags') else []
    context['categories'] = sorted(list(app.env.all_categories)) if hasattr(app.env, 'all_categories') else []
    context['types'] = sorted(list(app.env.all_types)) if hasattr(app.env, 'all_types') else []

    if 'meta' in context and context['meta']:
        if 'tags' in context['meta'] and isinstance(context['meta']['tags'], str):
            context['meta']['tags'] = _split_meta_list(context['meta']['tags'])
        if 'categories' in context['meta'] and isinstance(context['meta']['categories'], str):
            context['meta']['categories'] = _split_meta_list(context['meta']['categories'])
        if 'category' in context['meta'] and isinstance(context['meta']['category'], str):
            context['meta']['category'] = _split_meta_list(context['meta']['category'])
            context['meta'].setdefault('categories', context['meta']['category'])

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

def peek_metadata(filepath: str) -> Dict[str, str]:
    """Peek at the beginning of a file to extract navigation metadata.

    This enables sorting before Sphinx has fully processed the environment.

    Args:
        filepath: The path to the file to peek at.

    Returns:
        A dictionary containing the extracted metadata.

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



def inject_root_navigation(app: Any, docname: str, source: List[str]) -> None:
    """Automatically inject a hidden toctree into the master document (Root).

    This includes any document with :navigation: header or :navigation: footer.

    Args:
        app: The Sphinx application instance.
        docname: The name of the document.
        source: The list of source strings (mutable).

    """
    if getattr(getattr(app, "builder", None), "name", "") == "epub":
        return
    if docname != app.config.master_doc:
        return

    env = app.env
    header_docs = []
    footer_docs = []

    # Recursively scan docsrc (srcdir) for header/footer items
    for root, dirs, files in os.walk(env.srcdir):
        # Exclude dot-directories and standard Sphinx folders
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        if '_static' in dirs:
            dirs.remove('_static')
        if '_templates' in dirs:
            dirs.remove('_templates')

        for filename in files:
            if filename.endswith('.rst'):
                path = os.path.join(root, filename)
                found_docname = os.path.splitext(os.path.relpath(path, env.srcdir))[0]
                
                # Exclude master doc itself
                if found_docname == docname:
                    continue
                
                meta = peek_metadata(path)
                nav = meta.get('navigation')
                
                if nav == 'header' or nav == 'footer':
                    order_val = safe_numeric(meta.get('order', 999))
                    item = {'docname': found_docname, 'order': order_val}
                    
                    if nav == 'header':
                        header_docs.append(item)
                    elif nav == 'footer':
                        footer_docs.append(item)

    # Sort
    header_docs.sort(key=lambda x: x['order'])
    footer_docs.sort(key=lambda x: x['order'])
    
    # Combine (Header first, then Footer)
    final_docnames = [x['docname'] for x in header_docs] + \
                     [x['docname'] for x in footer_docs]

    if final_docnames:
        toctree_rst = "\n\n.. toctree::\n   :hidden:\n\n"
        for d in final_docnames:
            toctree_rst += f"   {d}\n"
        
        source[0] += toctree_rst


def setup(app: Any) -> Dict[str, Any]:
    """Register directives and connect to Sphinx events.

    Args:
        app: The Sphinx application instance.

    Returns:
        A dictionary containing extension metadata.

    """
    app.add_node(PendingCollection)
    app.add_directive("collection", CollectionDirective)
    app.connect('env-updated', collect_metadata)
    app.connect('html-collect-pages', generate_taxonomy_pages)
    app.connect('html-page-context', build_nav_links, priority=100)
    app.connect('source-read', inject_root_navigation)
    app.connect('doctree-resolved', process_collections)
    app.add_js_file('js/collection_controls.js')
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
