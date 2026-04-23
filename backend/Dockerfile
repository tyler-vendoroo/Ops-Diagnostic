FROM python:3.11-slim

WORKDIR /app

# System dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

RUN pip install hatch

COPY pyproject.toml .
RUN pip install .

# Install Playwright and download Chromium binary
RUN pip install playwright && playwright install chromium

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
