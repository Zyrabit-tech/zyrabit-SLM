# 1. Base Image: Use Slim for smaller attack surface
FROM python:3.10-slim

# 2. Environment Config (Avoid .pyc files and buffers)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 3. Create non-root user (Security)
# If container is compromised, they won't have system root access
RUN addgroup --system zyrabit && adduser --system --group zyrabit

# 4. Working Directory
WORKDIR /app

# 5. Install system dependencies (needed for some C++ libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 6. Install Python Dependencies (Cacheable layer)
COPY requirements.txt .
RUN pip install -r requirements.txt

# 7. Copy Code
COPY ./app ./app

# 8. Change permissions to non-root user
RUN chown -R zyrabit:zyrabit /app

# 9. Switch user
USER zyrabit

# 10. Expose Port
EXPOSE 8080

# 11. Startup Command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]