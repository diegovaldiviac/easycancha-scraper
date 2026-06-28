FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Suppress the HeadlessChrome UA that easycancha blocks at /api/login
    PLAYWRIGHT_CHROMIUM_ARGS="--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

COPY . .

CMD ["python", "main.py"]
