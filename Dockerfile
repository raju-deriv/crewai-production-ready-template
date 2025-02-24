# Multi-stage build
FROM python:3.12-slim as builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    python -m build

FROM python:3.12-slim as production
WORKDIR /app

# Install supervisor and create necessary directories
RUN apt-get update && \
    apt-get install -y supervisor && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/log/supervisor /var/run/supervisor /app/logs

# Copy and install the wheel from builder
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl && \
    rm *.whl

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/

# Copy application code and startup script
COPY . .

# Create non-root user and set permissions
RUN useradd -m -r crewai && \
    chown -R crewai:crewai /app/logs && \
    chown -R crewai:crewai /var/log/supervisor && \
    chown -R crewai:crewai /var/run/supervisor && \
    chmod 755 /var/log/supervisor /var/run/supervisor && \
    chmod +x /app/start.sh

# Switch to non-root user
USER crewai

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
