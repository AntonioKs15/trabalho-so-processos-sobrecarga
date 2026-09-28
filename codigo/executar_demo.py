"""
Roda o experimento completo:
  1. sobe cada servidor (processos, threads, eventos);
  2. aplica cargas crescentes (NIVEIS_CLIENTES) com o gerador de carga;
  3. mede, enquanto a carga roda, memória, threads e processos do servidor;
  4. salva resultados/resultados.csv e os gráficos PNG.

Uso:
    python executar_demo.py            # experimento completo (~2 min)
    python executar_demo.py --rapido   # versão curta para a apresentação (~40 s)
"""

import argparse
import asyncio
import csv
import os
import socket
import subprocess
import sys
import threading
import time

import psutil

from gerador_carga import rodar_carga

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_RESULTADOS = os.path.join(AQUI, "resultados")
MODELOS = {"processos": 8081, "threads": 8082, "eventos": 8083}
NIVEIS_CLIENTES = [10, 50, 100, 250, 500]


def esperar_porta(porta, limite=15):
    fim = time.time() + limite
    while time.time() < fim:
        try:
            socket.create_connection(("127.0.0.1", porta), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"servidor na porta {porta} não respondeu")


class Monitor(threading.Thread):
    """Amostra, a cada 200 ms, os recursos que o SO entregou ao servidor."""

    def __init__(self, pid):
        super().__init__(daemon=True)
        self.raiz = psutil.Process(pid)
        self.parar = threading.Event()
        self.mem_mb = self.threads = self.processos = 0
        self.cpu = []
        self.cache = {}

    def arvore(self):
        # reutiliza os objetos Process: cpu_percent() mede desde a chamada anterior
        procs = [self.raiz] + self.raiz.children(recursive=True)
        return [self.cache.setdefault(p.pid, p) for p in procs]

    def run(self):
        for p in self.arvore():
            p.cpu_percent(None)
        while not self.parar.wait(0.2):
            try:
                procs = self.arvore()
                self.mem_mb = max(self.mem_mb, sum(p.memory_info().rss for p in procs) / 2**20)
                self.threads = max(self.threads, sum(p.num_threads() for p in procs))
                self.processos = max(self.processos, len(procs))
                self.cpu.append(sum(p.cpu_percent(None) for p in procs))
            except psutil.Error:
                pass


def medir(modelo, porta, niveis, duracao):
    servidor = subprocess.Popen([sys.executable, os.path.join(AQUI, "servidores.py"),
                                 modelo, "--porta", str(porta)])
    linhas = []
    try:
        esperar_porta(porta)
        time.sleep(1)
        for n in niveis:
            mon = Monitor(servidor.pid)
            mon.start()
            r = asyncio.run(rodar_carga(porta, n, duracao))
            mon.parar.set()
            mon.join()
            total = r["atendidas"] + r["erros"]
            r.update(modelo=modelo,
                     memoria_mb=mon.mem_mb,
                     threads_so=mon.threads,
                     processos_so=mon.processos,
                     cpu_pct=sum(mon.cpu) / len(mon.cpu) if mon.cpu else 0.0,
                     erros_pct=100 * r["erros"] / total if total else 0.0)
            linhas.append(r)
            print(f"  {modelo:<9} {n:>4} clientes | {r['vazao_req_s']:7.1f} req/s | "
                  f"p99 {r['lat_p99_ms']:8.1f} ms | erros {r['erros_pct']:5.1f}% | "
                  f"mem {mon.mem_mb:6.1f} MB | threads {mon.threads:4d} | "
                  f"processos {mon.processos}", flush=True)
            time.sleep(1.5)
    finally:
        try:
            for p in psutil.Process(servidor.pid).children(recursive=True):
                p.kill()
        except psutil.Error:
            pass
        servidor.kill()
        servidor.wait()
    return linhas


def salvar_csv(linhas, caminho):
    campos = ["modelo", "clientes", "vazao_req_s", "lat_media_ms", "lat_p50_ms",
              "lat_p99_ms", "atendidas", "erros", "erros_pct", "memoria_mb",
              "threads_so", "processos_so", "cpu_pct"]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({k: round(v, 2) if isinstance(v, float) else v for k, v in l.items()})


# Paleta categórica validada (ordem fixa: 1 azul, 2 laranja, 3 verde-água)
CORES = {"processos": "#2a78d6", "threads": "#eb6834", "eventos": "#1baf7a"}
MARCADORES = {"processos": "s", "threads": "o", "eventos": "^"}
TINTA, TINTA_SEC, GRADE = "#1f1f1e", "#5f5e58", "#e4e3dc"


def rotular_fim_das_linhas(ax, finais, dpi, separacao_pt=11):
    """Rótulo direto no fim de cada linha, afastando rótulos que se sobrepõem."""
    ax.figure.canvas.draw()
    pos = sorted(((ax.transData.transform((x, y))[1] * 72 / dpi, m, x, y)
                  for m, x, y in finais))
    ajustadas = []
    for yp, m, x, y in pos:
        alvo = yp if not ajustadas else max(yp, ajustadas[-1][0] + separacao_pt)
        ajustadas.append((alvo, yp, m, x, y))
    for alvo, yp, m, x, y in ajustadas:
        ax.annotate(m, (x, y), xytext=(6, alvo - yp), textcoords="offset points",
                    va="center", fontsize=9, color=TINTA)


def graficos(linhas, pasta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "serif", "font.size": 10,
                         "axes.edgecolor": TINTA_SEC, "axes.labelcolor": TINTA,
                         "xtick.color": TINTA_SEC, "ytick.color": TINTA_SEC})
    metricas = [
        ("vazao_req_s", "Vazão (requisições/s)", "grafico_vazao.png", False),
        ("lat_p99_ms", "Latência p99 (ms, escala log)", "grafico_latencia_p99.png", True),
        ("memoria_mb", "Memória do servidor (MB)", "grafico_memoria.png", False),
        ("erros_pct", "Requisições com erro/timeout (%)", "grafico_erros.png", False),
    ]
    for chave, titulo, arquivo, log in metricas:
        fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=200)
        finais = []
        for modelo in MODELOS:
            pts = [(l["clientes"], l[chave]) for l in linhas if l["modelo"] == modelo]
            if not pts:
                continue
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=CORES[modelo], marker=MARCADORES[modelo], lw=2, ms=6,
                    label=modelo, markeredgecolor="white", markeredgewidth=1)
            finais.append((modelo, xs[-1], ys[-1]))
        if log:
            ax.set_yscale("log")
        else:
            ax.set_ylim(bottom=0)
        ax.set_xlabel("Clientes simultâneos")
        ax.set_ylabel(titulo)
        ax.grid(True, color=GRADE, lw=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        ax.set_xlim(0, max(l["clientes"] for l in linhas) * 1.15)
        ax.legend(frameon=False, loc="best", fontsize=9)
        rotular_fim_das_linhas(ax, finais, fig.dpi)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, arquivo))
        plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true", help="menos níveis e duração menor")
    a = ap.parse_args()
    niveis = [10, 100, 500] if a.rapido else NIVEIS_CLIENTES
    duracao = 3 if a.rapido else 6

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    todas = []
    for modelo, porta in MODELOS.items():
        print(f"\n=== Modelo: {modelo} ===", flush=True)
        todas += medir(modelo, porta, niveis, duracao)
    salvar_csv(todas, os.path.join(PASTA_RESULTADOS, "resultados.csv"))
    graficos(todas, PASTA_RESULTADOS)
    print(f"\nResultados salvos em {PASTA_RESULTADOS}")
