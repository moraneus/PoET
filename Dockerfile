# Dockerfile for PoET - Partial Order Execution Tracer
# This container provides a complete environment for running PoET monitoring
# with PCTL runtime verification capabilities

# Use Python 3.12 slim image to match PoET requirements
FROM python:3.12-slim

# Set metadata
LABEL maintainer="Moran Omer <moraneus@gmail.com>"
LABEL description="PoET - Partial Order Execution Tracer for Distributed Systems Runtime Verification"
LABEL version="1.0.0"
LABEL org.opencontainers.image.title="PoET"
LABEL org.opencontainers.image.description="PCTL Runtime Verification Tool for Distributed Systems"
LABEL org.opencontainers.image.authors="Moran Omer, Doron Peled, Ely Porat, Vijay K. Garg"
LABEL org.opencontainers.image.source="https://github.com/moraneus/PoET"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV POET_OUTPUT_LEVEL=default
ENV POET_WORKSPACE=/workspace

# Create a non-root user for security
RUN groupadd -r poet && useradd -r -g poet -d /app -s /bin/bash -c "PoET User" poet

# Install system dependencies including Graphviz for visualization
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    libc6-dev \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Copy the application code
COPY . .

# Create directories for user files and outputs
RUN mkdir -p /workspace /workspace/traces /workspace/properties /workspace/output && \
    chown -R poet:poet /app /workspace

# Copy example files to workspace
RUN if [ -d "examples" ]; then \
        cp -r examples/* /workspace/ 2>/dev/null || true; \
    fi

# Switch to non-root user
USER poet

# Expose port for potential web interface (future feature)
# EXPOSE 8080

# Add health check to verify PoET components
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import core, parser, utils, model, graphics; print('PoET components loaded successfully')" || exit 1

# Create volume mount points
VOLUME ["/workspace"]

# Set default command to show help
CMD ["python", "poet.py", "--help"]

# Build arguments for customization
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Add comprehensive build labels following OCI standards
LABEL org.opencontainers.image.created=$BUILD_DATE
LABEL org.opencontainers.image.version=$VERSION
LABEL org.opencontainers.image.revision=$VCS_REF
LABEL org.opencontainers.image.vendor="PoET Development Team"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.url="https://github.com/moraneus/PoET"
LABEL org.opencontainers.image.documentation="https://github.com/moraneus/PoET#readme"

# Legacy labels for backward compatibility
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="poet" \
      org.label-schema.description="Partial Order Execution Tracer - PCTL Runtime Verification Tool" \
      org.label-schema.url="https://github.com/moraneus/PoET" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/moraneus/PoET" \
      org.label-schema.vendor="PoET Development Team" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"