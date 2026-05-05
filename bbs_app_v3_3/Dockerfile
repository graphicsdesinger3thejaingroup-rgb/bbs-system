FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy app
COPY backend/  ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

# Pre-create runtime dirs
RUN mkdir -p logs generated

ENV PORT=5000
ENV FLASK_DEBUG=0
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app:app"]
