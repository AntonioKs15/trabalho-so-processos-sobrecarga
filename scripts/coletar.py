"""
Coleta os dados do artigo chamando a API publicada e gera os gráficos.

    python scripts/coletar.py https://so-c-rust-python.vercel.app
    python scripts/coletar.py --graficos      (só refaz os gráficos a partir de resultados/dados.json)

Saídas em resultados/: dados.json, resultados.csv, ambiente.json e fig_*.png.
Requer matplotlib.
"""

import csv
import json
import os
import sys
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "resultados")
LINGUAGENS = ["c", "rust", "python"]
NOMES = {"c": "C", "rust": "Rust", "python": "Python"}
CORES = {"c": "#2f63a0", "rust": "#b7410e", "python": "#c49a00"}  # validadas (dataviz)
REPETICOES = 5

# (teste, tamanho, threads) - o primeiro de cada teste é o "padrão" do artigo
PLANO = [
    ("cpu", 2_000_000, 4), ("cpu", 500_000, 4), ("cpu", 5_000_000, 4), ("cpu", 10_000_000, 4),
    ("memoria", 128, 4), ("memoria", 32, 4), ("memoria", 256, 4), ("memoria", 512, 4),
    ("io", 32, 4), ("io", 8, 4), ("io", 64, 4), ("io", 128, 4),
    ("threads", 10_000_000, 1), ("threads", 10_000_000, 2), ("threads", 10_000_000, 4),
    ("threads", 10_000_000, 8),
]
PADRAO = {"cpu": 2_000_000, "memoria": 128, "io": 32, "threads": 10_000_000}


def obter(url):
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:  # rede instável: tenta de novo
            print(f"  falhou ({e}); tentando de novo")
            time.sleep(2 * (tentativa + 1))
    raise SystemExit(f"não consegui acessar {url}")


