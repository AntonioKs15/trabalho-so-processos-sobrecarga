"""
Gera o artigo em PDF no formato de artigo científico ABNT (NBR 6022, 6023 e 10520).

    python gerar_pdf.py          (requer reportlab; os dados vêm de resultados/)

Os números citados no texto são lidos de resultados/dados.json e
resultados/ambiente.json, gerados por scripts/coletar.py. Se a coleta for
refeita, basta rodar este script de novo.
"""

import json
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether,
                                PageTemplate, Paragraph, Preformatted, Spacer, Table,
                                TableStyle)

# ------------------------------------------------------------------ CAPA ----
CAPA = {
    "instituicao": "FUCAPI",
    "curso": "Engenharia de Software",
    "autores": ["Antonio Arthur Cruz Sá Freitas",
                "Wesley Horquen da Silva",
                "Pedro Sérgio Fernandes",
                "Luis Gustavo Rocha Corrêa"],
    "professor": "Erick Farias",
    "disciplina": "Sistemas Operacionais",
    "titulo": "C, RUST E PYTHON VISTOS PELO KERNEL",
    "subtitulo": "tempo, CPU, memória e chamadas de sistema medidos com wait4 em uma "
                 "função serverless",
    "cidade": "Manaus",
    "ano": "2026",
    "url": "https://so-c-rust-python.vercel.app",
}

AQUI = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = os.path.join(AQUI, "resultados")
SAIDA = os.path.join(AQUI, "Artigo_SO_C_Rust_Python.pdf")

with open(os.path.join(RESULTADOS, "dados.json"), encoding="utf-8") as f:
    DADOS = json.load(f)
with open(os.path.join(RESULTADOS, "ambiente.json"), encoding="utf-8") as f:
    AMB = json.load(f)

PADRAO = {"cpu": 2_000_000, "memoria": 128, "io": 32, "threads": 10_000_000}
LING = ["c", "rust", "python"]
NOME = {"c": "C", "rust": "Rust", "python": "Python"}


def d(teste, l, tamanho=None, threads=4):
    tamanho = PADRAO[teste] if tamanho is None else tamanho
    return next(x for x in DADOS if x["teste"] == teste and x["linguagem"] == l
                and x["tamanho"] == tamanho and x["threads"] == threads)


def n(v, casas=1):
    """Número no formato brasileiro."""
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def razao(teste, metrica="tempo_total_ms", a="python", b="c", **kw):
    return d(teste, a, **kw)[metrica] / d(teste, b, **kw)[metrica]


# ----------------------------------------------------------------- FONTES ---
FONTES = r"C:\Windows\Fonts"
for nome, arq in [("TNR", "times.ttf"), ("TNR-B", "timesbd.ttf"),
                  ("TNR-I", "timesi.ttf"), ("TNR-BI", "timesbi.ttf"),
                  ("COUR", "cour.ttf")]:
    pdfmetrics.registerFont(TTFont(nome, os.path.join(FONTES, arq)))
pdfmetrics.registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I",
                              boldItalic="TNR-BI")

# ---------------------------------------------------------------- ESTILOS ---
LARGURA, ALTURA = A4
MARG_ESQ, MARG_DIR, MARG_SUP, MARG_INF = 3 * cm, 2 * cm, 3 * cm, 2 * cm
UTIL = LARGURA - MARG_ESQ - MARG_DIR

CORPO = ParagraphStyle("corpo", fontName="TNR", fontSize=12, leading=18,
                       alignment=TA_JUSTIFY, firstLineIndent=1.25 * cm, spaceAfter=0)
CORPO_SEM_RECUO = ParagraphStyle("corpo0", parent=CORPO, firstLineIndent=0)
RESUMO = ParagraphStyle("resumo", parent=CORPO, fontSize=11, leading=13.5, firstLineIndent=0)
ITEM = ParagraphStyle("item", parent=CORPO, firstLineIndent=0, leftIndent=1.25 * cm,
                      bulletIndent=0.6 * cm)
CENTRO = ParagraphStyle("centro", parent=CORPO, alignment=TA_CENTER, firstLineIndent=0)
CENTRO_B = ParagraphStyle("centrob", parent=CENTRO, fontName="TNR-B", fontSize=14, leading=18)
AUTORES = ParagraphStyle("autores", parent=CENTRO, alignment=TA_RIGHT, fontSize=11, leading=14)
NOTA = ParagraphStyle("nota", fontName="TNR", fontSize=10, leading=12, alignment=TA_JUSTIFY)
H1 = ParagraphStyle("h1", fontName="TNR-B", fontSize=12, leading=18, spaceBefore=18,
                    spaceAfter=12, alignment=TA_LEFT)
