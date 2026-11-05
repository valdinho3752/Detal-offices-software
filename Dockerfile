FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py .
COPY app ./app
COPY database ./database
COPY scripts ./scripts

RUN useradd --create-home clinica
USER clinica

EXPOSE 8000
CMD ["python", "run.py"]
