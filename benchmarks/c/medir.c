/*
 * medir.c - executa um programa e informa o que o kernel contabilizou para ele,
 * no estilo do /usr/bin/time.
 *
 * Uso: medir <programa> [argumentos...]
 *
 * Faz fork(), execvp() e wait4(); a saida do programa medido passa direto e,
 * em seguida, medir escreve uma linha JSON com o struct rusage do filho.
 *
 * Por que nao fazer isso direto no servidor Python? No Linux, o ru_maxrss de um
 * filho comeca com o pico de memoria do processo que fez o fork (o kernel
 * guarda o "hiwater" do espaco de enderecamento antigo na hora do exec). Um
 * servidor Python de ~28 MiB contaminaria a memoria de todos os testes. Como
 * medir e um binario estatico minusculo, o filho dele parte de quase zero.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double ms(struct timeval t) { return t.tv_sec * 1000.0 + t.tv_usec / 1000.0; }

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "uso: %s <programa> [argumentos...]\n", argv[0]);
        return 2;
    }
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 1; }
    if (pid == 0) {
        execvp(argv[1], argv + 1);
        perror("execvp");
        _exit(127);
    }

    int status;
    struct rusage u;
    if (wait4(pid, &status, 0, &u) < 0) { perror("wait4"); return 1; }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double parede = (t1.tv_sec - t0.tv_sec) * 1000.0 + (t1.tv_nsec - t0.tv_nsec) / 1e6;
    int codigo = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);

    fflush(stdout);
    printf("{\"medir\": true, \"pid\": %d, \"codigo\": %d, \"tempo_total_ms\": %.3f, "
           "\"cpu_usuario_ms\": %.3f, \"cpu_sistema_ms\": %.3f, \"memoria_max_kib\": %ld, "
           "\"page_faults_menores\": %ld, \"page_faults_maiores\": %ld, "
           "\"trocas_voluntarias\": %ld, \"trocas_involuntarias\": %ld}\n",
           (int)pid, codigo, parede, ms(u.ru_utime), ms(u.ru_stime), u.ru_maxrss,
           u.ru_minflt, u.ru_majflt, u.ru_nvcsw, u.ru_nivcsw);
    return codigo;
}
