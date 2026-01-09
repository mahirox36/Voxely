FROM ubuntu:23.10

# --------------------------
# Install multiple Java versions and python
# --------------------------
RUN apt-get update && apt-get install -y \
    openjdk-8-jdk-headless \
    openjdk-17-jdk-headless \
    openjdk-21-jdk-headless \
    python3 python3-pip \
    wget curl unzip git && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME defaults (optional, can be switched in Python)
ENV JAVA_8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV JAVA_17_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV JAVA_21_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_17_HOME/bin:$PATH"

# --------------------------
# Setup backend
# --------------------------
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 25401

CMD ["uvicorn", "core:app", "--host", "0.0.0.0", "--port", "25401"]
