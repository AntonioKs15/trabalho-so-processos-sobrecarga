"""
Três servidores HTTP mínimos, cada um com um modelo de execução diferente.

Todos fazem exatamente o mesmo trabalho por requisição (TRABALHO_IO_MS de espera,
simulando uma consulta a banco de dados, + TRABALHO_CPU_MS de processamento),
para que a única diferença entre eles seja COMO o sistema operacional é usado:

  processos -> pool fixo de processos (estilo "prefork" do Apache).
               Cada processo atende UMA conexão por vez.
  threads   -> uma thread do SO por conexão (thread-per-connection).
  eventos   -> um único processo/thread com laço de eventos (asyncio),
               estilo Nginx / Node.js.

Uso:
    python servidores.py processos --porta 8081
    python servidores.py threads   --porta 8082
    python servidores.py eventos   --porta 8083
"""

import argparse
import asyncio
import multiprocessing
import socket
import threading
import time

TRABALHO_IO_MS = 50          # espera de E/S simulada (ex.: consulta ao banco)
TRABALHO_CPU_MS = 1          # processamento simulado (ex.: montar a resposta)
REQUISICOES_POR_CONEXAO = 20  # como o MaxKeepAliveRequests do Apache
NUM_PROCESSOS = 8            # tamanho do pool no modelo "processos"
BACKLOG = 1024               # fila de conexões pendentes no kernel

CORPO = b"ok\n"


def resposta(fechar):
    conexao = b"close" if fechar else b"keep-alive"
    return (b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
            b"Content-Length: " + str(len(CORPO)).encode() + b"\r\n"
            b"Connection: " + conexao + b"\r\n\r\n" + CORPO)


def gastar_cpu(ms):
    """Ocupa a CPU de verdade (não libera o processador) por `ms` milissegundos."""
    fim = time.perf_counter() + ms / 1000
    x = 0
    while time.perf_counter() < fim:
        x += 1
    return x


def criar_socket(porta):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", porta))
    s.listen(BACKLOG)
    return s


# ---------------------------------------------------------------- bloqueante --
def atender_conexao_bloqueante(conn):
    """Usado pelos modelos 'processos' e 'threads': chamadas que BLOQUEIAM."""
    try:
        _atender(conn)
    except OSError:
        pass  # cliente desistiu (timeout) e fechou a conexão
    finally:
        conn.close()


def _atender(conn):
    buffer = b""
    for i in range(REQUISICOES_POR_CONEXAO):
        while b"\r\n\r\n" not in buffer:
            dados = conn.recv(4096)
            if not dados:
                return
            buffer += dados
        _, buffer = buffer.split(b"\r\n\r\n", 1)
        time.sleep(TRABALHO_IO_MS / 1000)   # E/S: o SO tira a tarefa da CPU
        gastar_cpu(TRABALHO_CPU_MS)
        ultima = i == REQUISICOES_POR_CONEXAO - 1
        conn.sendall(resposta(ultima))


# ----------------------------------------------------------------- processos --
def laco_do_processo(sock):
    # Cada processo filho bloqueia em accept() no MESMO socket de escuta;
    # o kernel entrega cada nova conexão a um dos processos livres.
    while True:
        conn, _ = sock.accept()
        atender_conexao_bloqueante(conn)


def servidor_processos(porta):
    sock = criar_socket(porta)
    filhos = [multiprocessing.Process(target=laco_do_processo, args=(sock,), daemon=True)
              for _ in range(NUM_PROCESSOS)]
    for p in filhos:
        p.start()
    print(f"[processos] {NUM_PROCESSOS} processos atendendo na porta {porta}", flush=True)
    for p in filhos:
        p.join()


# ------------------------------------------------------------------- threads --
def servidor_threads(porta):
    sock = criar_socket(porta)
    print(f"[threads] uma thread por conexão na porta {porta}", flush=True)
    while True:
        conn, _ = sock.accept()
        threading.Thread(target=atender_conexao_bloqueante, args=(conn,), daemon=True).start()


# ------------------------------------------------------------------- eventos --
async def atender_conexao_async(reader, writer):
    try:
        for i in range(REQUISICOES_POR_CONEXAO):
            try:
                await reader.readuntil(b"\r\n\r\n")
            except (asyncio.IncompleteReadError, ConnectionError):
                return
            await asyncio.sleep(TRABALHO_IO_MS / 1000)  # E/S: o laço atende outros
            gastar_cpu(TRABALHO_CPU_MS)                  # CPU: o laço inteiro para!
            ultima = i == REQUISICOES_POR_CONEXAO - 1
            writer.write(resposta(ultima))
            await writer.drain()
    finally:
        writer.close()


async def servidor_eventos(porta):
    servidor = await asyncio.start_server(atender_conexao_async, "127.0.0.1", porta,
                                          backlog=BACKLOG, reuse_address=True)
    print(f"[eventos] laço de eventos único na porta {porta}", flush=True)
    async with servidor:
        await servidor.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo", choices=["processos", "threads", "eventos"])
    ap.add_argument("--porta", type=int, default=8080)
    args = ap.parse_args()
    try:
        if args.modelo == "processos":
            servidor_processos(args.porta)
        elif args.modelo == "threads":
            servidor_threads(args.porta)
        else:
            asyncio.run(servidor_eventos(args.porta))
    except KeyboardInterrupt:
        pass
