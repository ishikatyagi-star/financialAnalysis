FROM python:3.11-slim

WORKDIR /app

# Copy project
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose API port
EXPOSE 7860

# Start FastAPI server
CMD ["uvicorn", "financial_analysis_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]