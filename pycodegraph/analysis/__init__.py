import os.path
import logging

log = logging.getLogger(__name__)


def shorten_module(module, depth):
    return ".".join(module.split(".")[: depth + 1])


def find_root_module(path):
    """
	Given a path, very naively try to guess what python package (aka root
	module) it corresponds to.
	"""
    path = os.path.abspath(path)

    def exists(filename):
        return os.path.exists(os.path.join(path, filename))

    if os.path.isfile(path):
        path = os.path.splitext(path)[0]
    module_parts = []
    while path != "/":
        if exists("setup.py") or exists("setup.cfg"):
            break
        module_parts.append(os.path.basename(path))
        path = os.path.dirname(path)
    if path == "/":
        return None

    if not module_parts:
        return None

    # ideally we should be checking if this is defined in setup.py,
    # but for now this is okay I think
    if module_parts[-1] == "src":
        module_parts = module_parts[:-1]
    return ".".join(reversed(module_parts))


def find_root_module_path(path, root_module):
    path = os.path.abspath(path)
    orig_path = path
    root_end_part = root_module.replace(".", "/")
    while not path.endswith("/" + root_end_part):
        path = os.path.dirname(path)
        if path == "/":
            msg = "could not find root module %r path based on %r" % (
                root_module,
                orig_path,
            )
            raise ValueError(msg)
    return os.path.dirname(path)


def find_module_files(root_path, exclude=None, filter=None, root_module=None):
    """
	Given a path, find all python files in that path and guess their module
	names. Generates tuples of (module, path).
	"""
    exclude = set(exclude or [])
    filter = set(filter) if filter else None

    if root_module is None:
        root_module = find_root_module(root_path)
        log.debug("resolved path %r to root_module %r", root_path, root_module)

    def dir_excluded(path):
        if path.startswith("."):
            return True
        if path in exclude:
            return True
        if filter is not None:
            return path not in filter
        return False

    for root, dirs, files in os.walk(root_path):
        # prevents os.walk from recursing excluded directories
        dirs[:] = [d for d in dirs if not dir_excluded(d)]
        for file in files:
            path = os.path.join(root, file)
            relpath = os.path.relpath(path, root_path)
            if file.endswith(".py"):
                module = relpath.replace(".py", "").replace("/", ".")
                module = module.replace(".__init__", "")
                if module == "__init__":
                    if root_module:
                        module = root_module
                    else:
                        log.warning("could not guess module of %r", relpath)
                        continue
                elif root_module:
                    module = "%s.%s" % (root_module, module)
                log.debug("resolved %r to %r", relpath, module)
                yield module, path
