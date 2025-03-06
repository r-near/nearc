FROM python:3.11-slim-bookworm

# Install required packages including Emscripten
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


# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy emsdk from Emscripten
COPY --from=docker.io/emscripten/emsdk:latest /emsdk /emsdk
ENV PATH="/emsdk:/emsdk/node/20.18.0_64bit/bin:/emsdk/upstream/emscripten:${PATH}"

ENV EMSDK="/emsdk"
ENV EMSCRIPTEN="/emsdk/upstream/emscripten"

RUN emcc -v


ENV PATH="/root/.local/bin:$PATH"

# Set up working directory
WORKDIR /app

# Copy your project files to the container
COPY src/ pyproject.toml uv.lock README.md /app/


# Install nearc
RUN uv tool install .

# Set working directory for build outputs
WORKDIR /build

# Set entrypoint to nearc
ENTRYPOINT ["nearc"]
