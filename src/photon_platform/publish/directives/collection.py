"""Directive for creating content collections."""

import os
import re
import shutil
from pathlib import Path
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri
from docutils.parsers.rst import directives
from docutils import nodes
from sphinx.addnodes import toctree
from typing import Any, Dict, List, Optional, Tuple
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


def safe_sort_key(value: Any) -> tuple[int, float, str]:
    """Return a type-safe comparable tuple for sorting mixed numeric and string metadata."""
    if value is None or value == "":
        return (2, 999999.0, "")
    res = to_numeric(value)
    if isinstance(res, (int, float)):
        return (0, float(res), "")
    return (1, 0.0, str(res))


def _normalize_log_meta(docname: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Infer :type: log and :date: from docnames under log/<stamp>/ when omitted."""
    if docname.startswith("log/") and docname != "log/index":
        meta.setdefault("type", "log")
        if not meta.get("date"):
            parts = docname.split("/")
            if len(parts) >= 2 and parts[1] != "index":
                meta["date"] = parts[1]
    return meta


class PendingCollection(nodes.General, nodes.Element):
    """A placeholder node for a collection.

    This node will be rendered after all documents have been read and metadata is available.
    """

    pass


class CollectionDirective(SphinxDirective):
    """Directive to insert a collection of articles."""

    has_content: bool = True
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
        'docs': directives.unchanged,
    }


    def run(self) -> List[nodes.Node]:
        """Process the collection directive.

        Instead of rendering immediately, this method:
        1. Discovers all relevant files respecting the Container Boundary Rule or explicit doc list.
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
            return _normalize_log_meta(docname, meta)

        explicit_docs = []
        if self.options.get('docs'):
            explicit_docs.extend(
                [d.strip() for d in re.split(r'[, \t\n]+', self.options['docs']) if d.strip()]
            )
        if self.content:
            for line in self.content:
                line_str = line.strip()
                if line_str.startswith(':doc:'):
                    line_str = line_str[len(':doc:'):].strip()
                elif line_str.startswith('- '):
                    line_str = line_str[2:].strip()
                if line_str:
                    explicit_docs.append(line_str)

        if explicit_docs:
            current_dir = os.path.dirname(env.docname)
            resolved_docs = []
            for ed in explicit_docs:
                clean_ed = ed.lstrip('/')
                cand = f"{current_dir}/{clean_ed}" if current_dir else clean_ed
                cand_norm = os.path.normpath(cand).replace(os.sep, '/')
                resolved_docs.append(cand_norm)
            docnames = resolved_docs
        elif collection_type == 'header':
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
            else:
                _excluded_companion_types = {
                    'book_title', 'translation', 'summary', 'notes',
                    'el', 'la', 'de', 'fr', 'it', 'apparatus',
                }
                docnames = [
                    d for d in docnames
                    if get_early_meta(d).get('type') not in _excluded_companion_types
                ]

            # Best-effort sort for toctree
            if sort_key:
                def get_sort_val(docname: str) -> Any:
                    meta = get_early_meta(docname)
                    return safe_sort_key(meta.get(sort_key))
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
            meta = _normalize_log_meta(docname, dict(env.metadata.get(docname, {})))
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

                    if meta.get('excerpt') and not meta.get('_enunciation_excerpt'):
                        item['excerpt_text'] = f"<p>{meta['excerpt']}</p>"
                    elif item_doctree:
                        # Find enunciation or first paragraph/blockquote outside admonitions
                        first_text = _find_first_excerpt_node(item_doctree)
                        if first_text:
                            item['excerpt_text'] = render_node_html(builder, first_text)
                    if not item['excerpt_text'] and meta.get('excerpt'):
                        item['excerpt_text'] = f"<p>{meta['excerpt']}</p>"

                    fig_info = _resolve_representative_figure(env, builder, docname, meta, item_doctree)
                    if fig_info:
                        item['excerpt_figure_filename'] = fig_info['uri']
                        item['excerpt_figure_alt'] = fig_info.get('alt') or item['title']
                        if fig_info.get('width'):
                            item['excerpt_figure_width'] = fig_info['width']
                        if prepare_inline_svg and fig_info.get('svg_disk_path'):
                            item['excerpt_svg_content'] = prepare_inline_svg(
                                fig_info['svg_disk_path'], as_thumbnail=True
                            )

                    try:
                        from ..book import detect_companion_tracks
                        c_tracks = detect_companion_tracks(env, docname)
                        if len(c_tracks) > 1:
                            item['companion_tracks'] = c_tracks
                    except Exception:
                        pass

                    if 'tags' in item and isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    if 'categories' in item and isinstance(item['categories'], str):
                        item['categories'] = [cat.strip() for cat in item['categories'].split(',') if cat.strip()]
                    if 'category' in item and isinstance(item['category'], str):
                        item['category'] = [cat.strip() for cat in item['category'].split(',') if cat.strip()]
                        item.setdefault('categories', item['category'])
                    if 'languages' in item and isinstance(item['languages'], str):
                        item['languages'] = [lang.strip() for lang in item['languages'].split(',') if lang.strip()]
                    collection_items.append(item)

        if sort_key:
            collection_items.sort(key=lambda x: safe_sort_key(x.get(sort_key)), reverse=reverse)

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
                'directory_kind': options.get('directory_kind', ''),
            },
            'pathto': pathto,
        }

        jinja_env = builder.templates.environment
        try:
            template = jinja_env.get_template(template_name)
        except Exception:
            from jinja2 import Environment, FileSystemLoader

            foundation_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "themes", "foundation")
            )
            fallback_env = Environment(loader=FileSystemLoader(foundation_dir))
            template = fallback_env.get_template(template_name)
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