H2 = ParagraphStyle("h2", parent=H1, fontName="TNR", spaceBefore=12, spaceAfter=6)
LEGENDA = ParagraphStyle("legenda", fontName="TNR", fontSize=10, leading=12,
                         alignment=TA_CENTER, spaceBefore=10, spaceAfter=4)
FONTE = ParagraphStyle("fonte", fontName="TNR", fontSize=10, leading=12,
                       alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
CELULA = ParagraphStyle("celula", fontName="TNR", fontSize=10, leading=12, alignment=TA_LEFT)
CELULA_C = ParagraphStyle("celulac", parent=CELULA, alignment=TA_CENTER)
REFERENCIA = ParagraphStyle("ref", fontName="TNR", fontSize=12, leading=13.5,
                            alignment=TA_LEFT, spaceAfter=9)
CODIGO = ParagraphStyle("codigo", fontName="COUR", fontSize=8.5, leading=10.5)

FONTE_AUTORES = f"Fonte: elaborado pelos autores ({CAPA['ano']})."


# ------------------------------------------------------------ AUXILIARES ----
class Titulo(Paragraph):
    """Título de seção que entra nos marcadores do PDF."""

    def __init__(self, texto, estilo, nivel):
        super().__init__(texto, estilo)
        self.nivel, self.texto_sumario = nivel, texto


def p(texto):
    return Paragraph(texto, CORPO)


def itens(lista):
    return [Paragraph(t, ITEM, bulletText="") for t in lista]


def secao(texto):
    return [CondPageBreak(3.5 * cm), Titulo(texto, H1, 0)]


def subsecao(texto):
    return [CondPageBreak(3 * cm), Titulo(texto, H2, 1)]


def tabela(numero, titulo, linhas, larguras, fonte=FONTE_AUTORES, alinhar_primeira=False):
    """Tabela ABNT/IBGE: dados numéricos, laterais abertas."""
    dados = []
    for i, linha in enumerate(linhas):
        estilo = ParagraphStyle("tc", parent=CELULA_C, fontName="TNR-B" if i == 0 else "TNR")
        dados.append([Paragraph(c, ParagraphStyle("tl", parent=estilo, alignment=TA_LEFT)
                                if (j == 0 and alinhar_primeira) else estilo)
                      for j, c in enumerate(linha)])
    t = Table(dados, colWidths=[w * UTIL for w in larguras], repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return [KeepTogether([Paragraph(f"Tabela {numero} – {titulo}", LEGENDA), t,
                          Paragraph(fonte, FONTE)])]


def figura(numero, titulo, arquivo, largura=0.8):
    img = Image(os.path.join(RESULTADOS, arquivo))
    escala = largura * UTIL / img.imageWidth
    img.drawWidth, img.drawHeight = img.imageWidth * escala, img.imageHeight * escala
    return [KeepTogether([Paragraph(f"Figura {numero} – {titulo}", LEGENDA), img,
                          Paragraph(FONTE_AUTORES + " Dados coletados em produção, mediana de "
                                    "5 execuções.", FONTE)])]


def codigo_fonte(numero, titulo, texto, arquivo):
    caixa = Table([[Preformatted(texto.strip("\n"), CODIGO)]], colWidths=[UTIL])
    caixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f2f2")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return [KeepTogether([Paragraph(f"Código {numero} – {titulo}", LEGENDA), caixa,
                          Paragraph(f"Fonte: elaborado pelos autores ({CAPA['ano']}), "
                                    f"arquivo <i>{arquivo}</i>.", FONTE)])]


# ---------------------------------------------------------- DOCUMENTO -------
class Documento(BaseDocTemplate):
    def __init__(self, arquivo):
        super().__init__(arquivo, pagesize=A4, leftMargin=MARG_ESQ, rightMargin=MARG_DIR,
                         topMargin=MARG_SUP, bottomMargin=MARG_INF,
                         title="C, Rust e Python vistos pelo kernel",
                         author="; ".join(CAPA["autores"]),
                         subject="Artigo de Sistemas Operacionais")
        frame = Frame(MARG_ESQ, MARG_INF, UTIL, ALTURA - MARG_SUP - MARG_INF, id="f",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate("txt", [frame], onPage=self.numerar)])

    @staticmethod
    def numerar(canvas, doc):
        canvas.setFont("TNR", 10)
        canvas.drawRightString(LARGURA - MARG_DIR, ALTURA - 2 * cm, str(doc.page))

    def afterFlowable(self, f):
        if isinstance(f, Titulo):
            chave = f"s{id(f)}"
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(f.texto_sumario, chave, f.nivel, closed=True)


