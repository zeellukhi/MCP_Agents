# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy dependency descriptor files
COPY pyproject.toml requirements.txt ./

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the API and MCP server ports (as defined in docker-compose)
EXPOSE 8081 9091

# Run the unified entry point that starts both API and MCP servers
CMD ["python", "main.py"]