def _extract_direct_figure(
    env: Any,
    builder: Any,
    docname: str,
    meta: Dict[str, Any],
    doctree: Optional[nodes.document],
) -> Optional[Dict[str, Any]]:
    """Extract direct `:featured_image:`, `.. picture::`, or `.. figure::` from a single `docname`."""
    doc_dir = os.path.dirname(docname)
    srcdir_path = Path(str(env.srcdir)).resolve()
    outdir_path = Path(str(builder.outdir)).resolve()

    def _resolve_asset_paths(raw_ref: str) -> Tuple[str, Optional[str]]:
        clean_ref = raw_ref.strip().lstrip("/")
        is_svg = clean_ref.lower().endswith(".svg")
        candidates: List[Path] = []
        if doc_dir:
            candidates.append((srcdir_path / doc_dir / clean_ref).resolve())
        candidates.append((srcdir_path / clean_ref).resolve())
        candidates.append((outdir_path / clean_ref).resolve())
        if hasattr(builder, "imagedir"):
            candidates.append((outdir_path / builder.imagedir / os.path.basename(clean_ref)).resolve())

        disk_found = next((c for c in candidates if c.is_file()), None)
        # Compute URI relative to outdir root using component-safe Path.is_relative_to
        # (avoiding 'docsrc'.startswith('docs') prefix collisions!)
        if disk_found is not None:
            if disk_found.is_relative_to(outdir_path):
                out_rel = disk_found.relative_to(outdir_path).as_posix()
                return out_rel, (str(disk_found) if is_svg else None)
            if disk_found.is_relative_to(srcdir_path):
                src_rel = disk_found.relative_to(srcdir_path).as_posix()
                if src_rel.startswith("_static/") or (outdir_path / src_rel).is_file():
                    return src_rel, (str(disk_found) if is_svg else None)
                if hasattr(builder, "imagedir"):
                    dest_name = disk_found.name
                    env_images = getattr(env, "images", None)
                    if isinstance(env_images, dict):
                        img_entry = env_images.get(src_rel)
                        if isinstance(img_entry, tuple) and len(img_entry) >= 2 and img_entry[1]:
                            dest_name = str(img_entry[1])
                    dest_file = outdir_path / builder.imagedir / dest_name
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if not dest_file.is_file() or dest_file.stat().st_mtime < disk_found.stat().st_mtime:
                        shutil.copy2(disk_found, dest_file)
                    if hasattr(builder, "images") and isinstance(builder.images, dict):
                        builder.images.setdefault(src_rel, dest_name)
                    out_rel = f"{builder.imagedir}/{dest_name}".replace(os.sep, "/")
                    return out_rel, (str(disk_found) if is_svg else None)
                return src_rel, (str(disk_found) if is_svg else None)
        return clean_ref, (str(disk_found) if (disk_found is not None and is_svg) else None)

    if meta.get("featured_image"):
        uri, svg_disk = _resolve_asset_paths(str(meta["featured_image"]))
        return {
            "uri": uri,
            "alt": meta.get("featured_image_alt") or "",
            "svg_disk_path": svg_disk,
        }

    if doctree is None:
        return None

    if picture_node:
        for n in doctree.findall(picture_node):
            if "main_src" in n and n["main_src"]:
                uri, svg_disk = _resolve_asset_paths(str(n["main_src"]))
                return {
                    "uri": uri,
                    "alt": n.get("alt", ""),
                    "svg_disk_path": svg_disk,
                }

    for fig_n in doctree.findall(nodes.figure):
        image_node = next(iter(fig_n.findall(nodes.image)), None)
        if image_node and image_node.get("uri"):
            raw_uri = str(image_node["uri"])
            uri, svg_disk = _resolve_asset_paths(raw_uri)
            if not svg_disk and hasattr(builder, "imagedir") and not uri.startswith(f"{builder.imagedir}/"):
                uri = os.path.join(builder.imagedir, os.path.basename(raw_uri)).replace(os.sep, "/")
            return {
                "uri": uri,
                "alt": image_node.get("alt", ""),
                "width": fig_n.get("width"),
                "svg_disk_path": svg_disk,
            }

    # Check bare top-level image nodes (excluding folio initial drop-caps)
    for img_n in doctree.findall(nodes.image):
        if "folio-initial-cap" in img_n.get("classes", []):
            continue
        if img_n.get("uri"):
            raw_uri = str(img_n["uri"])
            uri, svg_disk = _resolve_asset_paths(raw_uri)
            return {
                "uri": uri,
                "alt": img_n.get("alt", ""),
                "svg_disk_path": svg_disk,
            }

    return None


