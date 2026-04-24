FROM python:3.11-slim

WORKDIR /app

RUN pip install hatch

COPY pyproject.toml .
RUN pip install .

# Install Playwright and download Chromium with all required system dependencies.
# --with-deps installs the correct OS libraries for the current platform,
# replacing the manually-maintained apt-get list that was incomplete.
RUN pip install playwright && playwright install --with-deps chromium

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
