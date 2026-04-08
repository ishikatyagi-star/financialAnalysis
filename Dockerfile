FROM python:3.11

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "financial_analysis_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]