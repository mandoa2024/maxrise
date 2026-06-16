FROM ubuntu:22.04 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY examples/cpu_hotspot.c .
RUN gcc -O2 -g -fno-omit-frame-pointer -o /cpu_hotspot cpu_hotspot.c -lm

FROM ubuntu:22.04
COPY --from=builder /cpu_hotspot /usr/local/bin/cpu_hotspot
CMD ["bash", "-c", "echo $$ > /runtime/workload.pid; exec /usr/local/bin/cpu_hotspot"]
