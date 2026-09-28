# Demonstração: processos × threads × eventos sob sobrecarga

Código de apoio ao trabalho de Sistemas Operacionais. O mesmo "serviço" (responder
`ok` a uma requisição HTTP depois de 50 ms de espera de E/S e 1 ms de CPU) é
implementado de três formas. A única diferença entre elas é **como o SO é usado**:

| Modelo      | Como funciona                                  | Parecido com            |
|-------------|------------------------------------------------|-------------------------|
| `processos` | pool fixo de 8 processos; cada um atende 1 conexão por vez | Apache *prefork*, PHP-FPM |
| `threads`   | uma thread do SO por conexão                   | Apache *worker*, Tomcat clássico |
| `eventos`   | um único processo com laço de eventos (`asyncio`) | Nginx, Node.js          |

## Como rodar

```bash
pip install -r requirements.txt
python executar_demo.py            # experimento completo (~2 min)
python executar_demo.py --rapido   # versão curta para mostrar ao vivo (~40 s)
```

Os resultados vão para `resultados/`:
`resultados.csv`, `grafico_vazao.png`, `grafico_latencia_p99.png`,
`grafico_memoria.png` e `grafico_erros.png`.

Para testar um servidor isolado, em dois terminais:

```bash
python servidores.py threads --porta 8082
python gerador_carga.py --porta 8082 --clientes 200 --duracao 6
```

## Arquivos

- `servidores.py`: os três servidores. As constantes no topo (`TRABALHO_IO_MS`,
  `TRABALHO_CPU_MS`, `NUM_PROCESSOS`) mudam o cenário.
- `gerador_carga.py`: simula N clientes simultâneos e mede vazão, latência
  (média, p50, p99) e erros (requisições que passam de 5 s).
- `executar_demo.py`: roda tudo, mede memória, threads e processos do servidor
  com `psutil` e gera o CSV e os gráficos.

## Roteiro para a apresentação

1. **Processos (pool fixo).** A vazão trava em cerca de 8 ÷ 0,051 s ≈ 150 req/s.
   Quando há mais clientes que processos, eles esperam na fila do kernel
   (*backlog*). A latência p99 salta para segundos e, com 250 ou mais clientes,
   boa parte das requisições dá *timeout*. É o **colapso por sobrecarga**. Esse
   modelo também gasta mais memória: 9 processos Python, cada um com o próprio
   espaço de endereçamento.
2. **Threads.** Esse modelo escala a vazão enquanto há CPU, porque uma thread
   bloqueada em E/S libera o processador. O número de threads do SO cresce junto
   com o número de clientes (504 threads com 500 clientes). A partir de cerca de
   100 clientes, o escalonador e o GIL do Python viram gargalo e o p99 dispara:
   uma thread "azarada" espera muito tempo.
3. **Eventos.** Esse modelo usa um número fixo de threads (5) e pouca memória por
   conexão. A vazão chega perto da vazão das threads e o p99 fica mais baixo e
   previsível, porque o laço atende as conexões em ordem. O ponto fraco é que
   **qualquer trecho de CPU bloqueia todos os clientes** (`gastar_cpu` dentro do
   laço).

**Mensagem principal.** Sob sobrecarga, o modelo de execução decide *quem espera
e onde*: na fila do kernel (processos), no escalonador (threads) ou na fila do
laço de eventos. Isso muda a latência de cauda e o consumo de recursos, mesmo
quando a vazão média é parecida.

## Limitações (citadas no trabalho)

- O cliente e o servidor rodam na mesma máquina e disputam a CPU.
- Python tem GIL, então threads não executam código Python em paralelo. Em C,
  Go, Java ou Rust os números mudam.
- O trabalho é sintético (espera fixa + CPU fixa) e o experimento usa a pilha
  TCP do Windows ou do Linux sem ajuste fino.
