# ─── Stage 1: Build & Install Dependencies ───────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools needed for some pip packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt setup.py ./
COPY src/ src/

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime Image ──────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Chromium + ChromeDriver (needed for Selenium scraping)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
        libnss3 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libgbm1 \
        libasound2 \
        libxshmfence1 \
        wget \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set Chrome environment variables for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY app.py .
COPY setup.py .
COPY src/ src/
COPY pages/ pages/
COPY static/ static/
COPY templates/ templates/

# Install the project itself in editable mode
RUN pip install --no-cache-dir -e .

# Render uses the PORT env variable; default to 8501 for Streamlit
ENV PORT=8501

# Expose the port Streamlit will run on
EXPOSE ${PORT}

# Streamlit configuration for production
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT}/ || exit 1

# Start the Streamlit app — Render injects PORT at runtime
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0
