FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy only the dependency files first
COPY pyproject.toml uv.lock ./

# Install the project and dependencies
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the code
COPY . .

# Set PYTHONPATH so the 'server' can find 'financial_analysis_env'
ENV PYTHONPATH=/app

# Start the server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]