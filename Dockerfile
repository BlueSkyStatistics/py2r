FROM rocker/r-ver:4.4.3

# Install system dependencies (combining from both current Dockerfiles)
RUN apt update && apt install -y \
    # R system dependencies (from Dockerfile.r) \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    libgit2-dev \
    pandoc \
    cmake \
    # Python dependencies (from Dockerfile.python) \
    python3 \
    python3-pip \
    python3-dev \
    gcc \
    g++ \
    curl \
    # Additional dependencies for rpy2 to work properly \
    python3-venv \
    gfortran \
    libblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python/pip
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Set environment variables for R
ENV R_HOME=/usr/local/lib/R
ENV R_LIBS_USER=/usr/local/lib/R/site-library
ENV LD_LIBRARY_PATH=/usr/local/lib/R/lib:$LD_LIBRARY_PATH

# Create shared directories
RUN mkdir -p /shared /usr/local/lib/R/site-library

# Set working directory for Python app
WORKDIR /app

# https://docs.astral.sh/uv/guides/integration/docker/#non-editable-installs
ENV UV_SYSTEM_PYTHON=1
# Install Python package manager
RUN pip install uv --break-system-packages

# Copy Python project files
COPY pyproject.toml uv.lock ./

# Set environment variables for Python/rpy2 (following your current setup)
ENV UV_NO_CACHE=true
ENV PYTHONPATH=/app
ENV R_HOME_DIR=/usr/local/lib/R

# Install Python dependencies with uv
RUN uv sync --locked

# Copy application files
COPY ./*.py ./
COPY py2r ./py2r

# Expose port for HTTP server (Electron will connect to this)
EXPOSE 8000

# Run the HTTP-based console (no Rserve needed, uses local rpy2)
CMD ["uv", "run", "console_http.py", "8000"]
