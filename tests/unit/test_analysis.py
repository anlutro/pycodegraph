from pycodegraph.analysis import *


def test_find_root_module():
	root = find_root_module(__file__)
	assert root == 'tests.unit.test_analysis'
