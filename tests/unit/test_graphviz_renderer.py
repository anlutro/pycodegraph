import pycodegraph.renderers.graphviz


def render(imports):
	dot = pycodegraph.renderers.graphviz.render(imports)
	return dot.replace('    ', '\t').strip()


def test_render_with_no_imports():
	dot = render([])
	assert dot == '''
digraph {
}
	'''.strip()


def test_render_with_simple_imports():
	dot = render([('a', 'b'), ('a', 'c')])
	assert dot == '''
digraph {
	"a";
	"b";
	"c";
	"a" -> "b";
	"a" -> "c";
}
	'''.strip()
