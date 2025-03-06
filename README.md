# NEARC - NEAR Python Contract Compiler

NEARC is a specialized compiler that transforms Python smart contracts into WebAssembly bytecode for deployment on the NEAR blockchain. It allows developers to write smart contracts in Python rather than Rust or AssemblyScript, leveraging MicroPython as the underlying runtime.

## Features

- Write NEAR smart contracts in Python
- Use Python decorators (`@export`, `@view`, `@call`, etc.) to mark contract methods
- Automatic dependency detection and packaging
- Optimized WebAssembly output
- Automatic NEP-330 contract metadata compliance
- **Reproducible builds for contract verification**
- **Auto-detection of contract entrypoint files**

## Prerequisites

- Python 3.11 or newer
- [Emscripten](https://emscripten.org/docs/getting_started/) (emcc must be in PATH)
- [uv](https://github.com/astral-sh/uv) for Python package management
- [Docker](https://docs.docker.com/get-docker/) (for reproducible builds)
- [Git](https://git-scm.com/downloads) (for reproducible builds)

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
# Basic usage with explicit contract file
nearc contract.py

# Auto-detect contract file (looks for __init__.py or main.py)
nearc

# Specify output file
nearc contract.py -o my-contract.wasm

# Use custom virtual environment
nearc contract.py --venv my-venv

# Force rebuild
nearc contract.py --rebuild

# Initialize reproducible build configuration
nearc --init-reproducible-config

# Build reproducibly for contract verification
nearc contract.py --reproducible
```

### Command Line Options

| Option                      | Description                                                |
|-----------------------------|------------------------------------------------------------|
| `contract`                  | Path to contract file (optional - auto-detects if omitted) |
| `--output`, `-o`           | Output WASM filename (default: derived from contract name) |
| `--venv`                   | Path to virtual environment (default: `.venv`)             |
| `--rebuild`                | Force rebuild of all components                            |
| `--init-reproducible-config`| Initialize configuration for reproducible builds           |
| `--reproducible`           | Build reproducibly in Docker for contract verification     |

### Contract Entrypoint

NEARC requires a single entrypoint file that contains all the exported functions (functions with `@near.export` or other export decorators). While your contract can span multiple files, all decorated functions must be in this entrypoint file.

If you don't specify a contract file, NEARC will auto-detect the entrypoint by looking for:

1. `__init__.py` in the current directory (first priority)
2. `main.py` in the current directory (second priority)

Best practices:
- For simple contracts: Use a single file with all your code
- For complex contracts: Use `__init__.py` as your entrypoint that imports and re-exports functions from other modules

Example project structure:
```
my-contract/
├── __init__.py      # Entrypoint with all @export decorators
├── logic.py         # Supporting code (no export decorators)
├── models.py        # Data models and utilities
└── utils/
    └── helpers.py   # Additional utilities
```

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

## Reproducible Builds and Contract Verification

NEARC supports reproducible builds for contract verification, allowing users to verify that the deployed WASM matches the source code.

### Setting Up Reproducible Builds

1. Initialize the configuration:

```bash
nearc contract.py --init-reproducible-config
```

2. Update the generated configuration in `pyproject.toml` with the actual Docker image digest:

```toml
[tool.near.reproducible_build]
image = "ghcr.io/r-near/nearc@sha256:REPLACE_WITH_ACTUAL_DIGEST"
container_build_command = ["nearc"]
```

3. Ensure your code is in a Git repository with all changes committed.

4. Build reproducibly:

```bash
nearc contract.py --reproducible
```

### Verification Process

After deploying your contract, it can be verified on platforms like NearBlocks through SourceScan:

1. Find your contract on NearBlocks
2. Go to the Contract Code tab
3. Click "Verify and Publish"

The verification tool will:
- Extract the metadata from your contract
- Clone the Git repository at the specified commit
- Use the exact Docker image specified in your metadata
- Build the contract and compare it with the on-chain version

For detailed information, see our [Reproducible Builds Guide](docs/reproducible-builds.md).

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
    "build_environment": "ghcr.io/r-near/nearc@sha256:REPLACE_WITH_ACTUAL_DIGEST",
    "build_command": ["nearc"],
    "source_code_snapshot": "git+https://github.com/myorg/mycontract.git#CURRENT_COMMIT"
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