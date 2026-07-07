#!/bin/bash

set -e

VEX_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$VEX_ROOT"

echo "========================================"
echo "Vex Claude Ollama ile başlatılıyor..."
echo "Klasör: $VEX_ROOT"
echo "Model: qwen2.5-coder:7b"
echo "========================================"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama bulunamadı."
  echo "Kurulum: brew install ollama"
  exit 1
fi

if ! lsof -i :11434 >/dev/null 2>&1; then
  echo "Ollama server başlatılıyor..."
  nohup ollama serve >/tmp/ollama-vex.log 2>&1 &
  sleep 3
fi

if ! ollama list | grep -q "qwen2.5-coder:7b"; then
  echo "qwen2.5-coder:7b indiriliyor..."
  ollama pull qwen2.5-coder:7b
fi

echo ""
echo "Claude Code, Ollama endpoint'i ile açılıyor..."
echo ""

export ANTHROPIC_AUTH_TOKEN="ollama"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL="http://localhost:11434"

claude --model qwen2.5-coder:7b
