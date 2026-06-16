FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git perl ca-certificates \
    && git clone --depth 1 https://github.com/brendangregg/FlameGraph.git /opt/FlameGraph \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./analyzer
ENV FLAMEGRAPH_PL=/opt/FlameGraph/flamegraph.pl
CMD ["uvicorn", "analyzer.main:app", "--host", "0.0.0.0", "--port", "8090"]
