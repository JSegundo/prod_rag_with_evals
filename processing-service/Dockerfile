# Build stage
FROM python:3.11-slim-bookworm AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# # Upgrade pip and install build tools
RUN pip install pip setuptools wheel --upgrade

# Install heavy dependencies first (rarely changing)
COPY requirements/heavy.txt /requirements/
RUN pip install -r /requirements/heavy.txt

# Install base requirements second (frequently changing)
COPY requirements/base.txt /requirements/
RUN pip install -r /requirements/base.txt

# Cleanup after installing from requirements
RUN find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -delete && \
    rm -rf /root/.cache/pip

# Final stage
FROM python:3.11-slim-bookworm
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgomp1 \
    libxcb1 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "src/main.py"]