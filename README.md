Minimal build/deploy tool for Python NEAR smart contracts
=========================================================

This is a work-in-progress build/deploy tool for Python NEAR smart contracts.

Python source files are compiled into the WASM binary via [MicroPython](https://github.com/micropython/micropython) and [Emscripten](https://emscripten.org/docs/getting_started/downloads.html) and then deployed via `near-cli-rs` tool.

`near-py-tool` CLI is modelled after [cargo-near](https://github.com/near/cargo-near) with most of the 
command-line options compatible (not all are implemented yet).


Dependencies
------------

`near-py-tool` expects the following dependencies installed:
- Python>=3.9
- essential build tools like `make` and C compiler
- [Emscripten](https://emscripten.org/docs/getting_started/downloads.html) for compiling Python into WASM via MicroPython
- [near-cli-rs](https://github.com/near/near-cli-rs) for NEAR Protocol interactions


Platform support
----------------

Currenly Linux (including WSL) and MacOS are supported with more platforms planned for the future.


Python library support
----------------------

Most of the MicroPython standard library is included and should be functional where applicable to WASM runtime environment.

External Python package are supported as long as they don't require native compiled code to work. `near-py-tool` will download any packages referenced
via `pyproject.toml` and will try to compile them into the WASM binary alongside the main `contract.py` file.


NEAR ABI support
----------------

Currenly a minimal version of NEAR WASM ABI is implemented via `near` module:

- `near.input(index)` retrieves the specified contract input as `bytes`
- `near.value_return(value)` returns a value (`str` or `bytes`) from the contract
- `near.log_utf8(message)` logs a message (`str`)

Contract methods to be exported from the WASM binary should be decorated with `@near.export`.

See the `near-py-tool new`-generated project for more details.


Getting started
---------------

- install `near-py-tool` via `pip install near-py-tool`
- run `near-py-tool new test-project` to create a minimal Python smart contract project
- `cd ./test-project`
- run `near-py-tool build` to produce a standalone WASM file
- run `near-py-tool create-dev-account` to create a testnet account if you don't have one already
- run `near-py-tool deploy` to deploy the smart contract


TODO
----

- Proper Python exception support (currently any thrown exception will log the exception message and terminate the contract execution)
- Tests and CI
- NEAR ABI metadata generation
- More platform support & automatic dependency installation