from fnmatch import fnmatch
import ast
import logging
import os
import os.path

from . import find_root_module, find_root_module_path, find_module_files, shorten_module

log = logging.getLogger(__name__)


def find_imports_in_file(path, root_path=None):
    """
	Parse a python file, finding all imports.
	"""
    with open(path) as filehandle:
        return find_imports_in_code(filehandle.read(), path=path, root_path=root_path)


def resolve_relative_module(path, module, root_path, level=None):
    path = os.path.abspath(path)

    src_dir = os.path.dirname(path)
    src_path = os.path.relpath(src_dir, root_path)
    src_module = src_path.replace(".py", "").replace("/", ".")

    if level is None:
        level = 0
        for character in module:
            if character != ".":
                break
            level += 1
        module = module[level:]

    bits = src_module.rsplit(".", level - 1)
    if len(bits) < level:
        raise ValueError("attempted relative import beyond top-level package")
    base = bits[0]
    return "{}.{}".format(base, module) if module else base


def find_imports_in_code(code, path=None, root_path=None):
    """
	Parse some Python code, finding all imports.
	"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        log.exception("SyntaxError in %r", (path or "code"))
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
                        path=path, module=module, root_path=root_path, level=node.level
                    )
                else:
                    module = ("." * node.level) + (module if module else "")

            for name in node.names:
                if name.name == "*":
                    yield module
                else:
                    yield "%s.%s" % (module, name.name)
        elif isinstance(node, ast.Import):
            for name in node.names:
                yield name.name


def module_matches(module, searches, allow_fnmatch=False):
    """
	Check if a module matches some search terms.
	"""
    for search in searches:
        if module == search or module.startswith(search + "."):
            return True
        if allow_fnmatch and fnmatch(module, search):
            return True
    return False


def module_exists_on_filesystem(module, path):
    """
	Given a module name and a path to start from, check if there is a file on
	the filesystem which corresponds to this module.
	"""
    module_path = os.path.join(path, module.replace(".", "/"))

    return os.path.isfile(module_path + ".py") or (
        os.path.isdir(module_path)
        and os.path.isfile(os.path.join(module_path, "__init__.py"))
    )


class ImportAnalysis:
    def __init__(self, path, depth=0, include=None, exclude=None, filter=None):
        self.path = path
        self.depth = depth
        self.include = include
        self.exclude = exclude
        self.filter = filter

        self.root_module = find_root_module(path)
        if self.root_module:
            log.info("guessed root module to be %r", self.root_module)
            self.root_path = find_root_module_path(path, self.root_module)
            log.info("guessed root path to be %r", self.root_path)

            self.depth += self.root_module.count(".") + 1
            log.debug("depth=%d after finding root module", self.depth)
        else:
            log.info("no root module found, analyzing all modules in PWD")
            self.root_path = path

        self.module_files = list(
            find_module_files(
                self.path,
                exclude=self.exclude,
                filter=self.filter,
                root_module=self.root_module,
            )
        )
        log.info("found %d module files", len(self.module_files))

        self.search = set(
            shorten_module(module, self.depth) for module, path in self.module_files
        )
        log.info(
            "imports to search for: %r + %r", sorted(self.search), sorted(self.include)
        )

    def module_exists(self, module):
        return module_exists_on_filesystem(module, self.root_path)

    def find_module(self, module):
        if self.module_exists(module):
            return module

        # because with imports like `from a.b import c` there's no way for
        # us to know if c is a function or a submodule, we have to check for
        # both the module itself as well as its parent
        parent = ".".join(module.split(".")[:-1])
        if self.module_exists(parent):
            return parent

        return False

    def _is_module_excluded(self, module, path=None):
        if not self.exclude:
            return False

        if module in self.exclude:
            return True

        if any(e in module.split(".") for e in self.exclude):
            return True

        if path and any(e in path.split("/") for e in self.exclude):
            return True

        if self.filter is not None:
            return not (
                any(e in path.split("/") for e in self.filter)
                and any(e in module.split(".") for e in self.filter)
            )

        return False

    def find_imports_in_file(self, module, module_path):
        """
		Scan a file for imports and add the relevant ones to the "imports" set.
		"""
        if self._is_module_excluded(module, module_path):
            log.debug(
                "skipping module because it is in exclude: %r (%s)", module_path, module
            )
            return []

        short_module = shorten_module(module, self.depth)

        module_imports = list(find_imports_in_file(module_path, self.root_path))
        log.debug("found %d imports in %r", len(module_imports), module_path)

        imports = set()

        for module_import in module_imports:
            if self._is_module_excluded(module_import):
                log.debug(
                    "skipping module import of %s because it is in exclude",
                    module_import,
                )
                continue

            short_import = shorten_module(module_import, self.depth)

            if short_module == short_import:
                log.debug("skipping self-import %r -> %r", module, module_import)
                continue

            is_in_include = module_matches(
                module_import, self.include, allow_fnmatch=True
            )
            is_in_search = module_matches(module_import, self.search)

            if not is_in_include and not is_in_search:
                log.debug(
                    "skipping import %r, it is not in include or search", module_import
                )
                continue

            if not is_in_include:
                short_import = self.find_module(short_import)
                if not short_import:
                    log.debug(
                        "skipping import %r, could not find it on the filesystem",
                        module_import,
                    )
                    continue

            imports.add((short_module, short_import))

        return imports

    def find_imports(self):
        imports = set()

        for module, module_path in self.module_files:
            imports.update(self.find_imports_in_file(module, module_path))

        return imports


def find_imports(*args, **kwargs):
    analysis = ImportAnalysis(*args, **kwargs)
    return analysis.find_imports()
