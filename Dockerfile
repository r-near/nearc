FROM --platform=$BUILDPLATFORM python:3.11-slim-bookworm AS base

# For EMSDK, specify the platform explicitly
FROM --platform=$BUILDPLATFORM docker.io/emscripten/emsdk:latest AS emsdk-source

# For UV, specify the platform explicitly  
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:latest AS uv-source

# Back to the main build
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm

# Install required packages
RUN apt-get update && apt-get install -y \
    git \
    make \
    cmake \
    clang \
    gcc \
    g++ \
    wget \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy UV from the source stage
COPY --from=uv-source /uv /uvx /bin/

# Copy EMSDK from the source stage
COPY --from=emsdk-source /emsdk /emsdk
ENV PATH="/emsdk:/emsdk/node/20.18.0_64bit/bin:/emsdk/upstream/emscripten:${PATH}"

ENV EMSDK="/emsdk"
ENV EMSCRIPTEN="/emsdk/upstream/emscripten"

# Mark as running in a container
ENV CONTAINER="1"

RUN emcc -v

ENV PATH="/root/.local/bin:$PATH"

# Set up working directory
WORKDIR /app

# Copy your project files to the container
COPY src/ pyproject.toml uv.lock README.md /app/

# Install nearc
RUN uv tool install .

# Set working directory for build outputs
WORKDIR /home/near/code

# Set entrypoint to nearc with automatic dependency setup
ENTRYPOINT ["nearc", "--create-venv"]