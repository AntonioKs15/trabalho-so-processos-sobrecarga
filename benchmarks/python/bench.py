"""
bench.py - testes de desempenho em Python (mesmos algoritmos de bench.c e main.rs).

Uso: python bench.py <teste> <tamanho> [threads]
  cpu      <n>      crivo de Eratostenes ate n; resultado = quantidade de primos
  memoria  <mb>     aloca mb MiB e escreve 1 byte por pagina de 4 KiB
  io       <mb>     escreve e le mb MiB em /tmp em blocos de 4 KiB (os.read/os.write)
  threads  <n> [t]  t threads somam (i*i) % 1000 para i em [0, n)

Os lacos sao escritos em Python puro, de proposito: a ideia e medir o
interpretador, e nao rotinas em C escondidas na biblioteca padrao.
"""

import json
import os
import sys
import threading
import time

PAGINA = 4096
BLOCO = 4096
MIB = 1024 * 1024


def teste_cpu(n):
    primo = bytearray(b"\x01") * (n + 1)
    primo[0] = 0
    if n >= 1:
        primo[1] = 0
    i = 2
    while i * i <= n:
        if primo[i]:
            for j in range(i * i, n + 1, i):
                primo[j] = 0
        i += 1
    total = 0
    for x in primo:
        total += x
    return total


def teste_memoria(mb):
    tamanho = mb * MIB
    buf = bytearray(tamanho)  # CPython zera o buffer inteiro (toca todas as paginas)
    paginas = tamanho // PAGINA
    for p in range(paginas):
        buf[p * PAGINA] = p & 0xFF
    soma = 0
    for p in range(paginas):
        soma += buf[p * PAGINA]
    return soma


def teste_io(mb):
    caminho = f"/tmp/bench_python_{os.getpid()}.dat"
    blocos = mb * MIB // BLOCO
    # os.open/os.write/os.read chamam diretamente open(2)/write(2)/read(2), sem buffer
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    for b in range(blocos):
        os.write(fd, bytes([b & 0xFF]) * BLOCO)
    os.close(fd)

    soma = 0
    fd = os.open(caminho, os.O_RDONLY)
    while True:
        bloco = os.read(fd, BLOCO)
        if not bloco:
            break
        soma += bloco[0]
    os.close(fd)
    os.unlink(caminho)
    return soma


def teste_threads(n, t):
    passo = n // t
    somas = [0] * t

    def trabalhar(k, inicio, fim):
        s = 0
        for i in range(inicio, fim):
            s += (i * i) % 1000
        somas[k] = s

    threads = []
    for k in range(t):
        inicio = k * passo
        fim = n if k == t - 1 else (k + 1) * passo
        th = threading.Thread(target=trabalhar, args=(k, inicio, fim))
        th.start()
        threads.append(th)
    for th in threads:
        th.join()
    return sum(somas)


def main():
    if len(sys.argv) < 3:
        print("uso: bench.py <cpu|memoria|io|threads> <tamanho> [threads]", file=sys.stderr)
        sys.exit(2)
    teste = sys.argv[1]
    tamanho = int(sys.argv[2])
    t = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    t = max(1, min(256, t))

    testes = {
        "cpu": lambda: teste_cpu(tamanho),
        "memoria": lambda: teste_memoria(tamanho),
        "io": lambda: teste_io(tamanho),
        "threads": lambda: teste_threads(tamanho, t),
    }
    if teste not in testes:
        print(f"teste desconhecido: {teste}", file=sys.stderr)
        sys.exit(2)

    inicio = time.perf_counter()
    r = testes[teste]()
    ms = (time.perf_counter() - inicio) * 1000
    print(json.dumps({"linguagem": "python", "teste": teste, "resultado": r,
                      "tempo_interno_ms": round(ms, 3)}))


if __name__ == "__main__":
    main()
