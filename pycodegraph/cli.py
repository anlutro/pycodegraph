#!/usr/bin/env python

from __future__ import print_function
import argparse
import importlib
import logging
import os

import allib.logging

from pycodegraph.analysis.imports import find_imports

log = logging.getLogger()


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('path', type=str, nargs='?', default=os.getcwd(),
		help='path to your Python code. defaults to pwd')
	parser.add_argument('-c', '--clusters', action='store_true',
		help='draw boxes around top-level modules')
	parser.add_argument('-d', '--depth', type=int, default=0,
		help='inspect submodules as well as top-level modules')
	parser.add_argument('-i', '--include', type=str, nargs='*',
		help='specify external modules that should be included in the graph, '
			 'if they are imported')
	parser.add_argument('-x', '--exclude', type=str, nargs='*',
		help='patterns of directories/submodules that should not be graphed. '
			  'useful for tests, for example')
	parser.add_argument('-v', '--verbose', action='store_true')
	parser.add_argument('-vv', '--very-verbose', action='store_true')
	args = parser.parse_args()

	level = logging.WARNING
	if args.very_verbose:
		level = logging.DEBUG
	elif args.verbose:
		level = logging.INFO

	allib.logging.setup_logging(log_level=level, colors=True)

	include = args.include or []
	exclude = args.exclude or []

	imports = find_imports(
		args.path,
		depth=args.depth,
		include=include,
		exclude=exclude,
	)
	log.info('found total of %d imports in %r', len(imports), args.path)
	if not imports:
		log.warning('found no imports - try increasing depth!')

	# this can be changed to an arg later on, when we support multiple renderers
	renderer = 'graphviz'

	renderer_module = importlib.import_module('pycodegraph.renderers.%s' % renderer)
	print(renderer_module.render(imports))


if __name__ == '__main__':
	main()