def _resolve_representative_figure(
    env: Any,
    builder: Any,
    docname: str,
    meta: Optional[Dict[str, Any]] = None,
    item_doctree: Optional[nodes.document] = None,
    _visited: Optional[set] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve representative figure for `docname`, recursively bubbling from child units when `docname` is a container."""
    visited = _visited if _visited is not None else set()
    if docname in visited:
        return None
    visited.add(docname)

    resolved_meta = meta if meta is not None else dict(env.metadata.get(docname, {}))
    doctree = item_doctree
    if doctree is None:
        try:
            doctree = env.get_doctree(docname)
        except Exception:
            doctree = None

    # 1. Direct figure on docname
    direct = _extract_direct_figure(env, builder, docname, resolved_meta, doctree)
    if direct:
        return direct

    # 2. Companion reading track sibling in same unit directory
    try:
        from ..book import detect_companion_tracks

        for tr in detect_companion_tracks(env, docname):
            sib = tr.get("docname")
            if sib and sib != docname and sib not in visited:
                visited.add(sib)
                sib_meta = dict(env.metadata.get(sib, {}))
                try:
                    sib_dt = env.get_doctree(sib)
                except Exception:
                    sib_dt = None
                sib_fig = _extract_direct_figure(env, builder, sib, sib_meta, sib_dt)
                if sib_fig:
                    return sib_fig
    except Exception:
        pass

    # 3. Recursive container bubbling: if `docname` is a container (`.../index`), inspect ordered descendants
    if docname.endswith("/index") or docname == getattr(getattr(env, "config", None), "master_doc", "index"):
        prefix = "" if not docname.endswith("/index") else docname[:-5]  # includes trailing '/'
        candidates: List[Tuple[Tuple[Any, ...], str]] = []
        for cand in getattr(env, "found_docs", ()):
            if cand == docname or cand in visited:
                continue
            if prefix and not cand.startswith(prefix):
                continue
            rel_rest = cand[len(prefix) :]
            depth = rel_rest.count("/")
            cmeta = env.metadata.get(cand, {})
            ord_val = safe_numeric(
                cmeta.get("order", cmeta.get("number", cmeta.get("proposition", 999999))),
                999999,
            )
            # Prefer shallower direct children ordered by :order:/:number:, then deeper proposition units
            candidates.append(((depth, ord_val, cand), cand))

        candidates.sort(key=lambda pair: pair[0])
        for _sort_k, child_doc in candidates[:60]:
            if child_doc in visited:
                continue
            visited.add(child_doc)
            cmeta = dict(env.metadata.get(child_doc, {}))
            try:
                cdt = env.get_doctree(child_doc)
            except Exception:
                cdt = None
            cfig = _extract_direct_figure(env, builder, child_doc, cmeta, cdt)
            if cfig:
                return cfig

    return None


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

    if not item['excerpt_text'] and meta.get('excerpt'):
        item['excerpt_text'] = f"<p>{meta['excerpt']}</p>"

    fig_info = _resolve_representative_figure(env, app.builder, docname, meta, doctree)
    if fig_info:
        item['excerpt_figure_filename'] = fig_info['uri']
        item['excerpt_figure_alt'] = fig_info.get('alt') or item['title']
        if fig_info.get('width'):
            item['excerpt_figure_width'] = fig_info['width']
        if prepare_inline_svg and fig_info.get('svg_disk_path'):
            item['excerpt_svg_content'] = prepare_inline_svg(
                fig_info['svg_disk_path'], as_thumbnail=True
            )

    try:
        from ..book import detect_companion_tracks
        c_tracks = detect_companion_tracks(env, docname)
        if len(c_tracks) > 1:
            item['companion_tracks'] = c_tracks
    except Exception:
        pass
    return item


_ROMAN_VALUES = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
    'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
}


def _natural_taxonomy_sort_key(label: str) -> tuple:
    parts = label.lower().rsplit('-', 1)
    if len(parts) == 2:
        prefix, suffix = parts
        if suffix in _ROMAN_VALUES:
            return (prefix, 0, _ROMAN_VALUES[suffix], '')
        if suffix.isdigit():
            return (prefix, 0, int(suffix), '')
    return (label.lower(), 1, 0, label)


def _sort_taxonomy_articles(articles: List[Dict[str, Any]]) -> None:
    if any('order' in a or 'number' in a or 'proposition' in a for a in articles):
        articles.sort(
            key=lambda x: (
                safe_numeric(x.get('order', x.get('number', x.get('proposition', 999999))), 999999),
                safe_numeric(x.get('number', 999999), 999999),
                str(x.get('title', '')),
            )
        )
    elif any('date' in a for a in articles):
        articles.sort(key=lambda x: str(x.get('date', '')), reverse=True)
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
        meta = _normalize_log_meta(docname, env.metadata.setdefault(docname, {}))
        if 'tags' in meta:
            env.all_tags.update(_split_meta_list(meta['tags']))
        if 'categories' in meta:
            env.all_categories.update(_split_meta_list(meta['categories']))
        if 'category' in meta:
            env.all_categories.update(_split_meta_list(meta['category']))
        if 'type' in meta and meta['type']:
            env.all_types.add(str(meta['type']).strip())

    master_doc = getattr(getattr(app, 'config', None), 'master_doc', 'index')
    hdr, ftr = _scan_root_navigation_items(env.srcdir, master_doc)
    env._root_nav_signature = _nav_signature(hdr, ftr)


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
                    'label': tag,
                    'title': f"Posts tagged '{tag}'",
                    'articles': articles,
                    'sort_key': 'order',
                    'reverse': False,
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
                    'label': category,
                    'title': f"Posts in category '{category}'",
                    'articles': articles,
                    'sort_key': 'order',
                    'reverse': False,
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
                    'label': type_,
                    'title': f"Content of type '{type_}'",
                    'articles': articles,
                    'sort_key': 'order',
                    'reverse': False,
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

    context['tags'] = sorted(list(app.env.all_tags), key=_natural_taxonomy_sort_key) if hasattr(app.env, 'all_tags') else []
    context['categories'] = sorted(list(app.env.all_categories), key=_natural_taxonomy_sort_key) if hasattr(app.env, 'all_categories') else []
    context['types'] = sorted(list(app.env.all_types), key=_natural_taxonomy_sort_key) if hasattr(app.env, 'all_types') else []

    if 'meta' in context and context['meta']:
        _normalize_log_meta(pagename, context['meta'])
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
        meta = _normalize_log_meta(docname, app.env.metadata.setdefault(docname, {}))
        if meta.get('navigation') == 'header':
            title = app.env.titles.get(docname)
            nav_label = str(meta.get('nav_title') or '').strip() or (title.astext() if title else '')
            if nav_label:
                header_nav_list.append({
                    'docname': docname,
                    'title': nav_label,
                    'order': meta.get('order', 0),
                })
        if meta.get('navigation') == 'footer':
            title = app.env.titles.get(docname)
            nav_label = str(meta.get('nav_title') or '').strip() or (title.astext() if title else '')
            if nav_label:
                footer_nav_list.append({
                    'docname': docname,
                    'title': nav_label,
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

    header_nav_list.sort(key=lambda x: (safe_numeric(x['order']), x['docname']))
    context['header_nav_list'] = header_nav_list

    footer_nav_list.sort(key=lambda x: (safe_numeric(x['order']), x['docname']))
    context['footer_nav_list'] = footer_nav_list

    recent_logs.sort(key=lambda x: safe_sort_key(x['date']), reverse=True)
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



def _scan_root_navigation_items(srcdir: str, master_doc: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Scan srcdir for documents declaring :navigation: header or :navigation: footer."""
    header_docs: List[Dict[str, Any]] = []
    footer_docs: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(srcdir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        if '_static' in dirs:
            dirs.remove('_static')
        if '_templates' in dirs:
            dirs.remove('_templates')

        for filename in files:
            if filename.endswith('.rst'):
                path = os.path.join(root, filename)
                found_docname = os.path.splitext(os.path.relpath(path, srcdir))[0]
                if found_docname == master_doc:
                    continue

                meta = peek_metadata(path)
                nav = meta.get('navigation')
                if nav in ('header', 'footer'):
                    order_val = safe_numeric(meta.get('order', 999))
                    item = {
                        'docname': found_docname,
                        'order': order_val,
                        'nav_title': meta.get('nav_title', ''),
                    }
                    if nav == 'header':
                        header_docs.append(item)
                    else:
                        footer_docs.append(item)

    header_docs.sort(key=lambda x: (x['order'], x['docname']))
    footer_docs.sort(key=lambda x: (x['order'], x['docname']))
    return header_docs, footer_docs


def _nav_signature(header_docs: List[Dict[str, Any]], footer_docs: List[Dict[str, Any]]) -> tuple[Any, ...]:
    return tuple(
        ("h", d['docname'], d['order'], d['nav_title']) for d in header_docs
    ) + tuple(
        ("f", d['docname'], d['order'], d['nav_title']) for d in footer_docs
    )


def check_root_navigation_outdated(
    app: Any, env: Any, added: Any, changed: Any, removed: Any
) -> List[str]:
    """Mark master_doc outdated during incremental builds whenever header/footer navigation changes."""
    if getattr(getattr(app, "builder", None), "name", "") == "epub":
        return []
    master_doc = app.config.master_doc
    header_docs, footer_docs = _scan_root_navigation_items(env.srcdir, master_doc)
    sig = _nav_signature(header_docs, footer_docs)
    if getattr(env, '_root_nav_signature', None) != sig:
        if master_doc in env.found_docs:
            return [master_doc]
    return []


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
    header_docs, footer_docs = _scan_root_navigation_items(env.srcdir, docname)
    env._root_nav_signature = _nav_signature(header_docs, footer_docs)

    final_docnames = [x['docname'] for x in header_docs] + [x['docname'] for x in footer_docs]

    if final_docnames:
        toctree_rst = "\n\n.. toctree::\n   :hidden:\n\n"
        for d in final_docnames:
            toctree_rst += f"   {d}\n"

        source[0] += toctree_rst


class PeopleDirectoryDirective(CollectionDirective):
    """Directive to insert a searchable, sortable directory of people records."""

    def run(self) -> List[nodes.Node]:
        self.options.setdefault('sort', 'death_year')
        self.options.setdefault('template', 'collection/directory.html')
        self.options.setdefault('directory_kind', 'people')
        return super().run()


class ReferenceDirectoryDirective(CollectionDirective):
    """Directive to insert a searchable, sortable directory of reference/book records."""

    def run(self) -> List[nodes.Node]:
        self.options.setdefault('sort', 'year')
        self.options.setdefault('template', 'collection/directory.html')
        self.options.setdefault('directory_kind', 'references')
        return super().run()


class SourceDirectoryDirective(CollectionDirective):
    """Directive to insert a searchable, sortable directory of primary source witnesses."""

    def run(self) -> List[nodes.Node]:
        self.options.setdefault('sort', 'year')
        self.options.setdefault('template', 'collection/directory.html')
        self.options.setdefault('directory_kind', 'sources')
        return super().run()


def setup(app: Any) -> Dict[str, Any]:
    """Register directives and connect to Sphinx events.

    Args:
        app: The Sphinx application instance.

    Returns:
        A dictionary containing extension metadata.

    """
    app.add_node(PendingCollection)
    app.add_directive("collection", CollectionDirective)
    app.add_directive("people-directory", PeopleDirectoryDirective)
    app.add_directive("reference-directory", ReferenceDirectoryDirective)
    app.add_directive("source-directory", SourceDirectoryDirective)
    app.connect('env-get-outdated', check_root_navigation_outdated)
    app.connect('env-updated', collect_metadata)
    app.connect('html-collect-pages', generate_taxonomy_pages)
    app.connect('html-page-context', build_nav_links, priority=100)
    app.connect('source-read', inject_root_navigation)
    app.connect('doctree-resolved', process_collections)
    app.add_js_file('js/collection_controls.js')
    app.add_js_file('js/collection_directory.js')
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