# ============================================================================
#                                  CONTEÚDO
# ============================================================================
def cabecalho():
    c = CAPA
    autores = "<br/>".join(c["autores"])
    rodape = (f"Artigo apresentado à disciplina de {c['disciplina']} do curso de {c['curso']} "
              f"da {c['instituicao']}, professor {c['professor']}, {c['cidade']}, {c['ano']}. "
              f"Experimento disponível em {c['url']}.")
    resumo = (
        "Escolher uma linguagem de programação é, também, escolher como o programa vai usar o "
        "sistema operacional: quanto tempo passa em modo usuário e em modo kernel, quanta memória "
        "pede, quantas páginas toca e como suas threads são escalonadas. Este artigo compara C, "
        "Rust e Python executando os mesmos quatro algoritmos (processamento, alocação de memória, "
        "entrada e saída em arquivo e threads) como processos filhos de uma função serverless no "
        "Vercel, sobre Linux em uma microVM Firecracker. As medições não vêm de cronômetros dentro "
        "dos programas, e sim do próprio kernel, pela chamada de sistema <i>wait4</i>, que devolve "
        "a estrutura <i>rusage</i> de cada processo. Os resultados mostram que, em processamento "
        f"puro, o Python levou cerca de {n(razao('cpu'), 0)} vezes o tempo do C, enquanto C e Rust "
        "ficaram praticamente empatados; que em alocação de memória e em E/S a maior parte do tempo "
        "é gasta pelo kernel, resolvendo <i>page faults</i> e chamadas <i>read</i>/<i>write</i>, o "
        "que aproxima as três linguagens; e que o GIL do CPython impede que threads de Python "
        "aproveitem as duas CPUs disponíveis. A aplicação está publicada e pode ser executada "
        "ao vivo.")
    return [
        Paragraph(c["titulo"] + ":", CENTRO_B),
        Paragraph(c["subtitulo"], ParagraphStyle("st", parent=CENTRO, fontSize=13, leading=16)),
        Spacer(1, 16),
        Paragraph(autores, AUTORES),
        Spacer(1, 16),
        Paragraph("<b>Resumo:</b> " + resumo, RESUMO),
        Spacer(1, 8),
        Paragraph("<b>Palavras-chave:</b> chamadas de sistema; gerência de memória; "
                  "escalonamento; linguagens de programação; serverless.", RESUMO),
        Spacer(1, 10),
        Paragraph(rodape, NOTA),
    ]


# -------------------------------------------------------------- 1 INTRODUÇÃO
def introducao():
    s = secao("1 INTRODUÇÃO")
    s += [
        p("Todo programa, em qualquer linguagem, termina como um processo do sistema operacional "
          "(SO). É o SO que cria o processo, entrega a ele páginas de memória física, decide "
          "quando ele usa a CPU e executa, em seu nome, cada operação privilegiada, como ler um "
          "arquivo ou criar uma thread (TANENBAUM; BOS, 2016). A linguagem escolhida muda a forma "
          "desse diálogo: um programa em C ou Rust é traduzido antes da execução para instruções "
          "de máquina, enquanto um programa em Python é executado por um interpretador, que é ele "
          "próprio um processo com suas estruturas, sua memória e suas regras de concorrência."),
        p("Essa diferença costuma ser resumida como \"Python é lento\", o que é verdadeiro, mas "
          "incompleto. Para quem dimensiona servidores, paga por milissegundo em funções "
          "serverless ou desenvolve para sistemas embarcados, interessa saber <i>onde</i> o tempo "
          "é gasto: em código do usuário ou dentro do kernel, esperando ou calculando, com uma ou "
          "várias CPUs. Essas respostas o SO já possui, porque contabiliza os recursos de cada "
          "processo; basta perguntar."),
        p("O problema investigado é, portanto: <i>como C, Rust e Python diferem no uso dos "
          "recursos do sistema operacional (tempo de CPU em modo usuário e kernel, memória, "
          "page faults e trocas de contexto) ao executar o mesmo trabalho?</i> O objetivo geral é "
          "construir e publicar um experimento que responda a essa pergunta com dados do próprio "
          "kernel. Os objetivos específicos são:"),
    ]
    s += itens([
        "a) implementar os mesmos quatro testes (CPU, memória, E/S e threads) nas três linguagens, "
        "com verificação de que todas produzem o mesmo resultado;",
        "b) medir cada execução pela chamada de sistema <i>wait4</i>, sem depender de "
        "cronômetros internos;",
        "c) hospedar o experimento em uma plataforma serverless real (Vercel), acessível pelo "
        "navegador, para demonstração ao vivo;",
        "d) analisar os resultados à luz dos conceitos de processos, memória virtual, chamadas de "
        "sistema e escalonamento.",
    ])
    s += [p("O artigo está organizado assim: a Seção 2 apresenta os conceitos de SO envolvidos e "
            "as ferramentas; a Seção 3 descreve o experimento e analisa os resultados; e a Seção 4 "
            "traz as conclusões e onde o experimento pode ser aplicado.")]
    return s


