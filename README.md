# NEARC - NEAR Python Contract Compiler

NEARC is a specialized compiler that transforms Python smart contracts into WebAssembly bytecode for deployment on the NEAR blockchain. It allows developers to write smart contracts in Python rather than Rust or AssemblyScript, leveraging MicroPython as the underlying runtime.

## Features

- Write NEAR smart contracts in Python
- Use Python decorators (`@export`, `@view`, `@call`, etc.) to mark contract methods
- Automatic dependency detection and packaging
- Optimized WebAssembly output

## Prerequisites

- Python 3.11 or newer
- [Emscripten](https://emscripten.org/docs/getting_started/) (emcc must be in PATH)
- [uv](https://github.com/astral-sh/uv) for Python package management

## Getting Started

NEARC is designed to be used without installation via `uvx`:

```bash
# Use directly with uvx (recommended)
uvx nearc contract.py
```

Alternatively, you can install it globally:

```bash
# Add to global Python with uv
uv pip install nearc

# Or install from PyPI
pip install nearc
```

## Usage

```bash
# Basic usage
nearc contract.py

# Specify output file
nearc contract.py -o my-contract.wasm

# Use custom virtual environment
nearc contract.py --venv my-venv

# Force rebuild
nearc contract.py --rebuild
```

### Command Line Options

| Option           | Description                                                |
|------------------|------------------------------------------------------------|
| `--output`, `-o` | Output WASM filename (default: derived from contract name) |
| `--venv`         | Path to virtual environment (default: `.venv`)             |
| `--rebuild`      | Force rebuild of all components                            |

## Writing NEAR Contracts in Python

Here's a simple example of a NEAR smart contract written in Python:

```python
# counter.py
import near

@near.export
def get_count():
    return near.storage_read('count', 0)

@near.export
def increment():
    count = near.storage_write('count', 0)
    count += 1
    near.storage_read('count', count)
    return count
```

The compiler automatically detects functions with `@near.export` and similar decorators, making them available as contract methods in the compiled WebAssembly.

## How It Works

NEARC compiles Python smart contracts to WebAssembly through these steps:

1. **Code Analysis** - Identifies exported functions and dependencies in the Python code
2. **Manifest Generation** - Creates a MicroPython manifest file that includes all necessary modules
3. **Export Wrapping** - Generates C wrappers for exported functions
4. **WebAssembly Compilation** - Uses MicroPython and Emscripten to compile to WebAssembly
5. **Optimization** - Produces a compact WASM file ready for blockchain deployment

The compiler handles dependency resolution automatically, making it easy to use Python libraries in your contracts (as long as they're compatible with MicroPython).

## Development

If you want to contribute to NEARC or modify the source code:

```bash
# Clone the repository
git clone https://github.com/r-near/nearc
cd nearc

# Initialize submodules
git submodule update --init src/nearc/micropython
git -C src/nearc/micropython submodule update --init lib/micropython-lib

# Create virtual environment for development
uv init
uv pip install -e '.[dev]'
```

## Technical Details

### MicroPython Integration

NEARC uses a customized version of MicroPython as its runtime environment:

- Focused on minimal memory footprint and efficient execution
- Includes NEAR-specific host function bindings
- Provides a Python standard library subset optimized for smart contracts

### Support for External Dependencies

The compiler can include Python packages from your virtual environment:

- Automatically detects imports in your code
- Includes them in the compiled WebAssembly
- Warns about incompatible or missing dependencies

## Limitations

- Only supports MicroPython-compatible Python code
- Not all Python standard library modules are available
- No support for async/await syntax
- Limited compatibility with existing Python packages
- Contract size limitations (though generally sufficient for most use cases)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.