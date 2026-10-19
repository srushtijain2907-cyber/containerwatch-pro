FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY healer.py .
EXPOSE 8000
# runs as root on purpose: it needs access to /var/run/docker.sock (see README security notes)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "healer:app"]
