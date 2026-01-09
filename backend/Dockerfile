FROM python:3.14-slim

# --------------------------
# Install multiple Java versions
# --------------------------
RUN apt-get update && apt-get install -y \
    openjdk-8-jdk-headless \
    openjdk-17-jdk-headless \
    openjdk-21-jdk-headless \
    wget curl unzip git && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME defaults (optional, can be switched in Python)
ENV JAVA_8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV JAVA_17_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV JAVA_21_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_17_HOME/bin:$PATH"

# --------------------------
# Setup Python
# --------------------------
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose backend port
EXPOSE 25401

# Run Uvicorn on all interfaces
CMD ["uvicorn", "core:app", "--host", "0.0.0.0", "--port", "25401"]
