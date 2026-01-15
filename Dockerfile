# Use specific version for reproducibility
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
# build-essential: for compiling python packages like chroma-hnswlib
# poppler-utils: for pdf2image/unstructured
# libmagic1: for unstructured file type detection
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
# 1. Install CPU-only torch first to avoid downloading huge GPU binaries
RUN pip install --upgrade pip && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway ignores EXPOSE but good for documentation)
EXPOSE 8000

# Start command
# We use the shell form to allow variable expansion if needed, but CMD ["sh", "-c", ...] is safer
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
