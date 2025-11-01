FROM python:3.14

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Run Uvicorn on all interfaces so Docker can connect
CMD ["uvicorn", "core:app", "--host", "0.0.0.0", "--port", "25401"]
