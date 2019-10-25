# pycodegraph - Python code graphing tool

A tool/framework for analysing and graphing Python code.

Currently only supports graphing of imports, but hopefully more to come.

## Installing

Install via pip (preferably into your project's virtualenv):

	pip install pycodegraph

## Usage

Create a dot graph of your code and render it using dot:

	pycodegraph imports --depth=1 ./my_code | dot -Tsvg > mygraph.svg

Usually you'll want to adjust the depth depending on project size and/or number of submodules.

There is also `--include` and `--exclude` for more fine grained control over what gets included in the graph.

## License

[MIT license](https://opensource.org/licenses/MIT). See [LICENSE](LICENSE) for full text.
