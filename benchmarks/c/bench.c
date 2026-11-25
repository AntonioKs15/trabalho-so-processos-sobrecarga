/*
 * bench.c - testes de desempenho em C (mesmos algoritmos de bench.py e main.rs).
 *
 * Uso: bench_c <teste> <tamanho> [threads]
 *   cpu      <n>      crivo de Eratostenes ate n; resultado = quantidade de primos
 *   memoria  <mb>     aloca mb MiB e escreve 1 byte por pagina de 4 KiB
 *   io       <mb>     escreve e le mb MiB em /tmp em blocos de 4 KiB (read/write)
 *   threads  <n> [t]  t threads somam (i*i) % 1000 para i em [0, n)
 *
 * Saida: uma linha JSON {"linguagem","teste","resultado","tempo_interno_ms"}.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define PAGINA 4096
#define BLOCO 4096
#define MIB (1024L * 1024L)

static double agora_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000.0 + t.tv_nsec / 1e6;
}

static uint64_t teste_cpu(long n) {
    char *primo = malloc(n + 1);
    if (!primo) { perror("malloc"); exit(1); }
    for (long i = 0; i <= n; i++) primo[i] = 1;
    primo[0] = 0;
    if (n >= 1) primo[1] = 0;
    for (long i = 2; i * i <= n; i++)
        if (primo[i])
            for (long j = i * i; j <= n; j += i) primo[j] = 0;
    uint64_t total = 0;
    for (long i = 0; i <= n; i++) total += primo[i];
    free(primo);
    return total;
}

static uint64_t teste_memoria(long mb) {
    long tamanho = mb * MIB;
    unsigned char *buf = malloc(tamanho);
    if (!buf) { perror("malloc"); exit(1); }
    long paginas = tamanho / PAGINA;
    for (long p = 0; p < paginas; p++) buf[p * PAGINA] = (unsigned char)(p & 0xff);
    uint64_t soma = 0;
    for (long p = 0; p < paginas; p++) soma += buf[p * PAGINA];
    free(buf);
    return soma;
}

static uint64_t teste_io(long mb) {
    char caminho[64];
    snprintf(caminho, sizeof caminho, "/tmp/bench_c_%d.dat", (int)getpid());
    unsigned char bloco[BLOCO];
    long blocos = mb * MIB / BLOCO;

    int fd = open(caminho, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("open"); exit(1); }
    for (long b = 0; b < blocos; b++) {
        memset(bloco, (int)(b & 0xff), BLOCO);
        if (write(fd, bloco, BLOCO) != BLOCO) { perror("write"); exit(1); }
    }
    close(fd);

    fd = open(caminho, O_RDONLY);
    if (fd < 0) { perror("open"); exit(1); }
    uint64_t soma = 0;
    ssize_t lidos;
    while ((lidos = read(fd, bloco, BLOCO)) > 0) soma += bloco[0];
    close(fd);
    unlink(caminho);
    return soma;
}

typedef struct { uint64_t inicio, fim, soma; } Faixa;

static void *trabalhar(void *arg) {
    Faixa *f = arg;
    uint64_t s = 0;
    for (uint64_t i = f->inicio; i < f->fim; i++) s += (i * i) % 1000;
    f->soma = s;
    return NULL;
}

static uint64_t teste_threads(long n, int t) {
    pthread_t ids[256];
    Faixa faixas[256];
    uint64_t passo = (uint64_t)n / t;
    for (int k = 0; k < t; k++) {
        faixas[k].inicio = k * passo;
        faixas[k].fim = (k == t - 1) ? (uint64_t)n : (k + 1) * passo;
        pthread_create(&ids[k], NULL, trabalhar, &faixas[k]);
    }
    uint64_t total = 0;
    for (int k = 0; k < t; k++) {
        pthread_join(ids[k], NULL);
        total += faixas[k].soma;
    }
    return total;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "uso: %s <cpu|memoria|io|threads> <tamanho> [threads]\n", argv[0]);
        return 2;
    }
    const char *teste = argv[1];
    long tamanho = atol(argv[2]);
    int t = argc > 3 ? atoi(argv[3]) : 4;
    if (t < 1) t = 1;
    if (t > 256) t = 256;

    double inicio = agora_ms();
    uint64_t r;
    if (!strcmp(teste, "cpu")) r = teste_cpu(tamanho);
    else if (!strcmp(teste, "memoria")) r = teste_memoria(tamanho);
    else if (!strcmp(teste, "io")) r = teste_io(tamanho);
    else if (!strcmp(teste, "threads")) r = teste_threads(tamanho, t);
    else { fprintf(stderr, "teste desconhecido: %s\n", teste); return 2; }
    double ms = agora_ms() - inicio;

    printf("{\"linguagem\": \"c\", \"teste\": \"%s\", \"resultado\": %llu, "
           "\"tempo_interno_ms\": %.3f}\n", teste, (unsigned long long)r, ms);
    return 0;
}
