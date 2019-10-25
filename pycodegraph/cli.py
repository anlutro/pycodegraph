#!/usr/bin/env python

from __future__ import print_function
import argparse
import importlib
import logging
import os

import allib.logging

log = logging.getLogger(__name__)


class Entrypoint(object):
    def __init__(self, parser=None):
        self.parser = parser or argparse.ArgumentParser()
        self.add_argument = self.parser.add_argument
        self.parse_args = self.parser.parse_args
        self.add_argument(
            "path",
            type=str,
            nargs="?",
            default=os.getcwd(),
            help="path to your Python code. defaults to pwd",
        )
        self.add_argument("-v", "--verbose", action="store_true")
        self.add_argument("-vv", "--very-verbose", action="store_true")

    def run(self, args):
        raise NotImplementedError("Entrypoint must implement run method")


class ImportsEntrypoint(Entrypoint):
    def __init__(self, parser=None):
        super(ImportsEntrypoint, self).__init__(parser=parser)
        self.add_argument(
            "-c",
            "--clusters",
            action="store_true",
            help="draw boxes around top-level modules",
        )
        self.add_argument(
            "-d",
            "--depth",
            type=int,
            default=0,
            help="inspect submodules as well as top-level modules",
        )
        self.add_argument(
            "-i",
            "--include",
            type=str,
            nargs="*",
            help="specify external modules that should be included in the graph, "
            "if they are imported",
        )
        self.add_argument(
            "-x",
            "--exclude",
            type=str,
            nargs="*",
            help="patterns of directories/submodules that should not be graphed. "
            "useful for tests, for example",
        )

    def run(self, args):
        from pycodegraph.analysis.imports import find_imports

        include = args.include or []
        exclude = args.exclude or []

        imports = find_imports(
            args.path, depth=args.depth, include=include, exclude=exclude
        )
        log.info("found total of %d imports in %r", len(imports), args.path)
        if not imports:
            log.warning("found no imports - try increasing depth!")

        # this can be changed to an arg later on, when we support multiple renderers
        renderer = "graphviz"

        renderer_module = importlib.import_module("pycodegraph.renderers.%s" % renderer)
        print(renderer_module.render(imports))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    commands = {"imports": ImportsEntrypoint}
    for command in commands:
        subparser = subparsers.add_parser(command)
        commands[command] = commands[command](parser=subparser)
    args = parser.parse_args()

    level = logging.WARNING
    if args.very_verbose:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    allib.logging.setup_logging(log_level=level, colors=True)

    if args.command:
        commands[args.command].run(args)
    else:
        parser.print_help()
