FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY install_server.py .

# Use unbuffered output
ENV PYTHONUNBUFFERED=1

# Expose port 8001 for Streamlit to hit (our Fastapi wrapper)
EXPOSE 8001

# The main entrypoint
CMD ["python", "install_server.py", "--http"]
