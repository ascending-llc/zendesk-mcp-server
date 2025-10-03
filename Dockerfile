
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and README (required by hatchling build)
COPY pyproject.toml uv.lock README.md ./

# Sync dependencies using uv
RUN uv sync --frozen --no-dev

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the MCP server using uv
CMD ["uv", "run", "python", "-m", "zendesk_mcp_server.server"]
