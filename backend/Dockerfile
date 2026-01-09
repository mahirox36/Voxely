FROM python:3.14-slim

# --------------------------
# Install Java 8 and 17 + basic tools
# --------------------------
RUN apt-get update && apt-get install -y \
    openjdk-8-jdk-headless \
    openjdk-17-jdk-headless \
    wget curl unzip git && \
    rm -rf /var/lib/apt/lists/*


RUN mkdir -p /opt/java21
# download directly from GitHub (replace URL with your tar.gz)
RUN curl -L -o /tmp/OpenJDK21.tar.gz \
    https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.9+10/OpenJDK21U-jdk_x64_linux_hotspot_21.0.9_10.tar.gz && \
    tar -xzf /tmp/OpenJDK21.tar.gz -C /opt/java21 --strip-components=1 && \
    rm /tmp/OpenJDK21.tar.gz


ENV JAVA_8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV JAVA_17_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV JAVA_21_HOME=/opt/java21

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
