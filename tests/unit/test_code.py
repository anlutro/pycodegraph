import pytest
import os.path
from pycodegraph.code import *


def test_find_root_module():
	root = find_root_module(__file__)
	assert root == 'tests.unit.test_code'


def test_find_imports():
	code = 'import abc'
	imports = list(find_imports_in_code(code))
	assert imports == ['abc']


def test_shorten_module():
	assert 'foo' == shorten_module('foo.bar', 0)
	assert 'foo' == shorten_module('foo.bar.baz', 0)
	assert 'foo' == shorten_module('foo.bar.baz.foo', 0)
	assert 'foo.bar' == shorten_module('foo.bar', 1)
	assert 'foo.bar' == shorten_module('foo.bar.baz', 1)
	assert 'foo.bar' == shorten_module('foo.bar.baz.foo', 1)
	assert 'foo.bar' == shorten_module('foo.bar', 2)
	assert 'foo.bar.baz' == shorten_module('foo.bar.baz', 2)
	assert 'foo.bar.baz' == shorten_module('foo.bar.baz.foo', 2)


def test_module_exists_on_filesystem():
	path = os.path.dirname(__file__)
	assert module_exists_on_filesystem('test_code', path)
	assert not module_exists_on_filesystem('unit.test_code', path)
	assert not module_exists_on_filesystem('tests.unit.test_code', path)

	path = os.path.dirname(path)
	assert not module_exists_on_filesystem('test_code', path)
	assert module_exists_on_filesystem('unit.test_code', path)
	assert not module_exists_on_filesystem('tests.unit.test_code', path)

	path = os.path.dirname(path)
	assert not module_exists_on_filesystem('test_code', path)
	assert not module_exists_on_filesystem('unit.test_code', path)
	assert module_exists_on_filesystem('tests.unit.test_code', path)


@pytest.mark.parametrize('path, mod, root, expect', [
	('/path/to/foo/bar/baz.py', '..bar', '/path/to', 'foo.bar'),
	('/path/to/foo/bar/baz.py', '..baz', '/path/to', 'foo.baz'),
	('/path/to/foo/bar/baz.py', '..baz.bar', '/path/to', 'foo.baz.bar'),
	('/path/to/foo/bar/baz.py', '.bar', '/path/to', 'foo.bar.bar'),
	('/path/to/foo/bar/baz.py', '.', '/path/to', 'foo.bar'),
])
def test_resolve_relative_module(path, mod, root, expect):
	assert resolve_relative_module(path, mod, root) == expect


@pytest.mark.parametrize('path, mod, root, level, expect', [
	('/path/to/foo/bar/baz.py', 'bar', '/path/to', 2, 'foo.bar'),
	('/path/to/foo/bar/baz.py', 'baz', '/path/to', 2, 'foo.baz'),
	('/path/to/foo/bar/baz.py', 'baz.bar', '/path/to', 2, 'foo.baz.bar'),
	('/path/to/foo/bar/baz.py', 'bar', '/path/to', 1, 'foo.bar.bar'),
	('/path/to/foo/bar/baz.py', '', '/path/to', 1, 'foo.bar'),
])
def test_resolve_relative_module_with_level(path, mod, root, level, expect):
	assert resolve_relative_module(path, mod, root, level=level) == expect


def test_resolve_relative_with_too_many_dots():
	with pytest.raises(ValueError):
		resolve_relative_module('/path/to/foo/bar.py', '...foo', '/path/to')
	with pytest.raises(ValueError):
		resolve_relative_module('/path/to/foo/bar.py', 'foo', '/path/to', 3)
