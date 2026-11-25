# C, Rust e Python vistos pelo kernel

Trabalho final de Sistemas Operacionais, Engenharia de Software, FUCAPI, 2026.

**Equipe:** Antonio Arthur Cruz Sá Freitas, Wesley Horquen da Silva, Pedro Sérgio
Fernandes e Luis Gustavo Rocha Corrêa. **Professor:** Erick Farias.

O mesmo algoritmo em C, Rust e Python roda como processo filho no Linux de uma
função serverless do Vercel. O kernel informa, via `wait4()`/`struct rusage`, o tempo
de CPU em modo usuário e kernel, o pico de memória, os page faults e as trocas de contexto.

**Experimento ao vivo:** https://so-c-rust-python.vercel.app
(abrir com `#executar` no fim da URL já dispara o teste)

## Estrutura

| Caminho | O que é |
|---|---|
| `public/` | Página web (HTML, CSS e JS puros) |
| `api/benchmark.py`, `api/ambiente.py` | Funções Python do Vercel |
| `api/_executor.py` | Núcleo: roda cada linguagem sob o `medir` e calcula medianas |
| `benchmarks/c/bench.c`, `benchmarks/rust/src/main.rs`, `benchmarks/python/bench.py` | Os 4 testes (cpu, memoria, io, threads) em cada linguagem |
| `benchmarks/c/medir.c` | Medidor: `fork` + `execvp` + `wait4`, imprime o `rusage` em JSON |
| `bin/` | Binários Linux x86-64 estáticos (gerados por `build.sh`) |
| `scripts/coletar.py` | Coleta os dados na API publicada e gera os gráficos em `resultados/` |
| `scripts/local.sh` | Sobe tudo localmente em Docker (plano B sem internet), em http://localhost:8000 |
| `gerar_pdf.py` | Gera o artigo `Artigo_SO_C_Rust_Python.pdf` (ABNT) a partir de `resultados/` |
| `guia/` | Guia do projeto final |

## Comandos

```sh
sh build.sh                                              # recompila bin/ (Docker)
sh scripts/local.sh                                      # roda localmente
npx vercel deploy --prod                                 # publica
python scripts/coletar.py https://so-c-rust-python.vercel.app   # coleta dados + gráficos
python gerar_pdf.py                                      # gera o artigo (reportlab, pypdf)
```

Uso direto da API:
`/api/benchmark?teste=cpu&tamanho=2000000&repeticoes=3&threads=4&linguagens=c,rust,python`
