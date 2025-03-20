FROM --platform=$BUILDPLATFORM python:3.11-slim-bookworm AS base

# Install required packages and Homebrew dependencies
RUN apt-get update && apt-get install -y \
    git \
    make \
    cmake \
    clang \
    gcc \
    g++ \
    wget \
    curl \
    xz-utils \
    ca-certificates \
    build-essential \
    procps \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install Homebrew
RUN /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
ENV PATH="/home/linuxbrew/.linuxbrew/bin:${PATH}"

# Install Emscripten using Homebrew
RUN brew install emscripten

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables for Emscripten
ENV EMSDK="$(brew --prefix emscripten)/libexec"
ENV EMSCRIPTEN="$(brew --prefix emscripten)/libexec/upstream/emscripten"
ENV PATH="${EMSCRIPTEN}:${PATH}"

# Mark as running in a container
ENV CONTAINER="1"

# Verify Emscripten installation
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