def coletar(base):
    os.makedirs(SAIDA, exist_ok=True)
    amb = obter(f"{base}/api/ambiente")
    amb.pop("testes", None)
    with open(os.path.join(SAIDA, "ambiente.json"), "w", encoding="utf-8") as f:
        json.dump(amb, f, ensure_ascii=False, indent=2)
    print("ambiente:", amb["distribuicao"], amb["kernel"], amb["cpu_modelo"], amb["cpus_disponiveis"], "CPU")

    linhas = []
    for teste, tamanho, threads in PLANO:
        for l in LINGUAGENS:
            url = (f"{base}/api/benchmark?teste={teste}&tamanho={tamanho}&threads={threads}"
                   f"&repeticoes={REPETICOES}&linguagens={l}")
            d = obter(url)
            m = d["linguagens"][l]["mediana"]
            print(f"{teste:8} {tamanho:>10} t={threads} {l:7} total={m['tempo_total_ms']:>9.1f} ms "
                  f"usr={m['cpu_usuario_ms']:>8.1f} sys={m['cpu_sistema_ms']:>7.1f} rss={m['memoria_max_kib']}")
            linhas.append({"teste": teste, "tamanho": tamanho, "threads": threads, "linguagem": l,
                           "repeticoes": REPETICOES, **{k: v for k, v in m.items() if k != "comando"}})
    with open(os.path.join(SAIDA, "dados.json"), "w", encoding="utf-8") as f:
        json.dump(linhas, f, ensure_ascii=False, indent=1)
    with open(os.path.join(SAIDA, "resultados.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)


# ------------------------------------------------------------------ gráficos
def graficos():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(os.path.join(SAIDA, "dados.json"), encoding="utf-8") as f:
        dados = json.load(f)

    plt.rcParams.update({
        "font.family": "Times New Roman", "font.size": 10, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#888", "axes.grid": True,
        "grid.color": "#e3e3e3", "grid.linewidth": .6, "axes.axisbelow": True,
        "legend.frameon": False, "savefig.dpi": 200, "savefig.bbox": "tight",
    })

    def sel(teste, tamanho=None, threads=None, l=None):
        return [d for d in dados if d["teste"] == teste
                and (tamanho is None or d["tamanho"] == tamanho)
                and (threads is None or d["threads"] == threads)
                and (l is None or d["linguagem"] == l)]

    def padrao(teste, l):
        t = 4 if teste != "threads" else 4
        return sel(teste, PADRAO[teste], t, l)[0]

    testes = ["cpu", "memoria", "io", "threads"]
    rot = {"cpu": "CPU\n(n = 2 milhões)", "memoria": "Memória\n(128 MiB)",
           "io": "E/S\n(32 MiB)", "threads": "Threads\n(n = 10 mi, 4 threads)"}

    # Fig 1: tempo total por teste (escala log)
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    larg = .26
    for i, l in enumerate(LINGUAGENS):
        xs = [k + (i - 1) * (larg + .02) for k in range(len(testes))]
        ys = [padrao(t, l)["tempo_total_ms"] for t in testes]
        barras = ax.bar(xs, ys, larg, color=CORES[l], label=NOMES[l])
        for b, y in zip(barras, ys):
            ax.annotate(f"{y:.0f}" if y >= 10 else f"{y:.1f}", (b.get_x() + b.get_width() / 2, y),
                        ha="center", va="bottom", fontsize=7.5, xytext=(0, 1.5), textcoords="offset points")
    ax.set_yscale("log")
    ax.set_xticks(range(len(testes)), [rot[t] for t in testes])
    ax.set_ylabel("tempo total (ms, escala log)")
    ax.legend(ncol=3, loc="upper left")
    fig.savefig(os.path.join(SAIDA, "fig_tempo_total.png"))
    plt.close(fig)

    # Fig 2: CPU usuário x kernel (barras empilhadas, um painel por teste)
    fig, eixos = plt.subplots(1, 4, figsize=(6.6, 2.7))
    for ax, t in zip(eixos, testes):
        for i, l in enumerate(LINGUAGENS):
            m = padrao(t, l)
            ax.bar(i, m["cpu_usuario_ms"], .7, color=CORES[l], edgecolor="white", linewidth=1)
            ax.bar(i, m["cpu_sistema_ms"], .7, bottom=m["cpu_usuario_ms"], color="white",
                   edgecolor=CORES[l], hatch="////", linewidth=1)
        ax.set_xticks(range(3), [NOMES[l] for l in LINGUAGENS], fontsize=8)
        ax.set_title(rot[t].replace("\n", " ").split(" (")[0], fontsize=10)
        ax.tick_params(axis="y", labelsize=8)
    eixos[0].set_ylabel("tempo de CPU (ms)")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor="#555", label="modo usuário (ru_utime)"),
                        Patch(facecolor="white", edgecolor="#555", hatch="////", label="modo kernel (ru_stime)")],
               ncol=2, loc="lower center", bbox_to_anchor=(.5, -.06))
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(os.path.join(SAIDA, "fig_cpu_usuario_kernel.png"))
    plt.close(fig)

    # Fig 3: escalonamento com o tamanho (cpu e io)
    fig, eixos = plt.subplots(1, 2, figsize=(6.4, 2.8))
    for ax, t, xl in [(eixos[0], "cpu", "n (crivo)"), (eixos[1], "io", "MiB gravados e lidos")]:
        for l in LINGUAGENS:
            pts = sorted((d["tamanho"], d["tempo_total_ms"]) for d in sel(t, threads=4, l=l))
            ax.plot(*zip(*pts), marker="o", markersize=4, linewidth=2, color=CORES[l], label=NOMES[l])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(xl)
        ax.set_title("CPU" if t == "cpu" else "E/S", fontsize=10)
    eixos[0].set_ylabel("tempo total (ms)")
    eixos[0].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "fig_escala.png"))
    plt.close(fig)

    # Fig 4: threads (tempo total e trocas de contexto involuntárias)
    fig, eixos = plt.subplots(1, 2, figsize=(6.4, 2.8))
    for l in LINGUAGENS:
        pts = sorted((d["threads"], d["tempo_total_ms"], d["cpu_usuario_ms"] + d["cpu_sistema_ms"])
                     for d in sel("threads", l=l))
        ts = [p[0] for p in pts]
        eixos[0].plot(ts, [p[1] for p in pts], marker="o", markersize=4, linewidth=2, color=CORES[l], label=NOMES[l])
        eixos[1].plot(ts, [p[2] / p[1] for p in pts], marker="o", markersize=4, linewidth=2, color=CORES[l])
    eixos[0].set_yscale("log")
    eixos[0].set_ylabel("tempo total (ms, log)")
    eixos[1].set_ylabel("CPU / tempo de parede")
    eixos[1].axhline(1, color="#888", linewidth=.8, linestyle="--")
    for ax in eixos:
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8], ["1", "2", "4", "8"])
        ax.set_xlabel("threads")
    eixos[0].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "fig_threads.png"))
    plt.close(fig)

    # Fig 5: memória - page faults x MiB alocados
    fig, eixos = plt.subplots(1, 2, figsize=(6.4, 2.8))
    for l in LINGUAGENS:
        pts = sorted((d["tamanho"], d["page_faults_menores"], d["memoria_max_kib"] / 1024)
                     for d in sel("memoria", threads=4, l=l))
        xs = [p[0] for p in pts]
        eixos[0].plot(xs, [p[1] for p in pts], marker="o", markersize=4, linewidth=2, color=CORES[l], label=NOMES[l])
        eixos[1].plot(xs, [p[2] for p in pts], marker="o", markersize=4, linewidth=2, color=CORES[l])
    eixos[0].plot([32, 512], [32 * 256, 512 * 256], color="#888", linestyle="--", linewidth=.8,
                  label="1 por página (MiB × 256)")
    eixos[0].set_ylabel("page faults menores")
    eixos[1].set_ylabel("pico de memória (MiB)")
    for ax in eixos:
        ax.set_xscale("log", base=2)
        ax.set_yscale("log", base=2)
        ax.set_xlabel("MiB alocados")
    eixos[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(SAIDA, "fig_memoria.png"))
    plt.close(fig)
    print("gráficos gerados em", SAIDA)


if __name__ == "__main__":
    if "--graficos" not in sys.argv:
        if len(sys.argv) < 2:
            raise SystemExit(__doc__)
        coletar(sys.argv[1].rstrip("/"))
    graficos()
