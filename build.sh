#!/usr/bin/env sh
# Compila bench.c e main.rs para Linux x86_64 estatico (musl), dentro do Docker.
# Os binarios vao para bin/ e sao enviados ao Vercel junto com a funcao Python.
#
#   sh build.sh
set -e
cd "$(dirname "$0")"
RAIZ="$(pwd -W 2>/dev/null || pwd)"   # pwd -W: caminho Windows no Git Bash

MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 -v "$RAIZ:/src" -w /src rust:1-alpine sh -c '
  set -e
  apk add --no-cache gcc musl-dev >/dev/null
  gcc --version | head -1
  rustc --version
  gcc -O2 -static -pthread -o bin/bench_c benchmarks/c/bench.c
  gcc -O2 -static -o bin/medir benchmarks/c/medir.c
  cd benchmarks/rust
  CARGO_TARGET_DIR=/tmp/alvo cargo build --release --quiet
  cp /tmp/alvo/release/bench_rust /src/bin/bench_rust
  strip /src/bin/bench_c /src/bin/bench_rust /src/bin/medir
  chmod 755 /src/bin/bench_c /src/bin/bench_rust /src/bin/medir
'
ls -l bin/