# -------------------------------------------------------------- 2 CONTEXTO
def contexto():
    s = secao("2 CONTEXTO")
    s += subsecao("2.1 Processos, fork, exec e wait4")
    s += [
        p("No Linux, um novo programa nasce em duas etapas: <i>fork</i> duplica o processo "
          "chamador e <i>execve</i> substitui a imagem do filho pelo novo executável. Quando o filho "
          "termina, o pai o recolhe com uma das chamadas da família <i>wait</i>. A variante "
          "<i>wait4</i>, além do código de saída, preenche uma estrutura <i>struct rusage</i> com o "
          "que o kernel contabilizou para aquele processo: tempo de CPU em modo usuário "
          "(<i>ru_utime</i>) e em modo kernel (<i>ru_stime</i>), pico de memória residente "
          "(<i>ru_maxrss</i>), <i>page faults</i> menores e maiores (<i>ru_minflt</i>, "
          "<i>ru_majflt</i>) e trocas de contexto voluntárias e involuntárias (<i>ru_nvcsw</i>, "
          "<i>ru_nivcsw</i>) (KERRISK, 2010; LINUX MAN-PAGES, 2024). É o mesmo mecanismo usado "
          "pelo utilitário <i>/usr/bin/time</i>."),
    ]
    s += subsecao("2.2 Modo usuário, modo kernel e chamadas de sistema")
    s += [
        p("O processador alterna entre o modo usuário, em que roda o código do programa, e o modo "
          "kernel, em que roda o código do SO. A passagem acontece em chamadas de sistema (como "
          "<i>read</i> e <i>write</i>), em interrupções e em exceções, como o <i>page fault</i>. O "
          "tempo gasto no kernel em nome do processo aparece em <i>ru_stime</i>. Um programa que "
          "faz muitas chamadas de sistema pequenas, como gravar um arquivo em blocos de 4 KiB, "
          "acumula tempo de sistema independentemente da linguagem em que foi escrito "
          "(SILBERSCHATZ; GALVIN; GAGNE, 2015)."),
    ]
    s += subsecao("2.3 Memória virtual e page faults")
    s += [
        p("Quando um programa pede memória, o kernel apenas reserva endereços virtuais. A memória "
          "física é entregue sob demanda: no primeiro acesso a cada página de 4 KiB ocorre um "
          "<i>page fault</i> menor, e o kernel aloca e zera um quadro de memória e atualiza a "
          "tabela de páginas (BOVET; CESATI, 2005). Um <i>page fault</i> maior ocorre quando a "
          "página precisa ser lida do disco. Por isso, alocar 128 MiB e tocar cada página deve "
          "gerar cerca de 128 × 256 = 32.768 <i>page faults</i>, em qualquer linguagem."),
    ]
    s += subsecao("2.4 Threads, escalonamento e o GIL")
    s += [
        p("Threads são fluxos de execução que compartilham o espaço de endereçamento de um "
          "processo. No Linux, cada thread é uma tarefa escalonável, e o escalonador pode "
          "colocá-las em CPUs diferentes ao mesmo tempo. Nesse caso, a soma do tempo de CPU pode "
          "superar o tempo de parede. Em C (<i>pthreads</i>) e em Rust (<i>std::thread</i>) é o "
          "que acontece. No CPython, o interpretador de referência, existe o <i>Global "
          "Interpreter Lock</i> (GIL): apenas uma thread executa bytecode por vez, e as demais "
          "esperam pela trava (PYTHON SOFTWARE FOUNDATION, 2024). A PEP 703 propõe tornar o GIL "
          "opcional, mas ele continua ativo na versão padrão usada no experimento (GROSS, 2023)."),
    ]
    s += subsecao("2.5 Linguagens e plataforma")
    s += [
        p("C é compilado diretamente para código de máquina, com gerência manual de memória "
          "(KERNIGHAN; RITCHIE, 1988). Rust também é compilado para código nativo, mas garante "
          "segurança de memória em tempo de compilação, por meio do sistema de posse "
          "(<i>ownership</i>), sem coletor de lixo (KLABNIK; NICHOLS, 2023). Python é interpretado: "
          "o código-fonte é traduzido para bytecode e executado por uma máquina virtual, o que "
          "adiciona trabalho a cada operação. Pereira <i>et al.</i> (2017) mediram tempo, memória "
          "e energia de 27 linguagens e encontraram C e Rust entre as mais eficientes e Python "
          "entre as menos eficientes."),
        p("O experimento roda no Vercel, plataforma serverless em que cada função executa em "
          "Linux dentro de uma microVM. O ambiente da AWS em que essas funções rodam usa o "
          "Firecracker, um monitor de máquinas virtuais minimalista baseado em KVM (AGACHE "
          "<i>et al.</i>, 2020). A função é escrita em Python e cria os processos de teste. O "
          "Vercel não executa C e Rust diretamente, mas permite enviar binários junto com a "
          "função (VERCEL, 2026)."),
    ]
    return s


