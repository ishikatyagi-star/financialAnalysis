FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy only the dependency files first
COPY pyproject.toml uv.lock ./

# Install the project dependencies
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the code
COPY . .

# Install the project itself so package-dir mappings take effect
RUN uv pip install --system -e .

# Install yaml and gradio for metadata loading and web UI
RUN pip install pyyaml gradio

# Set PYTHONPATH so imports resolve correctly
ENV PYTHONPATH=/app

# Enable Custom Gradio web interface (and disable generic framework playground)
ENV ENABLE_WEB_INTERFACE=false

# Start the server — must match entrypoint in openenv.yaml
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]