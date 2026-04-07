FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY environment.py .
COPY openenv.yaml .
COPY inference.py .
COPY app.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["python3", "-u", "app.py"]