# ------------------------------------------------------------ 3 EXPERIMENTO
MEDIR = r"""
pid_t pid = fork();
if (pid == 0) {                       /* filho: vira o programa medido   */
    execvp(argv[1], argv + 1);
    _exit(127);
}
struct rusage u;
wait4(pid, &status, 0, &u);           /* pai: espera e recebe o rusage    */
printf("{\"cpu_usuario_ms\": %.3f, \"cpu_sistema_ms\": %.3f, "
       "\"memoria_max_kib\": %ld, \"page_faults_menores\": %ld, ...}\n",
       ms(u.ru_utime), ms(u.ru_stime), u.ru_maxrss, u.ru_minflt);
"""


def experimento():
    s = secao("3 EXPERIMENTO")
    s += subsecao("3.1 Arquitetura e metodologia")
    s += [
        p("A aplicação tem uma página web estática e duas funções Python no Vercel: "
          "<i>/api/ambiente</i>, que descreve a máquina (kernel, distribuição, CPU e memória), e "
          "<i>/api/benchmark</i>, que executa um teste nas três linguagens. Cada linguagem tem um "
          "programa com a mesma interface de linha de comando (<i>bench &lt;teste&gt; "
          "&lt;tamanho&gt; [threads]</i>) e os mesmos algoritmos:"),
    ]
    s += itens([
        "a) <b>CPU</b>: crivo de Eratóstenes até <i>n</i>; o resultado é a quantidade de primos;",
        "b) <b>memória</b>: aloca <i>N</i> MiB e escreve um byte em cada página de 4 KiB;",
        "c) <b>E/S</b>: grava e lê <i>N</i> MiB em <i>/tmp</i>, em blocos de 4 KiB, com "
        "<i>write</i> e <i>read</i> diretos, sem buffer da linguagem;",
        "d) <b>threads</b>: <i>t</i> threads dividem a soma de (<i>i</i>² mod 1000) para "
        "<i>i</i> de 0 a <i>n</i>.",
    ])
    s += [
        p("Os laços em Python foram escritos em Python puro, sem delegar o trabalho a funções da "
          "biblioteca implementadas em C, para medir o interpretador. Cada programa imprime o "
          "resultado, e a página confere se as três linguagens chegaram ao mesmo valor, o que "
          "garante que fizeram o mesmo trabalho."),
        p("A medição passa por um pequeno programa em C, <i>medir</i>, que faz <i>fork</i>, "
          "<i>execvp</i> e <i>wait4</i> (Código 1). Ele foi necessário por um detalhe do kernel "
          "descoberto durante o desenvolvimento: no <i>exec</i>, o Linux guarda o pico de memória "
          "do espaço de endereçamento anterior, de modo que o <i>ru_maxrss</i> de um filho criado "
          "diretamente pelo servidor Python (cerca de 28 MiB) começava com a memória do próprio "
          "servidor. Como <i>medir</i> é um binário estático de 39 KiB, o filho dele parte de "
          "quase zero."),
    ]
    s += codigo_fonte(1, "trecho central do medidor (fork, exec e wait4)", MEDIR,
                      "benchmarks/c/medir.c")
    s += [
        p("C e Rust foram compilados como binários estáticos para Linux x86-64 (musl), dentro de "
          "um contêiner Docker, e enviados ao Vercel junto com a função. O Python é o próprio "
          "interpretador da função. Cada configuração foi executada 5 vezes, e as figuras usam a "
          "mediana. O \"tempo total\" vai do <i>fork</i> ao retorno de <i>wait4</i> e inclui a "
          "carga do executável, portanto, para o Python, a inicialização do interpretador. A "
          "Tabela 1 resume o ambiente."),
    ]
    a = AMB
    s += tabela(1, "Ambiente de testes", [
        ["Item", "Valor"],
        ["Plataforma", f"Vercel Functions, região {a['regiao']} (Washington, EUA)"],
        ["Sistema operacional", a["distribuicao"]],
        ["Kernel", f"{a['sistema']} {a['kernel']}"],
        ["Processador", f"{a['cpu_modelo']}, {a['cpus_disponiveis']} vCPUs"],
        ["Memória visível", f"{n(int(a['memoria_total'].split()[0]) / 1024 / 1024, 2)} GiB"],
        ["Compiladores", "GCC 15.2 (-O2 -static), rustc 1.100 (--release, LTO), alvo musl"],
        ["Interpretador", f"CPython {a['python']}"],
    ], [0.3, 0.7], alinhar_primeira=True)

    s += subsecao("3.2 Execução")
    s += [
        p(f"O experimento está publicado em <i>{CAPA['url']}</i>. Na página, escolhe-se o teste, "
          "o tamanho, o número de threads e de repetições, e o botão executa as três linguagens "
          "em sequência. Para cada uma são exibidos o tempo total dividido em CPU de usuário e "
          "CPU de kernel, uma tabela com todas as métricas do <i>rusage</i> e um registro tipo "
          "terminal com o PID e os valores brutos de cada execução. Para coletar os dados deste "
          "artigo, o script <i>scripts/coletar.py</i> chamou a mesma API publicada com 16 "
          "configurações. Para uso sem internet, <i>scripts/local.sh</i> sobe a mesma aplicação "
          "em um contêiner Linux local."),
    ]

    s += subsecao("3.3 Resultados e análise")
    linhas = [["Teste", "Linguagem", "Total (ms)", "Usuário (ms)", "Kernel (ms)",
               "Memória (MiB)", "Page faults", "Trocas inv."]]
    rot = {"cpu": "CPU", "memoria": "Memória", "io": "E/S", "threads": "Threads"}
    for t in ["cpu", "memoria", "io", "threads"]:
        for l in LING:
            m = d(t, l)
            linhas.append([rot[t] if l == "c" else "", NOME[l], n(m["tempo_total_ms"]),
                           n(m["cpu_usuario_ms"]), n(m["cpu_sistema_ms"]),
                           n(m["memoria_max_kib"] / 1024), n(m["page_faults_menores"], 0),
                           n(m["trocas_involuntarias"], 0)])
    s += [p("A Tabela 2 reúne as medianas na configuração padrão de cada teste, e a Figura 1 "
            "compara o tempo total em escala logarítmica.")]
    s += tabela(2, "Métricas do kernel por teste (n = 2 milhões; 128 MiB; 32 MiB; n = 10 "
                   "milhões com 4 threads)", linhas,
                [0.11, 0.11, 0.12, 0.13, 0.12, 0.14, 0.14, 0.13])
    s += figura(1, "Tempo total por teste e linguagem (escala logarítmica)", "fig_tempo_total.png")

    cpu_c, cpu_r, cpu_p = d("cpu", "c"), d("cpu", "rust"), d("cpu", "python")
    s += [
        p(f"<b>CPU.</b> No crivo com <i>n</i> = 2 milhões, C levou {n(cpu_c['tempo_total_ms'])} ms, "
          f"Rust {n(cpu_r['tempo_total_ms'])} ms e Python {n(cpu_p['tempo_total_ms'])} ms, cerca de "
          f"{n(razao('cpu'), 0)} vezes mais. Quase todo esse tempo é de modo usuário (Figura 2): o "
          "programa só faz contas, e a diferença está no que cada instrução custa. Em C e Rust, "
          "marcar um múltiplo é uma instrução de máquina. Em Python, o interpretador busca o "
          "bytecode, verifica tipos e cria objetos inteiros a cada passo. A Figura 3 mostra que a "
          f"razão se mantém ao variar <i>n</i>: com 10 milhões, foram "
          f"{n(d('cpu', 'c', 10_000_000)['tempo_total_ms'])} ms em C contra "
          f"{n(d('cpu', 'python', 10_000_000)['tempo_total_ms'] / 1000, 2)} s em Python. A "
          "memória também difere: o processo Python tem cerca de "
          f"{n(cpu_p['memoria_max_kib'] / 1024, 0)} MiB de pico, quase tudo do próprio "
          f"interpretador, contra {n(cpu_c['memoria_max_kib'] / 1024)} MiB do C."),
    ]
    s += figura(2, "Tempo de CPU em modo usuário (sólido) e em modo kernel (hachurado)",
                "fig_cpu_usuario_kernel.png", largura=0.88)
    mem_c, mem_p = d("memoria", "c"), d("memoria", "python")
    s += [
        p(f"<b>Memória.</b> Ao alocar 128 MiB, as três linguagens geraram entre "
          f"{n(mem_c['page_faults_menores'], 0)} e {n(mem_p['page_faults_menores'], 0)} "
          "<i>page faults</i> menores, perto dos 32.768 previstos na Seção 2.3, e o tempo passou a "
          f"ser dominado pelo kernel: {n(mem_c['cpu_sistema_ms'])} ms de {n(mem_c['tempo_total_ms'])} "
          "ms no caso do C. Quem trabalha aqui é o SO, zerando e mapeando páginas, e por isso C e "
          "Rust empatam e o Python fica só "
          f"{n(razao('memoria'), 1)} vez mais lento. A Figura 4 mostra que <i>page faults</i> e "
          "memória residente crescem linearmente com o tamanho alocado, seguindo a regra de um "
          "<i>fault</i> por página, e que o Python soma um custo fixo de cerca de 10 MiB."),
    ]
    s += figura(3, "Escalabilidade com o tamanho da entrada: CPU e E/S (escalas logarítmicas)",
                "fig_escala.png")
    s += figura(4, "Page faults menores e pico de memória em função da memória alocada",
                "fig_memoria.png")
    io_c, io_p = d("io", "c"), d("io", "python")
    s += [
        p(f"<b>E/S.</b> Gravar e ler 32 MiB em blocos de 4 KiB significa {n(32 * 256 * 2, 0)} "
          f"chamadas de sistema. Em C, {n(io_c['cpu_sistema_ms'])} ms dos "
          f"{n(io_c['tempo_total_ms'])} ms foram tempo de kernel, e o Python gastou quase o mesmo "
          f"no kernel ({n(io_p['cpu_sistema_ms'])} ms). A diferença é o tempo de usuário entre "
          "uma chamada e outra, que no Python inclui criar um objeto <i>bytes</i> a cada bloco. Os "
          "dados ficam no <i>page cache</i>, de modo que não houve <i>page faults</i> maiores nem "
          "espera de disco. A lição prática é que, em programas limitados por chamadas de sistema, "
          "trocar de linguagem ajuda pouco; reduzir o número de chamadas, com blocos maiores ou "
          "buffers, ajuda muito mais."),
    ]
    t1c, t2c = d("threads", "c", threads=1), d("threads", "c", threads=2)
    t1p, t2p = d("threads", "python", threads=1), d("threads", "python", threads=2)
    s += [
        p(f"<b>Threads.</b> Com 2 vCPUs, passar de 1 para 2 threads reduziu o tempo do C de "
          f"{n(t1c['tempo_total_ms'])} para {n(t2c['tempo_total_ms'])} ms, e a razão entre CPU "
          f"consumida e tempo de parede chegou a "
          f"{n((t2c['cpu_usuario_ms'] + t2c['cpu_sistema_ms']) / t2c['tempo_total_ms'], 2)}: as "
          "duas threads rodaram de fato em paralelo (Figura 5). No Python, o tempo ficou em "
          f"{n(t1p['tempo_total_ms'] / 1000, 2)} s com 1 thread e {n(t2p['tempo_total_ms'] / 1000, 2)} s "
          "com 2, e a razão permaneceu em 1,0. As threads existem para o kernel, mas o GIL só "
          "deixa uma executar bytecode por vez. Com mais threads do que CPUs (4 e 8), C e Rust "
          "não melhoram, porque não há mais núcleos. A oscilação nessa faixa se deve à "
          "granularidade de cerca de 4 ms com que o kernel contabiliza o tempo de CPU, comparável "
          "à duração do teste."),
    ]
    s += figura(5, "Tempo total e razão CPU/tempo de parede em função do número de threads",
                "fig_threads.png")
    s += [
        p("<b>C contra Rust.</b> Em todos os testes as duas linguagens ficaram a poucos "
          "milissegundos uma da outra, dentro da variação entre execuções. O binário em Rust tem "
          "algumas centenas de KiB a mais de memória residente, pela biblioteca padrão maior, mas "
          "a segurança de memória do Rust não teve custo mensurável de desempenho nestes testes."),
    ]
    return s


