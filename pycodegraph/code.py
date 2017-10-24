#!/usr/bin/env python

from fnmatch import fnmatch
import ast
import logging
import os
import os.path

log = logging.getLogger()


def find_root_module(path):
	"""
	Given a path, very naively try to guess what python package (aka root
	module) it corresponds to.
	"""
	path = os.path.abspath(path)
	if os.path.isfile(path):
		path = os.path.splitext(path)[0]
	module_parts = []
	while path != '/':
		def exists(filename):
			return os.path.exists(os.path.join(path, filename))
		if exists('setup.py') or exists('setup.cfg'):
			break
		module_parts.append(os.path.basename(path))
		path = os.path.dirname(path)
	return '.'.join(reversed(module_parts))


def find_module_files(root_path, exclude):
	"""
	Given a path, find all python files in that path and guess their module
	names. Generates tuples of (module, path).
	"""
	def dir_excluded(path):
		return path in exclude or path.startswith('.')

	root_module = find_root_module(root_path)
	log.debug('resolved path %r to root_module %r', root_path, root_module)

	for root, dirs, files in os.walk(root_path):
		# prevents os.walk from recursing excluded directories
		dirs[:] = [d for d in dirs if not dir_excluded(d)]
		for file in files:
			path = os.path.join(root, file)
			relpath = os.path.relpath(path, root_path)
			if file.endswith('.py'):
				module = relpath.replace('.py', '').replace('/', '.')
				module = module.replace('.__init__', '')
				if module == '__init__':
					if root_module:
						module = root_module
					else:
						log.warning('could not guess module of %r', relpath)
						continue
				elif root_module:
					module = '%s.%s' % (root_module, module)
				log.debug('resolved %r to %r', relpath, module)
				yield module, path


def find_imports_in_file(path, root_module=None):
	"""
	Parse a python file, finding all imports.
	"""
	with open(path) as filehandle:
		return find_imports_in_code(
			filehandle.read(),
			path=path,
			root_module=root_module,
		)


def find_root_module_path(path, root_module):
	orig_path = path
	root_end_part = root_module.replace('.', '/')
	while not path.endswith('/' + root_end_part):
		path = os.path.dirname(path)
		if path == '/':
			raise ValueError('could not find root module %r path based on %r' % (root_module, orig_path))
	return path


def resolve_relative_module(module, level, path, root_module=None, root_path=None):
	path = os.path.abspath(path)
	if root_path is None:
		root_path = path
		while not root_path.endswith('/' + root_module):
			root_path = os.path.dirname(root_path)
			if root_path == '/':
				raise ValueError('could not find root path for %s from %r' % (
					root_module, path))
		# we need to get the parent directory of the root module directory for
		# relpath to include the full module "path"
		root_path = os.path.dirname(root_path)

	importing_from_dir = os.path.dirname(path)
	importing_from_path = os.path.relpath(importing_from_dir, root_path)
	importing_from_module = importing_from_path.replace('.py', '').replace('/', '.')

	# copied from python stdlib
	bits = importing_from_module.rsplit('.', level - 1)
	if len(bits) < level:
		raise ValueError('attempted relative import beyond top-level package')
	base = bits[0]
	return '{}.{}'.format(base, module) if module else base


def find_imports_in_code(code, path=None, root_module=None):
	"""
	Parse some Python code, finding all imports.
	"""
	try:
		tree = ast.parse(code)
	except SyntaxError:
		log.exception('SyntaxError in %r', (path or 'code'))
		return

	for node in ast.walk(tree):
		# note that there's no way for us to know if from x import y imports a
		# variable or submodule from x, so that will need to be figured out
		# later on in this script
		if isinstance(node, ast.ImportFrom):
			module = node.module

			# relative imports
			if node.level > 0:
				module = ('.' * node.level) + (module if module else '')
				if path and root_module:
					module = resolve_relative_module(
						module,
						node.level,
						path,
						root_module=root_module,
					)

			for name in node.names:
				if name.name == '*':
					yield module
				else:
					yield '%s.%s' % (module, name.name)
		elif isinstance(node, ast.Import):
			for name in node.names:
				yield name.name


