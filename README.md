# NEARC - NEAR Python Contract Compiler

A simple compiler that converts Python contracts to WebAssembly for deployment on NEAR.

## Usage

```
uvx nearc contract.py [OPTIONS]
```

### Options

- \`--output\`, \`-o\`: Output WASM filename [default: derived from contract name]
- \`--venv\`: Path to virtual environment [default: .venv]
- \`--rebuild\`: Force rebuild of all components

## Requirements

- Python 3.11+
- Emscripten (emcc must be in PATH)
- uv for managing virtual environments

## Development

```console
Development:
```
git clone https://github.com/r-near/nearc
cd nearc
git submodule update --init src/nearc/micropython
git -C src/nearc/micropython submodule update --init lib/micropython-lib
```
