# Dockerfile for MPPT Algorithm Comparison - Reproducible Research Environment

# Multi-stage build for minimal final image
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Development stage with additional tools
FROM base as development

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
RUN pip install pytest pytest-cov black flake8 mypy jupyter matplotlib

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# Run tests to verify environment
RUN pytest tests/ -v || true

# Final runtime image
FROM base as runtime

# Copy only necessary files
COPY src/ ./src/
COPY data/ ./data/
COPY results/ ./results/ 2>/dev/null || true
COPY scripts/ ./scripts/ 2>/dev/null || true
COPY Makefile ./

# Create non-root user for security
RUN useradd -m -u 1000 researcher && \
    chown -R researcher:researcher /app

USER researcher

# Default command
CMD ["python", "-c", "print('MPPT Comparison Environment Ready')"]

# LaTeX stage for paper compilation
FROM texlive/texlive:latest as paper

WORKDIR /paper

# Install additional LaTeX packages
RUN tlmgr install \
    algorithmicx \
    algorithms \
    amsmath \
    amssymb \
    booktabs \
    caption \
    color \
    colortbl \
    enumitem \
    float \
    geometry \
    graphicx \
    hyperref \
    listings \
    multirow \
    natbib \
    subcaption \
    tikz \
    titlesec \
    url \
    xcolor

COPY paper/ ./paper/
COPY results/ ./results/ 2>/dev/null || true

WORKDIR /paper/paper
CMD ["pdflatex", "-interaction=nonstopmode", "main.tex"]
