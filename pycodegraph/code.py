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


def find_module_files(root_path, exclude, root_module=None):
	"""
	Given a path, find all python files in that path and guess their module
	names. Generates tuples of (module, path).
	"""
	if root_module is None:
		root_module = find_root_module(root_path)
		log.debug('resolved path %r to root_module %r', root_path, root_module)

	def dir_excluded(path):
		return path in exclude or path.startswith('.')

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


def find_imports_in_file(path, root_path=None):
	"""
	Parse a python file, finding all imports.
	"""
	with open(path) as filehandle:
		return find_imports_in_code(
			filehandle.read(),
			path=path,
			root_path=root_path,
		)


def resolve_relative_module(path, module, root_path, level=None):
	path = os.path.abspath(path)

	src_dir = os.path.dirname(path)
	src_path = os.path.relpath(src_dir, root_path)
	src_module = src_path.replace('.py', '').replace('/', '.')

	if level is None:
		level = 0
		for character in module:
			if character != '.':
				break
			level += 1
		module = module[level:]

	bits = src_module.rsplit('.', level - 1)
	if len(bits) < level:
		raise ValueError('attempted relative import beyond top-level package')
	base = bits[0]
	return '{}.{}'.format(base, module) if module else base


def find_imports_in_code(code, path=None, root_path=None):
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
				if path and root_path:
					module = resolve_relative_module(
						path=path,
						module=module,
						root_path=root_path,
						level=node.level,
					)
				else:
					module = ('.' * node.level) + (module if module else '')

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


def module_exists_on_filesystem(module, path):
	"""
	Given a module name and a path to start from, check if there is a file on
	the filesystem which corresponds to this module.
	"""
	module_path = os.path.join(path, module.replace('.', '/'))
	log.debug('module_path=%r', module_path)

	return os.path.isfile(module_path + '.py') or (
		os.path.isdir(module_path) and
		os.path.isfile(os.path.join(module_path, '__init__.py'))
	)


def find_root_module_path(path, root_module):
	path = os.path.abspath(path)
	orig_path = path
	root_end_part = root_module.replace('.', '/')
	while not path.endswith('/' + root_end_part):
		path = os.path.dirname(path)
		if path == '/':
			msg = 'could not find root module %r path based on %r' % (
				root_module, orig_path
			)
			raise ValueError(msg)
	return os.path.dirname(path)


class ImportAnalysis():
	def __init__(self, path, depth=0, include=None, exclude=None):
		self.path = path
		self.depth = depth
		self.include = include
		self.exclude = exclude

		self.root_module = find_root_module(path)
		log.info('guessed root module to be %r', self.root_module)
		self.root_path = find_root_module_path(path, self.root_module)
		log.info('guessed root path to be %r', self.root_path)

		self.module_files = list(find_module_files(
			self.path, exclude=self.exclude, root_module=self.root_module
		))
		log.info('found %d module files', len(self.module_files))

		self.search = set(
			shorten_module(module, self.depth)
			for module, path in self.module_files
		)
		log.info(
			'imports to search for: %r + %r',
			sorted(self.search),
			sorted(self.include),
		)

	def module_exists(self, module):
		return module_exists_on_filesystem(module, self.root_path)

	def find_module(self, module):
		if self.module_exists(module):
			return module

		# because with imports like `from a.b import c` there's no way for
		# us to know if c is a function or a submodule, we have to check for
		# both the module itself as well as its parent
		parent = '.'.join(module.split('.')[:-1])
		if self.module_exists(parent):
			return parent

		return False

	def find_imports_in_file(self, module, module_path):
		"""
		Scan a file for imports and add the relevant ones to the "imports" set.
		"""
		module_parts = module.split('.')
		module_path_parts = module_path.split('/')
		if self.exclude and (
			any(e in module_parts for e in self.exclude)
			or any(e in module_path_parts for e in self.exclude)
		):
			log.debug('skipping module because it is in exclude: %r (%s)',
				module_path, module)
			return []

		short_module = shorten_module(module, self.depth)

		module_imports = list(find_imports_in_file(module_path, self.root_path))
		log.debug('found %d imports in %r', len(module_imports), module_path)

		imports = set()

		for module_import in module_imports:
			short_import = shorten_module(module_import, self.depth)

			if short_module == short_import:
				log.debug('skipping self-import %r -> %r', module, module_import)
				continue

			is_in_include = module_matches(
				module_import, self.include, allow_fnmatch=True
			)
			is_in_search = module_matches(
				module_import, self.search
			)

			if not is_in_include and not is_in_search:
				log.debug('skipping import %r, it is not in include or search',
					module_import)
				continue

			if not is_in_include:
				short_import = self.find_module(short_import)
				if not short_import:
					log.debug('skipping import %r, could not find it on the filesystem',
						module_import)
					continue

			imports.add((short_module, short_import))

		return imports

	def find_imports(self):
		imports = set()

		for module, module_path in self.module_files:
			imports.update(
				self.find_imports_in_file(module, module_path)
			)

		return imports


def find_imports(path, depth=0, include=None, exclude=None):
	analysis = ImportAnalysis(
		path, depth=depth, include=include, exclude=exclude
	)
	return analysis.find_imports()
