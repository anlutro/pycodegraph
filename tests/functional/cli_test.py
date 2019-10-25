import subprocess
import textwrap


def test_cli():
	out = subprocess.check_output(['pycodegraph', 'imports', '--depth=1'])
	assert out.decode().strip() == textwrap.dedent('''
	digraph {
	    "pycodegraph.analysis";
	    "pycodegraph.cli";
	    "pycodegraph.renderers";
	    "tests.unit";
	    "pycodegraph.cli" -> "pycodegraph.analysis";
	    "pycodegraph.renderers" -> "pycodegraph.analysis";
	    "tests.unit" -> "pycodegraph.analysis";
	    "tests.unit" -> "pycodegraph.renderers";
	}
	''').strip()
