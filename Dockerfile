FROM python:3.11

WORKDIR /app
# This ensures Python can find 'financial_analysis_env' and 'server'
ENV PYTHONPATH=/app

# 1. Install uv as required by the validator
RUN pip install uv

# 2. Copy the config files first (best practice for caching)
COPY pyproject.toml requirements.txt uv.lock* ./

# 3. Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of the code
COPY . .

# 5. Install the local package in editable mode so imports work perfectly
RUN pip install -e .

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]