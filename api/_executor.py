"""
Nucleo do experimento: executa cada linguagem como um processo filho e pede ao
kernel (wait4 -> struct rusage) a conta de recursos que aquele processo gastou.

Este arquivo comeca com "_" para que o Vercel nao o transforme em funcao; ele e
importado por benchmark.py e ambiente.py (e por scripts/servidor_local.py).
"""

import json
import os
import platform
import shutil
import statistics
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(RAIZ, "bin")
BENCH_PY = os.path.join(RAIZ, "benchmarks", "python", "bench.py")
TMP_BIN = "/tmp/bench_bin"

# Limites para cada chamada caber no tempo maximo da funcao serverless.
TESTES = {
    "cpu":     {"rotulo": "CPU (crivo de Eratóstenes)", "unidade": "n",
                "padrao": 2_000_000, "minimo": 1_000, "maximo": 10_000_000},
    "memoria": {"rotulo": "Memória (alocar e tocar páginas)", "unidade": "MiB",
                "padrao": 128, "minimo": 1, "maximo": 512},
    "io":      {"rotulo": "E/S (read/write em blocos de 4 KiB)", "unidade": "MiB",
                "padrao": 32, "minimo": 1, "maximo": 128},
    "threads": {"rotulo": "Threads (soma paralela)", "unidade": "n",
                "padrao": 10_000_000, "minimo": 1_000, "maximo": 20_000_000},
}
LINGUAGENS = ["c", "rust", "python"]
MAX_REPETICOES = 5
MAX_THREADS = 16


def _preparar_binario(nome):
    """Copia o binario para /tmp e marca como executavel.

    No Vercel o pacote da funcao e somente leitura e o bit de execucao pode
    se perder (repositorio editado no Windows); /tmp e gravavel.
    """
    origem = os.path.join(BIN, nome)
    if os.access(origem, os.X_OK):
        return origem
    os.makedirs(TMP_BIN, exist_ok=True)
    destino = os.path.join(TMP_BIN, nome)
    if not os.path.exists(destino):
        shutil.copy(origem, destino)
        os.chmod(destino, 0o755)
    return destino


def comando(linguagem, teste, tamanho, threads):
    args = [teste, str(tamanho), str(threads)]
    if linguagem == "python":
        return [sys.executable, BENCH_PY] + args
    return [_preparar_binario(f"bench_{linguagem}")] + args


def executar(linguagem, teste, tamanho, threads):
    """Roda o teste sob o bin/medir (fork + execvp + wait4, em C).

    medir imprime primeiro a linha JSON do proprio teste e depois uma linha
    JSON com o struct rusage que o kernel devolveu no wait4. Ver medir.c para
    o motivo de nao chamar wait4 direto daqui (ru_maxrss herdado no fork).
    """
    cmd = comando(linguagem, teste, tamanho, threads)
    proc = subprocess.run([_preparar_binario("medir")] + cmd, capture_output=True,
                          text=True, timeout=55)
    linhas = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    if proc.returncode != 0 or len(linhas) < 2:
        raise RuntimeError(f"{linguagem} terminou com código {proc.returncode}: "
                           f"{proc.stderr.strip()[:300]}")
    programa, medida = json.loads(linhas[-2]), json.loads(linhas[-1])
    return {
        "pid": medida["pid"],
        "comando": " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)),
        "resultado": programa["resultado"],
        "tempo_interno_ms": programa["tempo_interno_ms"],
        **{m: medida[m] for m in ("tempo_total_ms", "cpu_usuario_ms", "cpu_sistema_ms",
                                  "memoria_max_kib", "page_faults_menores",
                                  "page_faults_maiores", "trocas_voluntarias",
                                  "trocas_involuntarias")},
    }


METRICAS = ["tempo_interno_ms", "tempo_total_ms", "cpu_usuario_ms", "cpu_sistema_ms",
            "memoria_max_kib", "page_faults_menores", "page_faults_maiores",
            "trocas_voluntarias", "trocas_involuntarias"]


def validar(teste, tamanho, repeticoes, threads):
    if teste not in TESTES:
        raise ValueError(f"teste inválido: {teste}")
    lim = TESTES[teste]
    tamanho = lim["padrao"] if tamanho is None else int(tamanho)
    tamanho = max(lim["minimo"], min(lim["maximo"], tamanho))
    repeticoes = max(1, min(MAX_REPETICOES, int(repeticoes or 3)))
    threads = max(1, min(MAX_THREADS, int(threads or 4)))
    return tamanho, repeticoes, threads


def comparar(teste, tamanho=None, repeticoes=3, threads=4, linguagens=None):
    """Roda as linguagens intercaladas (c, rust, python, c, rust, ...) e devolve
    a mediana de cada metrica, alem de todas as execucoes individuais."""
    tamanho, repeticoes, threads = validar(teste, tamanho, repeticoes, threads)
    linguagens = [l for l in (linguagens or LINGUAGENS) if l in LINGUAGENS]
    execucoes = {l: [] for l in linguagens}
    for _ in range(repeticoes):
        for l in linguagens:
            execucoes[l].append(executar(l, teste, tamanho, threads))

    resultado = {}
    for l, runs in execucoes.items():
        mediana = {m: round(statistics.median(r[m] for r in runs), 3) for m in METRICAS}
        mediana["resultado"] = runs[0]["resultado"]
        mediana["comando"] = runs[0]["comando"]
        resultado[l] = {"mediana": mediana, "execucoes": runs}

    valores = {resultado[l]["mediana"]["resultado"] for l in resultado}
    return {
        "teste": teste,
        "descricao": TESTES[teste]["rotulo"],
        "tamanho": tamanho,
        "unidade": TESTES[teste]["unidade"],
        "threads": threads,
        "repeticoes": repeticoes,
        "resultados_conferem": len(valores) == 1,
        "linguagens": resultado,
    }


def _ler(caminho):
    try:
        with open(caminho) as f:
            return f.read()
    except OSError:
        return ""


def ambiente():
    """Descricao da maquina onde o experimento esta rodando."""
    os_release = dict(
        linha.split("=", 1) for linha in _ler("/etc/os-release").splitlines() if "=" in linha
    )
    cpuinfo = _ler("/proc/cpuinfo")
    modelo = next((l.split(":", 1)[1].strip() for l in cpuinfo.splitlines()
                   if l.startswith("model name")), platform.processor() or "desconhecido")
    meminfo = {l.split(":")[0]: l.split(":")[1].strip() for l in _ler("/proc/meminfo").splitlines()
               if ":" in l}
    u = platform.uname()
    try:
        cpus_permitidas = len(os.sched_getaffinity(0))
    except AttributeError:
        cpus_permitidas = os.cpu_count()

    def versao(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return ""

    return {
        "sistema": u.system,
        "kernel": u.release,
        "versao_kernel": u.version,
        "arquitetura": u.machine,
        "distribuicao": os_release.get("PRETTY_NAME", "").strip('"'),
        "cpu_modelo": modelo,
        "cpus_logicas": os.cpu_count(),
        "cpus_disponiveis": cpus_permitidas,
        "memoria_total": meminfo.get("MemTotal", ""),
        "python": platform.python_version(),
        "pid_funcao": os.getpid(),
        "vercel": bool(os.environ.get("VERCEL")),
        "regiao": os.environ.get("VERCEL_REGION", ""),
        "binarios": {
            "c": os.path.exists(os.path.join(BIN, "bench_c")),
            "medir": os.path.exists(os.path.join(BIN, "medir")),
            "rust": os.path.exists(os.path.join(BIN, "bench_rust")),
        },
        "testes": TESTES,
    }
