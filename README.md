# NEARC - NEAR Python Contract Compiler

NEARC is a specialized compiler that transforms Python smart contracts into WebAssembly bytecode for deployment on the NEAR blockchain. It allows developers to write smart contracts in Python rather than Rust or AssemblyScript, leveraging MicroPython as the underlying runtime.

## Features

- Write NEAR smart contracts in Python
- Use Python decorators (`@export`, `@view`, `@call`, etc.) to mark contract methods
- Automatic dependency detection and packaging
- Optimized WebAssembly output
- Automatic NEP-330 contract metadata compliance

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
    count = near.storage_read('count', 0)
    count += 1
    near.storage_write('count', count)
    return count
```

The compiler automatically detects functions with `@near.export` and similar decorators, making them available as contract methods in the compiled WebAssembly.

## Contract Metadata (NEP-330)

NEARC automatically adds NEP-330 compliant metadata to your contracts. You can customize the metadata in two ways:

### Using Standard Project Metadata (PEP 621)

You can use standard Python project metadata fields in your `pyproject.toml` file, which NEARC will automatically use to populate NEP-330 metadata:

```toml
[project]
name = "my-near-contract"
version = "0.2.0"
description = "My NEAR smart contract"

[project.urls]
repository = "https://github.com/myorg/mycontract"
```

### Using NEAR-Specific Configuration

For more advanced metadata and NEAR-specific fields, you can use the `[tool.near.contract]` section:

```toml
[tool.near.contract]
version = "0.2.0"
link = "https://github.com/myorg/mycontract"
standards = [
  { standard = "nep141", version = "1.0.0" },
  { standard = "nep148", version = "1.0.0" }
]
build_info = {
  build_environment = "docker.io/sourcescan/near-python@sha256:bf488476d9c4e49e36862bbdef2c595f88d34a295fd551cc65dc291553849471",
  source_code_snapshot = "git+https://github.com/myorg/mycontract.git#main",
  contract_path = ".",
  build_command = ["nearc", "contract.py", "--no-debug"]
}
```

This will generate a `contract_source_metadata` function in your contract that returns:

```json
{
  "version": "0.2.0",
  "link": "https://github.com/myorg/mycontract",
  "standards": [
    { "standard": "nep141", "version": "1.0.0" },
    { "standard": "nep148", "version": "1.0.0" },
    { "standard": "nep330", "version": "1.0.0" }
  ],
  "build_info": {
    "build_environment": "docker.io/sourcescan/near-python@sha256:bf488476d9c4e49e36862bbdef2c595f88d34a295fd551cc65dc291553849471",
    "source_code_snapshot": "git+https://github.com/myorg/mycontract.git#main",
    "contract_path": ".",
    "build_command": ["nearc", "contract.py", "--no-debug"]
  }
}
```

If you already have a `contract_source_metadata` function in your contract, it will be preserved.

### Metadata Field Priority

When both standard project metadata and NEAR-specific configuration are present, NEARC uses the following priority order:

1. Standard PEP 621 fields (`[project]` section)
2. NEAR-specific fields (`[tool.near.contract]` section)

The NEP-330 standard is always included in the standards list, ensuring compliance.

## How It Works

NEARC compiles Python smart contracts to WebAssembly through these steps:

1. **Code Analysis** - Identifies exported functions and dependencies in the Python code
2. **Metadata Injection** - Adds NEP-330 metadata if not already present
3. **Manifest Generation** - Creates a MicroPython manifest file that includes all necessary modules
4. **Export Wrapping** - Generates C wrappers for exported functions
5. **WebAssembly Compilation** - Uses MicroPython and Emscripten to compile to WebAssembly
6. **Optimization** - Produces a compact WASM file ready for blockchain deployment

The compiler handles dependency resolution automatically, making it easy to use Python libraries in your contracts (as long as they're compatible with MicroPython).


## Reproducible Builds

NEARC supports reproducible builds through Docker containers, ensuring that compiled WASM contracts can be verified by tools like SourceScan.

### Setting Up for Reproducible Builds

1. Initialize the reproducible build configuration in your project:

```bash
nearc contract.py --init-reproducible-config
```

This adds the required configuration to your `pyproject.toml` file. Update it with the correct Docker image digest found in our [GitHub releases](https://github.com/r-near/nearc/releases).

### Example Configuration

Your `pyproject.toml` should have a section like this:

```toml
[tool.near.reproducible_build]
image = "rnear/nearc:0.3.2-python-3.11"
image_digest = "sha256:abcdef123456789abcdef123456789abcdef123456789abcdef123456789abc"
container_build_command = ["nearc"]
```

### Building Reproducibly

To create a reproducible build:

1. Ensure all your code is committed to a Git repository
2. Run:

```bash
nearc contract.py --reproducible
```

This will:
- Verify your Git repository is clean (all changes committed)
- Pull the specified Docker image
- Build your contract in the container
- Generate a WASM file with embedded metadata for verification

### Requirements for Verification

For successful verification:
- All code must be in a public Git repository
- All changes must be committed before building
- You must use the `--reproducible` flag for the build

### Verification Process

When your contract is deployed, verification tools like SourceScan will:
1. Extract the metadata from your contract
2. Pull the exact source code from your Git repository
3. Build using the same Docker container specified in your metadata
4. Compare the resulting WASM with what's deployed on-chain

### Troubleshooting

If verification fails:
- Ensure you used `--reproducible` flag when building
- Check that all code was committed before building
- Verify you're using the correct Docker image and digest
- Make sure your Git repository is public and accessible

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