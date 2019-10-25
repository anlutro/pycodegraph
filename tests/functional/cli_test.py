import subprocess


test_cli_expected = """
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
"""


def test_cli():
    out = subprocess.check_output(["pycodegraph", "imports", "--depth=1"])
    assert out.decode().strip() == test_cli_expected.strip()
