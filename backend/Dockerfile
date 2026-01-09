FROM python:3.14-slim

# Install basic tools
RUN apt-get update && apt-get install -y wget curl unzip git && rm -rf /var/lib/apt/lists/*

# --------------------------
# Java 8
# --------------------------
RUN mkdir -p /opt/java8 && \
    curl -L -o /tmp/jdk8.tar.gz \
    https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u472-b08/OpenJDK8U-jdk_x64_linux_hotspot_8u472b08.tar.gz && \
    tar -xzf /tmp/jdk8.tar.gz -C /opt/java8 --strip-components=1 && \
    rm /tmp/jdk8.tar.gz

# --------------------------
# Java 17
# --------------------------
RUN mkdir -p /opt/java17 && \
    curl -L -o /tmp/jdk17.tar.gz \
    https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.9+9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.9_9.tar.gz && \
    tar -xzf /tmp/jdk17.tar.gz -C /opt/java17 --strip-components=1 && \
    rm /tmp/jdk17.tar.gz

# --------------------------
# Java 21
# --------------------------
RUN mkdir -p /opt/java21 && \
    curl -L -o /tmp/jdk21.tar.gz \
    https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.9+10/OpenJDK21U-jdk_x64_linux_hotspot_21.0.9_10.tar.gz && \
    tar -xzf /tmp/jdk21.tar.gz -C /opt/java21 --strip-components=1 && \
    rm /tmp/jdk21.tar.gz

# --------------------------
# JAVA_HOME
# --------------------------
ENV JAVA_8_HOME=/opt/java8
ENV JAVA_17_HOME=/opt/java17
ENV JAVA_21_HOME=/opt/java21
ENV PATH="$JAVA_17_HOME/bin:$PATH"

# --------------------------
# Python backend
# --------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 25401
CMD ["uvicorn", "core:app", "--host", "0.0.0.0", "--port", "25401"]