# ------------------------------------------------------------- 4 CONCLUSÃO
def conclusao():
    s = secao("4 CONCLUSÃO")
    s += [
        p("O experimento mostrou que a diferença entre linguagens depende do recurso do SO que o "
          f"programa exercita. Em processamento puro, o Python foi cerca de {n(razao('cpu'), 0)} "
          f"vezes mais lento que C e Rust e, com threads, cerca de {n(razao('threads'), 0)} vezes, "
          "por causa do interpretador e do GIL. Em memória e E/S, a maior parte do trabalho é do "
          "kernel, e as linguagens ficaram a menos de 2 vezes umas das outras. C e Rust "
          "empataram. Mais do que \"qual linguagem é mais rápida\", as métricas do <i>rusage</i> "
          "mostram onde o tempo vai, e isso orienta a otimização certa."),
        p("Entre as dificuldades, destacam-se: executar C e Rust em uma plataforma que só oferece "
          "Python e Node.js, resolvido com binários estáticos compilados em Docker e copiados "
          "para <i>/tmp</i> com permissão de execução; a herança do pico de memória do processo "
          "pai no <i>ru_maxrss</i>, resolvida com o medidor em C; e a granularidade da "
          "contabilidade de CPU, que exige testes com duração bem maior que alguns milissegundos "
          "para comparações finas."),
        p("<b>Onde o experimento pode ser aplicado.</b> Em <i>infraestrutura serverless e "
          "nuvem</i>, em que se paga por tempo e memória de execução, as mesmas medidas indicam "
          "quais funções vale reescrever em linguagem compilada: as limitadas por CPU, e não as "
          "limitadas por E/S. Em <i>servidores corporativos</i>, o par <i>ru_utime</i>/"
          "<i>ru_stime</i> separa gargalos de aplicação de gargalos de kernel, como excesso de "
          "chamadas de sistema ou de <i>page faults</i>, e o medidor pode ser usado em pipelines "
          "de integração contínua para detectar regressões de desempenho. Em <i>sistemas "
          "embarcados</i>, os cerca de 10 MiB fixos do interpretador Python e seu tempo de "
          "inicialização pesam muito mais do que em um servidor, o que favorece C e Rust. No "
          "ensino, a página publicada permite a qualquer aluno ver o kernel trabalhar pelo "
          "navegador."),
        p("Como trabalhos futuros, propõem-se: incluir o CPython sem GIL (PEP 703) e o PyPy, que "
          "usa compilação JIT; medir energia; contar chamadas de sistema com <i>strace</i> ou "
          "eBPF, o que não é permitido dentro da microVM do Vercel; e comparar o custo de "
          "inicialização a frio (<i>cold start</i>) das funções em cada linguagem."),
    ]
    return s


