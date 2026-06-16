#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: Mini-Drop real perf mode requires Linux." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not installed." >&2
  echo "Install Docker Engine: https://docs.docker.com/engine/install/ubuntu/" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose v2 plugin is not installed." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon is unavailable or the current user lacks permission." >&2
  echo "Try: sudo usermod -aG docker \"$USER\" and then log in again." >&2
  exit 1
fi

paranoid="$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo unknown)"
echo "kernel.perf_event_paranoid=$paranoid"
echo "Docker and Compose are ready. The privileged Agent uses host PID namespace."
