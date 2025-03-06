# NEAR Python Contracts: Reproducible Builds Guide

This guide explains how to create reproducible builds for NEAR Python smart contracts, enabling source code verification by tools like SourceScan.

## What are Reproducible Builds?

Reproducible builds ensure that a given source code always compiles to the exact same bytecode, regardless of when or where you build it. This is essential for verifying that the deployed contract matches its source code.

For NEAR contracts, this means ensuring that:
1. The source code is available in a Git repository
2. The build environment is standardized (using Docker)
3. The build process is deterministic
4. All build information is embedded in the contract's metadata

## Prerequisites

- Python 3.11+
- Docker installed and configured
- Git repository for your contract
- nearc 0.3.2+ (Python contract compiler)

## Step 1: Initialize Reproducible Build Configuration

To start using reproducible builds, initialize the configuration in your project:

```bash
nearc contract.py --init-reproducible-config
```

This will create or update your `pyproject.toml` file with the necessary configuration:

```toml
[tool.near.reproducible_build]
image = "ghcr.io/r-near/nearc@sha256:REPLACE_WITH_ACTUAL_DIGEST"
container_build_command = ["nearc"]
```

## Step 2: Update Configuration with Correct Docker Image Digest

Replace the example digest with the actual SHA-256 digest of the Docker image:

```toml
image_digest = "sha256:abcdef123456789abcdef123456789abcdef123456789abcdef123456789abc"
```

You can find the digest by running:

```bash
docker pull ghcr.io/r-near/nearc:latest
docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/r-near/nearc:latest
```

## Step 3: Commit Your Code to Git

Before building reproducibly, make sure:
1. Your code is part of a Git repository
2. All changes are committed
3. The repository has a remote URL set

```bash
git init  # If not already a git repository
git add .
git commit -m "Ready for reproducible build"
git remote add origin https://github.com/username/my-near-contract
```

The reproducible build will fail if there are uncommitted changes.

## Step 4: Build Your Contract Reproducibly

Use the `--reproducible` flag to build your contract:

```bash
nearc contract.py --reproducible
```

This will:
1. Verify that all code is committed
2. Pull the specified Docker image
3. Run the build inside a Docker container
4. Generate a WASM file with embedded metadata

## Step 5: Deploy Your Contract

Deploy your contract as usual:

```bash
near deploy your-account.near contract.wasm
```

## Step 6: Verify Your Contract

After deployment, you can verify your contract on SourceScan:
1. Find your contract on NearBlocks
2. Go to the Contract Code tab
3. Click "Verify and Publish"
4. Wait for the verification process to complete

## How Verification Works

1. **Metadata Extraction**: SourceScan reads the contract metadata
2. **Source Retrieval**: Clones the repository at the specific commit
3. **Environment Setup**: Uses the exact Docker image specified
4. **Build Process**: Runs the same build command
5. **Comparison**: Compares the generated WASM with the on-chain WASM

If they match exactly, the contract is verified!

## Troubleshooting

### Build fails with Git errors
- Ensure all changes are committed
- Check that your repository has a remote set
- Make sure the remote is accessible

### Docker issues
- Verify Docker is running
- Ensure you have permissions to use Docker
- Check you have internet access to pull the image

### Verification fails
- Confirm you used the correct Docker image digest
- Ensure your repository is public
- Verify that the commit hash in the metadata matches the source code

## Technical Details

### Docker Image

The Docker image contains:
- A specific version of Python
- Emscripten compiler
- nearc at a specific version
- All necessary dependencies

### Metadata Structure

The contract metadata follows the NEP-330 standard with these fields:

```json
{
  "standards": [{"standard": "nep330", "version": "1.0.0"}],
  "link": "https://github.com/username/my-near-contract",
  "build_info": {
    "build_environment": "ghcr.io/r-near/nearc@sha256:REPLACE_WITH_ACTUAL_DIGEST",
    "build_command": ["nearc"],
    "source_code_snapshot": "git+https://github.com/username/my-near-contract.git#CURRENT_COMMIT"
  }
}
```

This information enables exact reproduction of the build environment.

## Complete Example of pyproject.toml

```toml
[project]
name = "my-near-contract"
version = "0.1.0"
description = "My NEAR smart contract in Python"
requires-python = ">=3.11"
repository = "https://github.com/username/my-near-contract"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.near.reproducible_build]
# Docker image, descriptor of build environment
image = "ghcr.io/r-near/nearc@sha256:REPLACE_WITH_ACTUAL_DIGEST"
# Build command inside the Docker container
container_build_command = ["nearc"]

# Optional contract-specific metadata
[tool.near.contract]
standards = [
  { standard = "nep141", version = "1.0.0" }
]
```