def referencias():
    refs = [
        "AGACHE, A.; BROOKER, M.; IORDACHE, A.; LIGUORI, A.; NEUGEBAUER, R.; PIWONKA, P.; "
        "POPA, D.-M. Firecracker: lightweight virtualization for serverless applications. "
        "<i>In</i>: USENIX SYMPOSIUM ON NETWORKED SYSTEMS DESIGN AND IMPLEMENTATION, 17., 2020, "
        "Santa Clara. <b>Proceedings</b> [...]. Berkeley: USENIX Association, 2020. p. 419-434.",

        "BOVET, D. P.; CESATI, M. <b>Understanding the Linux kernel</b>. 3. ed. Sebastopol: "
        "O'Reilly, 2005.",

        "GROSS, S. <b>PEP 703</b>: making the global interpreter lock optional in CPython. "
        "[<i>S. l.</i>]: Python Software Foundation, 2023. Disponível em: "
        "https://peps.python.org/pep-0703/. Acesso em: 25 nov. 2026.",

        "KERNIGHAN, B. W.; RITCHIE, D. M. <b>The C programming language</b>. 2. ed. Englewood "
        "Cliffs: Prentice Hall, 1988.",

        "KERRISK, M. <b>The Linux programming interface</b>: a Linux and UNIX system "
        "programming handbook. San Francisco: No Starch Press, 2010.",

        "KLABNIK, S.; NICHOLS, C. <b>The Rust programming language</b>. 2. ed. San Francisco: "
        "No Starch Press, 2023.",

        "LINUX MAN-PAGES. <b>getrusage(2)</b> e <b>wait4(2)</b>: Linux programmer's manual. "
        "[<i>S. l.</i>], 2024. Disponível em: https://man7.org/linux/man-pages/man2/"
        "getrusage.2.html. Acesso em: 25 nov. 2026.",

        "PEREIRA, R.; COUTO, M.; RIBEIRO, F.; RUA, R.; CUNHA, J.; FERNANDES, J. P.; SARAIVA, J. "
        "Energy efficiency across programming languages: how do energy, time, and memory "
        "relate? <i>In</i>: ACM SIGPLAN INTERNATIONAL CONFERENCE ON SOFTWARE LANGUAGE "
        "ENGINEERING, 10., 2017, Vancouver. <b>Proceedings</b> [...]. New York: ACM, 2017. "
        "p. 256-267. DOI: 10.1145/3136014.3136031.",

        "PYTHON SOFTWARE FOUNDATION. <b>threading</b>: thread-based parallelism. Python 3.12 "
        "documentation. [<i>S. l.</i>], 2024. Disponível em: "
        "https://docs.python.org/3.12/library/threading.html. Acesso em: 25 nov. 2026.",

        "SILBERSCHATZ, A.; GALVIN, P. B.; GAGNE, G. <b>Fundamentos de sistemas "
        "operacionais</b>. 9. ed. Rio de Janeiro: LTC, 2015.",

        "TANENBAUM, A. S.; BOS, H. <b>Sistemas operacionais modernos</b>. 4. ed. São "
        "Paulo: Pearson, 2016.",

        "VERCEL. <b>Using the Python runtime with Vercel Functions</b>. [<i>S. l.</i>], 2026. "
        "Disponível em: https://vercel.com/docs/functions/runtimes/python. "
        "Acesso em: 25 nov. 2026.",
    ]
    s = [CondPageBreak(4 * cm), Titulo("REFERÊNCIAS", ParagraphStyle(
        "tref", parent=H1, alignment=TA_CENTER), 0)]
    s += [Paragraph(r, REFERENCIA) for r in refs]
    return s


def montar():
    doc = Documento(SAIDA)
    story = cabecalho() + introducao() + contexto() + experimento() + conclusao() + referencias()
    doc.build(story)
    from pypdf import PdfReader
    print(f"PDF gerado: {SAIDA} ({len(PdfReader(SAIDA).pages)} páginas)")


if __name__ == "__main__":
    montar()