def shorten_module(module, depth):
	return '.'.join(module.split('.')[:depth+1])


def module_matches(module, searches, allow_fnmatch=False):
	"""
	Check if a module matches some search terms.
	"""
	for search in searches:
		if module == search or module.startswith(search + '.'):
			return True
		if allow_fnmatch and fnmatch(module, search):
			return True
	return False


def module_exists_on_filesystem(module, path, root_module=None):
	"""
	Given a module name and a path to start from, check if there is a file on
	the filesystem which corresponds to this module.
	"""

	# if there is a root module set, we need to traverse up the directory tree
	if root_module:
		dotdots = ['..'] * (root_module.count('.') + 1)
		path = os.path.join(path, *dotdots)

	module_path = os.path.join(path, module.replace('.', '/'))

	return os.path.isfile(module_path + '.py') or (
		os.path.isdir(module_path) and
		os.path.isfile(os.path.join(module_path, '__init__.py'))
	)


def find_imports(path, depth=0, include=None, exclude=None):
	"""
	Find all interesting imports in all python files in a directory.

	Args:
	  path (str): Path to the directory of code.
	  depth (int): Number of submodules to traverse into.
	  include (seq): Additional modules that you want to track imports of.
	  exclude (seq): Names of submodules to exclude from the results.
	"""
	if exclude is None:
		exclude = []

	root_module = find_root_module(path)
	module_files = list(find_module_files(path, exclude=exclude))
	log.info('found %d module files', len(module_files))

	imports_to_search_for = set(
		shorten_module(module, depth) for module, path in module_files
	)
	if include:
		imports_to_search_for.update(include)
	log.info('imports_to_search_for: %r', sorted(imports_to_search_for))

	imports = set()

	def analyze_import(module, module_import):
		"""
		Analyze a single import and add it to the "imports" set if it is
		relevant to what the user asked for.
		"""
		module_import = shorten_module(module_import, depth)
		if module == module_import:
			log.debug('skipping self-importing module %r', module)
			return

		if not module_matches(module_import, imports_to_search_for, allow_fnmatch=True):
			log.debug('skipping import %r, it is not in imports_to_search_for', module_import)
			return

		include_match = module_matches(module_import, include)
		module_import_path = module_exists_on_filesystem(module_import, path, root_module)

		# because with imports like `from a.b import c` there's no way for
		# us to know if c is a function or a submodule, we have to check for
		# both the module itself as well as its parent
		if not module_import_path:
			parent_module_import = '.'.join(module_import.split('.')[:-1])
			module_import_path = module_exists_on_filesystem(
				parent_module_import, path, root_module
			)
			if module_import_path:
				module_import = parent_module_import

		if module_import_path or include_match:
			log.debug('adding %r -> %r (module_import_path=%r, include_match=%r)',
				module, module_import, module_import_path, include_match)
			imports.add((module, module_import))
		else:
			log.debug('skipping %r -> %r (module_import_path=%r, include_match=%r)',
				module, module_import, module_import_path, include_match)

	def analyze_file(module, module_path):
		"""
		Scan a file for imports and add the relevant ones to the "imports" set.
		"""
		module_parts = module.split('.')
		module_path_parts = module_path.split('/')
		if exclude and (
			any(e in module_parts for e in exclude)
			or any(e in module_path_parts for e in exclude)
		):
			log.debug('skipping module because it is in exclude: %r (%s)',
				module_path, module)
			return

		shortened_module = shorten_module(module, depth)
		module_imports = list(find_imports_in_file(module_path, root_module))
		log.debug('found %d imports in %r (shortened_module=%r)',
			len(module_imports), module_path, shortened_module)

		for module_import in module_imports:
			analyze_import(shortened_module, module_import)

	for module, module_path in module_files:
		analyze_file(module, module_path)

	return imports
