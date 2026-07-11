FROM python:3.11-slim

WORKDIR /workspace

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app_platform/ ./app_platform/

# Set environment
ENV PYTHONPATH=/workspace
ENV BRAND_NAME=Shopnoltd
ENV COMPANY_NAME="Shopno Database Firm"

# Expose port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "app_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
