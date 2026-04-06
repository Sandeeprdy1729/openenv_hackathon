FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY environment.py .
COPY openenv.yaml .
COPY inference.py .

EXPOSE 8003

CMD ["python3", "environment.py"]