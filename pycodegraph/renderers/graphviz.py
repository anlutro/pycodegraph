from collections import defaultdict
from pycodegraph.analysis import shorten_module


def get_all_modules(imports):
    all_modules = set()
    for src_module, target_module in imports:
        all_modules.add(src_module)
        all_modules.add(target_module)
    return all_modules


def locate_clusters(imports, depth=0):
    all_modules = get_all_modules(imports)
    clusters = defaultdict(lambda: set())
    for module in all_modules:
        clusters[shorten_module(module, depth)].add(module)
    return clusters.items()


def render_nodes(nodes, indent=4, shape=None):
    if shape:
        attrs = " [shape=%s]" % shape
    else:
        attrs = ""
    return sorted([(" " * indent + '"%s"%s;' % (node, attrs)) for node in nodes])


def render_subgraph(name, nodes, indent=4):
    lines = [" " * indent + "subgraph cluster_%s {" % name]
    lines.extend(render_nodes(nodes, indent + 4))
    lines.append(" " * indent + "}")
    return lines


def render(imports, font=None, rankdir=None, clusters=False):
    lines = ["digraph {"]
    if font:
        lines.extend(
            [
                '    graph [fontname = "%s"];' % font,
                '    node [fontname = "%s"];' % font,
                '    edge [fontname = "%s"];' % font,
            ]
        )
    if rankdir:
        lines.append("    rankdir=%s;" % rankdir)
    if len(lines) > 1:
        lines.append("")

    if clusters:
        for cluster, nodes in locate_clusters(imports):
            if len(nodes) > 2:
                lines.extend(render_subgraph(cluster, nodes, indent=4))
            else:
                lines.extend(render_nodes(nodes, indent=4))
    else:
        all_modules = get_all_modules(imports)
        lines.extend(render_nodes(all_modules, indent=4))

    for src_module, target_module in sorted(imports):
        lines.append('    "%s" -> "%s";' % (src_module, target_module))

    lines.append("}")
    return "\n".join(lines)
