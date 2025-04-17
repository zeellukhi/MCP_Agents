# MCP_Agents/Dockerfile
# --- Base Image ---
# Use an official Python runtime as a parent image.
# Choose a version compatible with your dependencies, slim version is smaller.
FROM python:3.11-slim

# --- Environment Variables ---
# Prevents Python from buffering stdout and stderr (good for logging in containers)
ENV PYTHONUNBUFFERED=1
# Set the working directory inside the container
WORKDIR /app

# --- Install Dependencies ---
# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt ./
# Install dependencies. --no-cache-dir reduces image size.
# Consider using --upgrade pip setuptools wheel first for robustness
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# --- Copy Application Code ---
# Copy the rest of the application source code into the container
# Includes src/, main.py, potentially credentials if needed (though .env is better)
COPY src/ ./src/
COPY main.py ./

# --- Container Healthcheck (Optional but Recommended) ---
# Example: Check if the API server is responding on its port
# Adjust the port and path as necessary. Requires curl to be installed.
# RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* # Uncomment if adding curl
# HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
#  CMD curl --fail http://localhost:8081/ || exit 1 # Check if root serves frontend or use /api/chat

# --- Default Command ---
# Command to run when the container launches.
# Uses the host/port settings from .env or defaults defined in config.py/main.py.
CMD ["python", "main.py"]

# Note: Ports are typically exposed in docker-compose.yml, not directly here.
# EXPOSE 8081
# EXPOSE 9091