FROM python:3.11

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy everything
COPY . .

# Upgrade pip
RUN pip install --upgrade pip

# Install YOUR project (this installs openenv-core too)
RUN pip install .

# Run server
CMD ["uvicorn", "financial_analysis_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]