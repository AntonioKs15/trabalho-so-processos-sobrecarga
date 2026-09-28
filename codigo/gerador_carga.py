"""
Gerador de carga: simula N clientes simultâneos fazendo requisições HTTP
sem parar durante alguns segundos e mede vazão, latência e erros.

Uso isolado (com um servidor já rodando):
    python gerador_carga.py --porta 8082 --clientes 100 --duracao 6
"""

import argparse
import asyncio
import statistics
import time

TIMEOUT_S = 5.0  # uma requisição que demora mais que isso conta como erro
REQUISICAO = b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"


async def ler_resposta(reader):
    cabecalho = await reader.readuntil(b"\r\n\r\n")
    tamanho, fechar = 0, False
    for linha in cabecalho.split(b"\r\n"):
        nome, _, valor = linha.partition(b":")
        nome = nome.strip().lower()
        if nome == b"content-length":
            tamanho = int(valor)
        elif nome == b"connection" and valor.strip().lower() == b"close":
            fechar = True
    await reader.readexactly(tamanho)
    return fechar


async def cliente(porta, fim, latencias, erros):
    reader = writer = None
    while time.perf_counter() < fim:
        inicio = time.perf_counter()
        try:
            async with asyncio.timeout(TIMEOUT_S):
                if writer is None:
                    reader, writer = await asyncio.open_connection("127.0.0.1", porta)
                writer.write(REQUISICAO)
                await writer.drain()
                fechar = await ler_resposta(reader)
            if time.perf_counter() <= fim:
                latencias.append((time.perf_counter() - inicio) * 1000)
        except (TimeoutError, OSError, asyncio.IncompleteReadError):
            erros.append(1)
            fechar = True
            await asyncio.sleep(0.05)
        if fechar and writer is not None:
            writer.close()
            reader = writer = None
    if writer is not None:
        writer.close()


def percentil(valores, p):
    if not valores:
        return float("nan")
    ordenados = sorted(valores)
    k = min(len(ordenados) - 1, int(round(p / 100 * (len(ordenados) - 1))))
    return ordenados[k]


async def rodar_carga(porta, clientes, duracao):
    latencias, erros = [], []
    fim = time.perf_counter() + duracao
    await asyncio.gather(*(cliente(porta, fim, latencias, erros) for _ in range(clientes)))
    return {
        "clientes": clientes,
        "vazao_req_s": len(latencias) / duracao,
        "lat_media_ms": statistics.fmean(latencias) if latencias else float("nan"),
        "lat_p50_ms": percentil(latencias, 50),
        "lat_p99_ms": percentil(latencias, 99),
        "erros": len(erros),
        "atendidas": len(latencias),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=8080)
    ap.add_argument("--clientes", type=int, default=50)
    ap.add_argument("--duracao", type=float, default=6)
    a = ap.parse_args()
    r = asyncio.run(rodar_carga(a.porta, a.clientes, a.duracao))
    for k, v in r.items():
        print(f"{k:>14}: {v:.1f}" if isinstance(v, float) else f"{k:>14}: {v}")
