"""
Gera o trabalho em PDF no formato ABNT (NBR 14724, 6023 e 10520).

    python gerar_pdf.py

Para editar: preencha os campos [PREENCHER] em CAPA logo abaixo e altere o
texto nas funções de cada seção. Os gráficos vêm de codigo/resultados/.
"""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether,
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

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
    "titulo": "PROCESSOS, THREADS E EVENTOS SOB SOBRECARGA",
    "subtitulo": "pesquisa exploratória e revisão bibliográfica sobre modelos de "
                 "execução de servidores",
    "cidade": "Manaus",
    "ano": "2026",
}

AQUI = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = os.path.join(AQUI, "codigo", "resultados")
SAIDA = os.path.join(AQUI, "Trabalho_SO_Processos_Sobrecarga.pdf")

# ----------------------------------------------------------------- FONTES ---
FONTES = r"C:\Windows\Fonts"
for nome, arq in [("TNR", "times.ttf"), ("TNR-B", "timesbd.ttf"),
                  ("TNR-I", "timesi.ttf"), ("TNR-BI", "timesbi.ttf")]:
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
ITEM = ParagraphStyle("item", parent=CORPO, firstLineIndent=0, leftIndent=1.25 * cm,
                      bulletIndent=0.6 * cm)
CITACAO_LONGA = ParagraphStyle("citlonga", parent=CORPO, fontSize=10, leading=12,
                               leftIndent=4 * cm, firstLineIndent=0,
                               spaceBefore=12, spaceAfter=12)
CENTRO = ParagraphStyle("centro", parent=CORPO, alignment=TA_CENTER, firstLineIndent=0)
CENTRO_B = ParagraphStyle("centrob", parent=CENTRO, fontName="TNR-B")
H1 = ParagraphStyle("h1", fontName="TNR-B", fontSize=12, leading=18, spaceAfter=18,
                    alignment=TA_LEFT)
H2 = ParagraphStyle("h2", parent=H1, spaceBefore=18, spaceAfter=18)
H3 = ParagraphStyle("h3", parent=H1, fontName="TNR-BI", spaceBefore=12, spaceAfter=12)
TITULO_SEM_NUM = ParagraphStyle("tsn", parent=H1, alignment=TA_CENTER)
LEGENDA = ParagraphStyle("legenda", fontName="TNR", fontSize=10, leading=12,
                         alignment=TA_CENTER, spaceBefore=12, spaceAfter=4)
FONTE = ParagraphStyle("fonte", fontName="TNR", fontSize=10, leading=12,
                       alignment=TA_CENTER, spaceBefore=4, spaceAfter=12)
CELULA = ParagraphStyle("celula", fontName="TNR", fontSize=10, leading=12,
                        alignment=TA_LEFT)
CELULA_P = ParagraphStyle("celulap", parent=CELULA, fontSize=8.5, leading=10)
CELULA_C = ParagraphStyle("celulac", parent=CELULA, alignment=TA_CENTER)
REFERENCIA = ParagraphStyle("ref", fontName="TNR", fontSize=12, leading=14,
                            alignment=TA_LEFT, spaceAfter=14)
NATUREZA = ParagraphStyle("natureza", fontName="TNR", fontSize=11, leading=13,
                          alignment=TA_JUSTIFY, leftIndent=8 * cm)

FONTE_AUTORES = f"Fonte: elaborado pelos autores ({CAPA['ano']})."


# ------------------------------------------------------------ AUXILIARES ----
class Titulo(Paragraph):
    """Título que entra no sumário e nos marcadores do PDF."""

    def __init__(self, texto, estilo, nivel, no_sumario=True):
        super().__init__(texto, estilo)
        self.nivel, self.texto_sumario, self.no_sumario = nivel, texto, no_sumario


def p(texto):
    return Paragraph(texto, CORPO)


def p0(texto):
    return Paragraph(texto, CORPO_SEM_RECUO)


def itens(lista, marcador="•"):
    return [Paragraph(t, ITEM, bulletText=marcador) for t in lista]


def secao(texto):
    return [PageBreak(), Titulo(texto, H1, 0)]


def subsecao(texto):
    return [CondPageBreak(4 * cm), Titulo(texto, H2, 1)]


def subsubsecao(texto):
    return [CondPageBreak(3 * cm), Titulo(texto, H3, 2)]


def quadro(numero, titulo, linhas, larguras, cabecalho=True, pequeno=False,
           fonte=FONTE_AUTORES):
    """Quadro ABNT: conteúdo textual, grade fechada, título acima e fonte abaixo."""
    est = CELULA_P if pequeno else CELULA
    est_cab = ParagraphStyle("cab", parent=est, fontName="TNR-B", alignment=TA_CENTER)
    dados = []
    for i, linha in enumerate(linhas):
        e = est_cab if (cabecalho and i == 0) else est
        dados.append([c if not isinstance(c, str) else Paragraph(c, e) for c in linha])
    t = Table(dados, colWidths=[w * UTIL for w in larguras], repeatRows=1 if cabecalho else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.5, colors.black),
              ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if cabecalho:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")))
    t.setStyle(TableStyle(estilo))
    return [Paragraph(f"Quadro {numero} – {titulo}", LEGENDA), t,
            Paragraph(fonte, FONTE)]


def tabela(numero, titulo, linhas, larguras, fonte=FONTE_AUTORES):
    """Tabela ABNT/IBGE: dados numéricos, laterais abertas."""
    dados = [[Paragraph(c, ParagraphStyle("tc", parent=CELULA_C,
                                          fontName="TNR-B" if i == 0 else "TNR"))
              for c in linha] for i, linha in enumerate(linhas)]
    t = Table(dados, colWidths=[w * UTIL for w in larguras], repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return [KeepTogether([Paragraph(f"Tabela {numero} – {titulo}", LEGENDA), t,
                          Paragraph(fonte, FONTE)])]


def figura(numero, titulo, arquivo, largura=0.92):
    caminho = os.path.join(RESULTADOS, arquivo)
    img = Image(caminho)
    escala = largura * UTIL / img.imageWidth
    img.drawWidth, img.drawHeight = img.imageWidth * escala, img.imageHeight * escala
    return [KeepTogether([Paragraph(f"Figura {numero} – {titulo}", LEGENDA), img,
                          Paragraph(FONTE_AUTORES, FONTE)])]


def ficha(numero, referencia_curta, campos):
    linhas = [[f"<b>{k}</b>", v] for k, v in campos]
    return [KeepTogether(quadro(numero, f"Fichamento de {referencia_curta}", linhas, [0.22, 0.78],
                                cabecalho=False))]


# ---------------------------------------------------------- DOCUMENTO -------
class Documento(BaseDocTemplate):
    def __init__(self, arquivo):
        super().__init__(arquivo, pagesize=A4, leftMargin=MARG_ESQ, rightMargin=MARG_DIR,
                         topMargin=MARG_SUP, bottomMargin=MARG_INF,
                         title="Processos, threads e eventos sob sobrecarga",
                         author="; ".join(CAPA["autores"]),
                         subject="Trabalho de Sistemas Operacionais")
        frame = Frame(MARG_ESQ, MARG_INF, UTIL, ALTURA - MARG_SUP - MARG_INF, id="f",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate("pre", [frame]),
                               PageTemplate("txt", [frame], onPage=self.numerar)])

    @staticmethod
    def numerar(canvas, doc):
        # NBR 14724: páginas contadas a partir da folha de rosto (a capa não conta)
        # e numeradas a partir da primeira folha da parte textual.
        canvas.setFont("TNR", 10)
        canvas.drawRightString(LARGURA - MARG_DIR, ALTURA - 2 * cm, str(doc.page - 1))

    def afterFlowable(self, f):
        if isinstance(f, Titulo):
            chave = f"s{id(f)}"
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(f.texto_sumario, chave, f.nivel, closed=True)
            if f.no_sumario:
                self.notify("TOCEntry", (f.nivel, f.texto_sumario, self.page - 1, chave))


# ============================================================================
#                                  CONTEÚDO
# ============================================================================
def capa():
    c = CAPA
    topo = [Paragraph(c["instituicao"], CENTRO_B), Paragraph(c["curso"].upper(), CENTRO_B),
            Spacer(1, 30)] + [Paragraph(a.upper(), CENTRO) for a in c["autores"]]
    meio = [Paragraph(c["titulo"], CENTRO_B), Paragraph(c["subtitulo"], CENTRO)]
    base = [Paragraph(c["cidade"].upper(), CENTRO), Paragraph(c["ano"], CENTRO)]
    return [bloco_vertical(topo, meio, base), PageBreak()]


def folha_de_rosto():
    c = CAPA
    topo = [Paragraph(a.upper(), CENTRO) for a in c["autores"]]
    natureza = (f"Trabalho apresentado à disciplina de {c['disciplina']} do curso de "
                f"{c['curso']} da {c['instituicao']}, como requisito parcial de "
                f"avaliação (Fases 1 e 2: pesquisa exploratória e revisão bibliográfica).<br/><br/>"
                f"Professor(a): {c['professor']}")
    meio = [Paragraph(c["titulo"], CENTRO_B), Paragraph(c["subtitulo"], CENTRO),
            Spacer(1, 40), Paragraph(natureza, NATUREZA)]
    base = [Paragraph(c["cidade"].upper(), CENTRO), Paragraph(c["ano"], CENTRO)]
    return [bloco_vertical(topo, meio, base), PageBreak()]


def bloco_vertical(topo, meio, base):
    t = Table([[topo], [meio], [base]], colWidths=[UTIL],
              rowHeights=[7.5 * cm, 12.5 * cm, 4.5 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (0, 0), "TOP"),
                           ("VALIGN", (0, 1), (0, 1), "MIDDLE"),
                           ("VALIGN", (0, 2), (0, 2), "BOTTOM"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def resumo():
    texto = (
        "Servidores de Internet precisam atender milhares de clientes simultâneos e, "
        "quando a demanda supera a capacidade, entram em sobrecarga: as filas crescem, a "
        "latência aumenta e o serviço pode colapsar. A forma como o servidor usa as "
        "abstrações do sistema operacional (processos, threads ou um laço de eventos) "
        "influencia diretamente esse comportamento. Este trabalho apresenta as Fases 1 e "
        "2 de uma pesquisa sobre o tema. Na Fase 1, realizou-se um levantamento de temas "
        "atuais em Sistemas Operacionais, a identificação de problemas em aberto e uma "
        "busca em bases acadêmicas (Google Acadêmico, ACM Digital Library, IEEE Xplore, "
        "anais da USENIX e arXiv), que resultou em 14 trabalhos pré-selecionados, dos "
        "quais oito foram fichados. Na Fase 2, os trabalhos foram comparados quanto a "
        "métodos, tecnologias, ambientes, métricas e resultados. Observou-se que as "
        "comparações clássicas entre arquiteturas medem principalmente a vazão em "
        "máquinas dedicadas, enquanto os trabalhos recentes priorizam a latência de cauda "
        "em ambientes compartilhados. A lacuna identificada é a ausência, entre os "
        "trabalhos analisados, de uma avaliação comparativa dos três modelos sob "
        "sobrecarga em contêineres com cotas de CPU, considerando latência de cauda, "
        "memória e taxa de erros. Uma demonstração prática em Python ilustra as "
        "diferenças entre os modelos.")
    return [Paragraph("RESUMO", TITULO_SEM_NUM), p0(texto), Spacer(1, 18),
            p0("<b>Palavras-chave:</b> sistemas operacionais; servidores; processos; "
               "threads; sobrecarga."), PageBreak()]


def sumario():
    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [
        ParagraphStyle("t0", fontName="TNR-B", fontSize=12, leading=18, leftIndent=0,
                       firstLineIndent=0),
        ParagraphStyle("t1", fontName="TNR", fontSize=12, leading=18, leftIndent=0,
                       firstLineIndent=0),
        ParagraphStyle("t2", fontName="TNR-I", fontSize=12, leading=18, leftIndent=0,
                       firstLineIndent=0),
    ]
    return [Paragraph("SUMÁRIO", TITULO_SEM_NUM), toc, NextPageTemplate("txt")]


# -------------------------------------------------------------- 1 INTRODUÇÃO
def introducao():
    s = secao("1 INTRODUÇÃO")
    s += [
        p("Servidores web, APIs e microsserviços atendem, a todo momento, milhares de "
          "requisições simultâneas. Para isso, dependem de abstrações fornecidas pelo "
          "sistema operacional (SO): <i>processos</i>, que isolam espaços de endereçamento; "
          "<i>threads</i>, que compartilham memória dentro de um processo; e mecanismos de "
          "entrada e saída (E/S) que permitem a um único fluxo de execução acompanhar "
          "várias conexões, base dos servidores <i>orientados a eventos</i> "
          "(TANENBAUM; BOS, 2016; SILBERSCHATZ; GALVIN; GAGNE, 2015)."),
        p("Quando a demanda excede a capacidade do servidor, ocorre a <i>sobrecarga</i> "
          "(<i>overload</i>). Nessa situação as filas crescem, o tempo de resposta aumenta "
          "e, no limite, o serviço entra em colapso, gastando recursos com requisições que "
          "já não serão aproveitadas (WELSH; CULLER; BREWER, 2001). A maneira como o "
          "servidor organiza sua execução (um processo por conexão, uma thread por "
          "conexão ou um laço de eventos) define onde essas filas se formam, quanto de "
          "memória e CPU é consumido e quão previsível é a latência."),
        p("O debate sobre qual modelo é mais adequado existe há mais de duas décadas. "
          "Servidores orientados a eventos foram propostos como alternativa mais "
          "eficiente aos baseados em processos (PAI; DRUSCHEL; ZWAENEPOEL, 1999), outros "
          "autores defenderam que threads bem implementadas seriam equivalentes "
          "(VON BEHREN; CONDIT; BREWER, 2003) e comparações cuidadosas chegaram a "
          "conclusões diferentes (PARIAG <i>et al.</i>, 2007; HARJI; BUHR; BRECHT, 2012). "
          "Com a adoção de microsserviços, contêineres e nuvem, o problema ganhou novas "
          "dimensões: latência de cauda, controle de admissão e compartilhamento de CPU "
          "entre aplicações (ZHOU <i>et al.</i>, 2018; CHO <i>et al.</i>, 2020; "
          "JEFFERY; JENSEN; MORTIER, 2024)."),
        p("Diante disso, este trabalho parte da seguinte pergunta de pesquisa: <i>como os "
          "modelos de servidor baseados em processos, threads e eventos se comportam, em "
          "desempenho e consumo de recursos, quando o servidor está sobrecarregado?</i>"),
        p("O objetivo geral é realizar uma pesquisa exploratória e uma revisão "
          "bibliográfica sobre esse tema, identificando o estado da arte e uma lacuna "
          "científica. Os objetivos específicos são:"),
    ]
    s += itens(["a) levantar temas relevantes em Sistemas Operacionais e problemas atuais;",
                "b) buscar, selecionar e fichar artigos científicos sobre o tema;",
                "c) comparar as abordagens existentes quanto a métodos, tecnologias, "
                "ambientes, métricas e resultados;",
                "d) identificar lacunas e escolher uma para investigação futura;",
                "e) ilustrar o problema com uma demonstração prática em código."],
               marcador="")
    s += [p("O trabalho está organizado da seguinte forma: a Seção 2 apresenta a Fase 1 "
            "(pesquisa exploratória); a Seção 3 apresenta a Fase 2 (revisão bibliográfica "
            "e lacuna); a Seção 4 descreve a demonstração prática; e a Seção 5 traz as "
            "considerações finais.")]
    return s


# ------------------------------------------------------------------ 2 FASE 1
def fase1():
    s = secao("2 FASE 1 – PESQUISA EXPLORATÓRIA")
    s += [p("Esta seção descreve o levantamento de temas, a identificação dos problemas "
            "atuais, o protocolo de busca de artigos e a leitura analítica (fichamento) "
            "dos trabalhos selecionados.")]

    # 2.1
    s += subsecao("2.1 Levantamento de temas relevantes em Sistemas Operacionais")
    s += [p("A equipe explorou diferentes áreas de Sistemas Operacionais para identificar "
            "temas com relevância acadêmica e tecnológica. O Quadro 1 resume as áreas "
            "consideradas, exemplos de problemas discutidos atualmente e a relação de cada "
            "uma com o conteúdo da disciplina.")]
    s += quadro(1, "Áreas de Sistemas Operacionais consideradas no levantamento", [
        ["Área", "Exemplos de temas atuais", "Relação com a disciplina"],
        ["Escalonamento de CPU",
         "Escalonamento em escala de microssegundos para reduzir a latência de cauda "
         "(KAFFES <i>et al.</i>, 2019); realocação rápida de núcleos entre aplicações "
         "(OUSTERHOUT <i>et al.</i>, 2019; FRIED <i>et al.</i>, 2020); novo escalonador "
         "EEVDF no Linux 6.6.",
         "Políticas de escalonamento, preempção, troca de contexto."],
        ["Gerência de memória",
         "Memória em camadas, páginas grandes, consumo de memória por processo e por "
         "conexão em servidores.",
         "Memória virtual, paginação, espaço de endereçamento."],
        ["Entrada e saída",
         "Novas interfaces de E/S assíncrona no Linux, como o io_uring "
         "(DIDONA <i>et al.</i>, 2022; JASNY <i>et al.</i>, 2025).",
         "E/S bloqueante × não bloqueante, chamadas de sistema."],
        ["Virtualização e contêineres",
         "Isolamento de recursos com cgroups e cotas de CPU; interferência entre "
         "aplicações vizinhas (JEFFERY; JENSEN; MORTIER, 2024).",
         "Proteção, isolamento, compartilhamento de recursos."],
        ["Concorrência em servidores",
         "Processos × threads × eventos; controle de sobrecarga e de admissão "
         "(PARIAG <i>et al.</i>, 2007; CHO <i>et al.</i>, 2020).",
         "Processos, threads, sincronização, filas."],
    ], [0.22, 0.48, 0.30])
    s += [p("O tema escolhido foi <b>concorrência em servidores sob sobrecarga</b>, com o "
            "recorte na comparação entre os modelos de execução baseados em processos, "
            "threads e eventos. A escolha se justifica por três motivos: (i) o tema reúne "
            "vários conteúdos centrais da disciplina (processos, threads, escalonamento e "
            "E/S); (ii) possui literatura consolidada e, ao mesmo tempo, pesquisa ativa "
            "recente; e (iii) permite uma demonstração prática simples, sem necessidade de "
            "hardware especializado.")]

    # 2.2
    s += subsecao("2.2 Identificação de problemas atuais")
    s += [p("A partir da leitura exploratória, foram identificados os seguintes problemas "
            "e desafios discutidos na literatura recente:")]
    s += itens([
        "<b>Colapso sob sobrecarga.</b> Quando a demanda ultrapassa a capacidade, "
        "servidores sem controle de admissão podem entrar em colapso de congestionamento. "
        "Cho <i>et al.</i> (2020) mostram que, com a demanda a 1,4 vez a capacidade, "
        "esquemas anteriores levam de 500 ms (DAGOR) a 1,58 s (SEDA) para se recuperar.",
        "<b>Latência de cauda.</b> Em arquiteturas de microsserviços, uma requisição do "
        "usuário depende de muitas chamadas internas, e a lentidão de poucas respostas "
        "(percentil 99, ou p99) domina o tempo total (ZHOU <i>et al.</i>, 2018; "
        "CHO <i>et al.</i>, 2020).",
        "<b>Custo de recursos por conexão.</b> Modelos com um processo ou uma thread por "
        "conexão consomem memória e geram trocas de contexto. Modelos de eventos evitam "
        "esse custo, mas qualquer operação bloqueante paralisa o laço inteiro "
        "(PAI; DRUSCHEL; ZWAENEPOEL, 1999; VON BEHREN; CONDIT; BREWER, 2003).",
        "<b>Sobrecomprometimento de CPU em contêineres.</b> Muitos ambientes de execução "
        "criam threads de acordo com o número de CPUs da máquina e ignoram as cotas "
        "impostas por cgroups, o que eleva a latência de cauda (JEFFERY; JENSEN; "
        "MORTIER, 2024).",
        "<b>Novas interfaces de E/S.</b> O io_uring promete reduzir o custo das chamadas "
        "de sistema, mas o ganho depende de como é usado (DIDONA <i>et al.</i>, 2022; "
        "JASNY <i>et al.</i>, 2025).",
    ])
    s += [p("Assim, respondendo à questão proposta na Fase 1, <b>o problema investigado "
            "atualmente</b> é: <i>como organizar a execução concorrente de um servidor "
            "(processos, threads ou eventos) e controlar a entrada de trabalho para que ele "
            "mantenha vazão e latência de cauda previsíveis quando a demanda excede a "
            "capacidade, especialmente em ambientes compartilhados como contêineres e "
            "nuvem</i>.")]

    # 2.3
    s += subsecao("2.3 Busca de artigos científicos")
    s += subsubsecao("2.3.1 Bases utilizadas")
    s += [p("As buscas foram realizadas em setembro de 2026 nas seguintes bases: "
            "<b>Google Acadêmico</b>, como base de ampla cobertura; <b>ACM Digital "
            "Library</b>, com os anais de SOSP, EuroSys, SoCC e SYSTOR; <b>IEEE "
            "Xplore</b>, com os anais do ANCS; <b>anais da USENIX</b> (OSDI, NSDI, ATC e "
            "HotOS); e <b>arXiv</b>, para trabalhos recentes ainda em processo de "
            "publicação.")]
    s += subsubsecao("2.3.2 Palavras-chave")
    s += [p("Foram usadas palavras-chave em inglês, idioma predominante da área, "
            "combinadas com operadores booleanos, além de termos em português para "
            "localizar material introdutório. O Quadro 2 apresenta as expressões "
            "utilizadas.")]
    s += quadro(2, "Expressões de busca utilizadas", [
        ["Expressão de busca", "Objetivo"],
        ['"web server architecture" AND (threads OR events OR processes)',
         "Comparações entre modelos de execução"],
        ['"event-driven" AND "thread-per-connection" AND performance',
         "Debate threads × eventos"],
        ['"overload control" AND (server OR microservices OR RPC)',
         "Controle de sobrecarga e admissão"],
        ['"tail latency" AND (scheduling OR threads OR "thread-per-core")',
         "Latência de cauda e escalonamento"],
        ['(cgroups OR "CPU quota") AND threads AND latency',
         "Efeito de contêineres e cotas"],
        ['io_uring AND (epoll OR performance)', "Novas interfaces de E/S"],
        ['"arquitetura de servidores web" OR "sobrecarga em servidores"',
         "Material em português"],
    ], [0.62, 0.38])
    s += subsubsecao("2.3.3 Período de publicação")
    s += [p("Adotou-se o período de <b>1999 a 2026</b>. Trabalhos de 1999 a 2012 foram "
            "mantidos como <i>fundamentação</i>, pois são as comparações clássicas entre "
            "arquiteturas, ainda citadas pelos trabalhos atuais. Para o <i>estado da "
            "arte</i>, priorizou-se o intervalo de <b>2018 a 2026</b>.")]
    s += subsubsecao("2.3.4 Critérios de seleção")
    s += [p("Após a leitura de título e resumo, aplicaram-se os critérios abaixo.")]
    s += itens([
        "<b>I1</b> – tratar de modelos de concorrência de servidores, controle de "
        "sobrecarga ou latência de cauda em servidores;",
        "<b>I2</b> – apresentar avaliação experimental com métricas quantitativas "
        "(exceto artigos de posição de grande influência);",
        "<b>I3</b> – ser publicado em conferência ou periódico com revisão por pares, ou "
        "ser um <i>preprint</i> recente de grupo de pesquisa identificável;",
        "<b>I4</b> – ter texto completo acessível;",
        "<b>E1</b> (exclusão) – foco exclusivo em armazenamento ou banco de dados, sem "
        "relação com o atendimento de requisições;",
        "<b>E2</b> (exclusão) – depender de hardware ou SO especializado (por exemplo, "
        "desvio do kernel) sem comparação com modelos convencionais. Esses trabalhos "
        "foram usados apenas como contexto do estado da arte;",
        "<b>E3</b> (exclusão) – textos sem metodologia descrita, como comparativos "
        "comerciais entre Apache e Nginx publicados em blogs de provedores de hospedagem.",
    ], marcador="")
    s += subsubsecao("2.3.5 Artigos encontrados")
    s += [p("O Quadro 3 lista os 14 trabalhos pré-selecionados após a triagem por título "
            "e resumo, com a indicação de quais foram escolhidos para fichamento e quais "
            "foram mantidos como contexto.")]
    s += quadro(3, "Trabalhos encontrados e situação após aplicação dos critérios", [
        ["Nº", "Trabalho", "Ano", "Veículo", "Situação"],
        ["1", "Flash: an efficient and portable web server (PAI; DRUSCHEL; ZWAENEPOEL)",
         "1999", "USENIX ATC", "Contexto (fundamentação)"],
        ["2", "SEDA: an architecture for well-conditioned, scalable internet services "
              "(WELSH; CULLER; BREWER)", "2001", "SOSP", "<b>Selecionado</b>"],
        ["3", "Why events are a bad idea (VON BEHREN; CONDIT; BREWER)", "2003",
         "HotOS", "<b>Selecionado</b>"],
        ["4", "Comparing the performance of web server architectures "
              "(PARIAG <i>et al.</i>)", "2007", "EuroSys", "<b>Selecionado</b>"],
        ["5", "Comparing high-performance multi-core web-server architectures "
              "(HARJI; BUHR; BRECHT)", "2012", "SYSTOR", "<b>Selecionado</b>"],
        ["6", "Overload control for scaling WeChat microservices (ZHOU <i>et al.</i>)",
         "2018", "SoCC", "<b>Selecionado</b>"],
        ["7", "Shinjuku: preemptive scheduling for µsecond-scale tail latency "
              "(KAFFES <i>et al.</i>)", "2019", "NSDI", "Contexto (E2)"],
        ["8", "Shenango: achieving high CPU efficiency for latency-sensitive datacenter "
              "workloads (OUSTERHOUT <i>et al.</i>)", "2019", "NSDI", "Contexto (E2)"],
        ["9", "The impact of thread-per-core architecture on application tail latency "
              "(ENBERG; RAO; TARKOMA)", "2019", "ANCS", "<b>Selecionado</b>"],
        ["10", "Overload control for µs-scale RPCs with Breakwater (CHO <i>et al.</i>)",
         "2020", "OSDI", "<b>Selecionado</b>"],
        ["11", "Caladan: mitigating interference at microsecond timescales "
               "(FRIED <i>et al.</i>)", "2020", "OSDI", "Contexto (E2)"],
        ["12", "Understanding modern storage APIs: libaio, SPDK and io_uring "
               "(DIDONA <i>et al.</i>)", "2022", "SYSTOR", "Contexto (E1)"],
        ["13", "Reducing tail latencies through environment- and neighbour-aware thread "
               "management (JEFFERY; JENSEN; MORTIER)", "2024", "arXiv",
         "<b>Selecionado</b>"],
        ["14", "High-performance DBMSs with io_uring: when and how to use it "
               "(JASNY <i>et al.</i>)", "2025", "arXiv", "Contexto (E1)"],
    ], [0.06, 0.53, 0.08, 0.13, 0.20])
    s += [p("Também foram encontrados comparativos de desempenho entre Apache e Nginx em "
            "sites de empresas de hospedagem. Eles foram descartados pelo critério E3, "
            "pois não descrevem ambiente, carga nem método de medição.")]

    # 2.4
    s += subsecao("2.4 Leitura e análise dos trabalhos")
    s += [p("Para cada trabalho selecionado, a equipe identificou o problema investigado, "
            "o objetivo, a metodologia, os resultados, as limitações e os possíveis "
            "trabalhos futuros. Quando uma limitação ou um trabalho futuro não é "
            "declarado pelos próprios autores, o texto indica que se trata de uma "
            "observação da equipe. Os fichamentos estão nos Quadros 4 a 11.")]
    fichas = [
        ("Welsh, Culler e Brewer (2001)", [
            ("Problema", "Serviços de Internet sofrem picos de carga muito acima da média. "
             "Servidores com uma thread ou um processo por requisição degradam sob carga "
             "alta e não têm mecanismo para se manter estáveis."),
            ("Objetivo", "Propor a SEDA (<i>Staged Event-Driven Architecture</i>), na qual o "
             "serviço é dividido em estágios orientados a eventos, ligados por filas "
             "explícitas, com controladores dinâmicos de recursos."),
            ("Metodologia", "Implementação em Java (plataforma Sandstorm) de um servidor "
             "web (Haboob) e de outros serviços; comparação com Apache (processos) e Flash "
             "(eventos) sob número crescente de clientes, medindo vazão, tempo de resposta "
             "e justiça entre clientes."),
            ("Resultados", "O Haboob manteve vazão comparável ou superior e distribuição "
             "de tempos de resposta mais justa. Os controladores de admissão limitaram a "
             "latência sob sobrecarga ao rejeitar requisições excedentes."),
            ("Limitações", "Custo adicional das filas entre estágios e necessidade de "
             "ajustar os controladores. Estudos posteriores mostraram que o Haboob não "
             "competiu bem com servidores otimizados (PARIAG <i>et al.</i>, 2007)."),
            ("Trabalhos futuros", "Aplicar o modelo a outros serviços e obter do SO "
             "mais informações e controle sobre o uso de recursos."),
        ]),
        ("von Behren, Condit e Brewer (2003)", [
            ("Problema", "Havia um consenso de que servidores orientados a eventos seriam "
             "superiores às threads para alta concorrência."),
            ("Objetivo", "Argumentar que threads podem oferecer as mesmas vantagens dos "
             "eventos, com um modelo de programação mais simples."),
            ("Metodologia", "Análise conceitual da dualidade entre threads e eventos e "
             "implementação de uma biblioteca de threads em nível de usuário (Capriccio), "
             "usada em um servidor web (Knot) comparado ao Haboob (SEDA)."),
            ("Resultados", "A biblioteca escalou até 100.000 threads e o servidor obteve "
             "desempenho igual ou superior ao Haboob. Os autores atribuem o mau desempenho "
             "das threads a implementações inadequadas, e não ao modelo."),
            ("Limitações", "Artigo de posição (<i>workshop</i>), com avaliação curta. "
             "Segundo Pariag <i>et al.</i> (2007), o Capriccio não suportava "
             "multiprocessadores."),
            ("Trabalhos futuros", "Apoio do compilador para threads (análise do uso de "
             "pilha e detecção de condições de corrida) e integração com o SO."),
        ]),
        ("Pariag <i>et al.</i> (2007)", [
            ("Problema", "Os estudos anteriores chegavam a conclusões divergentes sobre "
             "qual arquitetura de servidor tem melhor desempenho."),
            ("Objetivo", "Comparar, com ajuste cuidadoso, três arquiteturas: orientada a "
             "eventos (µserver), uma thread por conexão (Knot/Capriccio) e híbrida em "
             "<i>pipeline</i> (WatPipe)."),
            ("Metodologia", "Servidor com um Xeon de 3,06 GHz em modo uniprocessador, "
             "2 GB de RAM e Linux 2.6.16; quatro máquinas clientes; carga estática "
             "inspirada no SPECweb99, gerada com httperf para permitir sobrecarga; "
             "variações com <i>sendfile</i> bloqueante e não bloqueante."),
            ("Resultados", "O µserver (eventos) e o WatPipe (<i>pipeline</i>) obtiveram "
             "cerca de 18% mais vazão que a melhor versão do Knot (threads). O ajuste do "
             "número de conexões e de threads ou processos foi decisivo."),
            ("Limitações", "Um único núcleo de CPU, apenas conteúdo estático e dependência "
             "de ajuste manual (observação da equipe)."),
            ("Trabalhos futuros", "Os autores citam cargas com mais e menos acesso a disco "
             "e servidores capazes de se ajustar automaticamente à carga."),
        ]),
        ("Harji, Buhr e Brecht (2012)", [
            ("Problema", "Entender como arquitetura e implementação afetam o desempenho de "
             "servidores web em processadores com vários núcleos."),
            ("Objetivo", "Comparar as arquiteturas N-cópias, orientada a eventos e em "
             "<i>pipeline</i> em 4 núcleos, usando nginx, lighttpd e Apache como "
             "referência."),
            ("Metodologia", "Duas cargas de conteúdo estático, uma atendida pela cache do "
             "sistema de arquivos e outra com E/S de disco intensa; métricas de vazão "
             "(Mbps) e conexões por segundo."),
            ("Resultados", "Vazão de 4.000 a 6.000 Mbps com 40 mil a 70 mil conexões por "
             "segundo, acima de nginx, lighttpd e Apache. A diferença entre as melhores "
             "versões de cada arquitetura ficou em até 10%. Os autores concluem que a "
             "implementação e o ajuste importam mais que a arquitetura."),
            ("Limitações", "Apenas conteúdo estático e 4 núcleos. Não mede latência de "
             "cauda nem avalia virtualização (observação da equipe)."),
            ("Trabalhos futuros", "Os autores apontam o uso de muitos núcleos, execução em "
             "máquinas virtuais e a restrição de servidores a subconjuntos de núcleos."),
        ]),
        ("Zhou <i>et al.</i> (2018)", [
            ("Problema", "Em um sistema de grande escala com microsserviços (WeChat), o "
             "controle de sobrecarga feito separadamente por serviço prejudica o sistema "
             "como um todo."),
            ("Objetivo", "Propor o DAGOR, um controle de sobrecarga independente da lógica "
             "de cada serviço e colaborativo entre serviços."),
            ("Metodologia", "Detecção de sobrecarga pelo tempo de espera na fila e "
             "admissão por prioridades em dois níveis (negócio e usuário); implantação em "
             "produção no WeChat e experimentos que medem a taxa de sucesso e a justiça."),
            ("Resultados", "Alta taxa de sucesso mesmo sob sobrecarga, com justiça entre "
             "requisições. O sistema está em produção há mais de cinco anos."),
            ("Limitações", "Projetado para a arquitetura do WeChat e com parâmetros "
             "definidos empiricamente. Cho <i>et al.</i> (2020) mostram que ele demora "
             "cerca de 500 ms para se recuperar em serviços de microssegundos."),
            ("Trabalhos futuros", "Os autores sugerem aplicar os princípios de projeto a "
             "outros sistemas de microsserviços."),
        ]),
        ("Enberg, Rao e Tarkoma (2019)", [
            ("Problema", "A arquitetura <i>thread-per-core</i> reduz os custos de "
             "sincronização e de interação com o SO, mas seu efeito na latência de cauda "
             "ainda não havia sido medido."),
            ("Objetivo", "Medir o impacto da arquitetura <i>thread-per-core</i> na latência "
             "de cauda de aplicações."),
            ("Metodologia", "Implementação de um armazenamento chave-valor com "
             "particionamento em nível de aplicação e troca de mensagens entre threads, "
             "comparado ao Memcached em hardware comum."),
            ("Resultados", "Latência de cauda até 71% menor que a do Memcached."),
            ("Limitações", "Avalia um único tipo de aplicação. Cargas desbalanceadas podem "
             "concentrar trabalho em um núcleo (observação da equipe)."),
            ("Trabalhos futuros", "Avaliar a arquitetura em servidores web e em cenários "
             "com cotas de CPU (sugestão da equipe)."),
        ]),
        ("Cho <i>et al.</i> (2020)", [
            ("Problema", "Manter vazão e latência de cauda sob sobrecarga em chamadas "
             "remotas (RPC) com tempo de serviço de microssegundos."),
            ("Objetivo", "Propor o Breakwater, um controle de sobrecarga conduzido pelo "
             "servidor."),
            ("Metodologia", "O servidor emite créditos com base no atraso de fila, usa "
             "especulação de demanda e descarte ativo de requisições; implementação sobre "
             "o Shenango; comparação com DAGOR e SEDA por vazão útil, latência de cauda e "
             "tempo de convergência."),
            ("Resultados", "Com a demanda a 1,4 vez a capacidade, o sistema estabiliza em "
             "menos de 20 ms, sem colapso. DAGOR e SEDA levam 500 ms e 1,58 s para se "
             "recuperar."),
            ("Limitações", "Depende de um ambiente de execução de baixa latência "
             "(Shenango) e da alteração do protocolo RPC (observação da equipe)."),
            ("Trabalhos futuros", "Avaliar a abordagem em serviços com tempos de serviço "
             "maiores e em pilhas convencionais do Linux (sugestão da equipe)."),
        ]),
        ("Jeffery, Jensen e Mortier (2024)", [
            ("Problema", "O excesso de threads do SO em relação à CPU disponível eleva a "
             "latência de cauda. As causas são a detecção incorreta do número de CPUs "
             "sob cotas (cgroups) e o desconhecimento do uso de CPU pelas aplicações "
             "vizinhas."),
            ("Objetivo", "Analisar como as linguagens detectam as CPUs disponíveis e "
             "propor o <i>friendlypool</i>, um conjunto de threads que considera o uso "
             "de CPU dos vizinhos."),
            ("Metodologia", "Levantamento de ambientes de execução (Go, threads virtuais "
             "Java, Rust/Tokio, entre outros) quanto ao suporte a cgroups; experimentos em "
             "Linux 6.2 com dois processadores Xeon Silver 4112, aplicações em cgroups "
             "com cotas; medição da latência máxima e da vazão."),
            ("Resultados", "O <i>friendlypool</i> reduz a latência máxima dos "
             "<i>workers</i> em até 6,7 vezes, com perda de vazão de até 1,4 vez, "
             "ajustável por um fator de sobrecomprometimento."),
            ("Limitações", "É um <i>preprint</i>, os experimentos usam uma única máquina "
             "e há troca entre latência e vazão."),
            ("Trabalhos futuros", "Os autores propõem uma interface unificada, "
             "independente de linguagem, para obter o número de CPUs disponíveis."),
        ]),
    ]
    for i, (ref, campos) in enumerate(fichas, start=4):
        s += ficha(i, ref, campos)
    return s


# ------------------------------------------------------------------ 3 FASE 2
def fase2():
    s = secao("3 FASE 2 – REVISÃO BIBLIOGRÁFICA")

    s += subsecao("3.1 Seleção dos trabalhos mais relevantes")
    s += [p("Dos 14 trabalhos encontrados, os oito fichados foram considerados os mais "
            "diretamente relacionados ao problema e organizados em três eixos:")]
    s += itens([
        "<b>Eixo A – Comparação de arquiteturas:</b> von Behren, Condit e Brewer (2003), "
        "Pariag <i>et al.</i> (2007) e Harji, Buhr e Brecht (2012). Respondem "
        "diretamente à pergunta de pesquisa;",
        "<b>Eixo B – Controle de sobrecarga:</b> Welsh, Culler e Brewer (2001), Zhou "
        "<i>et al.</i> (2018) e Cho <i>et al.</i> (2020). Tratam do comportamento quando a "
        "demanda excede a capacidade;",
        "<b>Eixo C – Threads, núcleos e ambientes compartilhados:</b> Enberg, Rao e "
        "Tarkoma (2019) e Jeffery, Jensen e Mortier (2024). Tratam da relação entre o "
        "número de threads, os núcleos e a latência de cauda.",
    ], marcador="")

    s += subsecao("3.2 Estado da arte")
    s += [p("A literatura mostra uma evolução em quatro momentos."),
          p("<b>(1) Um processo ou uma thread por conexão.</b> É o modelo clássico do "
            "Apache no modo <i>prefork</i>. É simples e isola as conexões, mas cada "
            "conexão ocupa memória e gera trocas de contexto. Quando o número máximo de "
            "processos é atingido, as novas conexões esperam na fila do kernel e o tempo "
            "de resposta fica irregular (WELSH; CULLER; BREWER, 2001)."),
          p("<b>(2) Servidores orientados a eventos.</b> Um único processo acompanha "
            "muitas conexões por meio de chamadas como <i>select</i> e <i>epoll</i>. O "
            "Flash (PAI; DRUSCHEL; ZWAENEPOEL, 1999) mostrou o ganho dessa abordagem e "
            "também seu ponto fraco: operações bloqueantes, como a leitura de disco, "
            "paralisam o laço e exigem processos auxiliares."),
          p("<b>(3) O debate entre threads e eventos e os modelos híbridos.</b> A SEDA "
            "propôs estágios de eventos com filas e controle de admissão; von Behren, "
            "Condit e Brewer (2003) defenderam threads leves. As comparações mais "
            "cuidadosas (PARIAG <i>et al.</i>, 2007; HARJI; BUHR; BRECHT, 2012) mostram "
            "que, quando bem ajustadas, as arquiteturas ficam a 10% a 18% umas das outras "
            "em vazão. A implementação e o ajuste pesam tanto quanto o modelo."),
          p("<b>(4) De 2018 até hoje: latência de cauda e ambientes compartilhados.</b> O "
            "foco passou da vazão média para o p99 e para o comportamento sob sobrecarga "
            "em microsserviços. As linhas atuais incluem controle de admissão (ZHOU "
            "<i>et al.</i>, 2018; CHO <i>et al.</i>, 2020), escalonamento e realocação de "
            "núcleos em microssegundos (KAFFES <i>et al.</i>, 2019; OUSTERHOUT <i>et al.</i>, "
            "2019; FRIED <i>et al.</i>, 2020), a arquitetura <i>thread-per-core</i> "
            "(ENBERG; RAO; TARKOMA, 2019), o respeito às cotas de CPU de contêineres "
            "(JEFFERY; JENSEN; MORTIER, 2024) e novas interfaces de E/S como o io_uring "
            "(DIDONA <i>et al.</i>, 2022; JASNY <i>et al.</i>, 2025)."),
          p("Em síntese, o estado da arte indica que não existe um modelo universalmente "
            "superior. Sob sobrecarga, o que diferencia os modelos é <i>onde a espera "
            "acontece</i> (na fila do kernel, no escalonador de threads ou na fila do laço "
            "de eventos) e se o sistema <i>controla a admissão</i> de novas requisições "
            "ou as deixa se acumular.")]

    s += subsecao("3.3 Comparação das abordagens existentes")
    s += [p("Os Quadros 12 e 13 comparam os trabalhos selecionados quanto a métodos, "
            "tecnologias, ambientes, métricas, resultados, vantagens e limitações.")]
    s += quadro(12, "Comparação dos trabalhos: métodos, tecnologias e ambientes", [
        ["Trabalho", "Método", "Tecnologias", "Ambiente"],
        ["Welsh, Culler e Brewer (2001)", "Proposta e avaliação experimental",
         "Java, SEDA/Haboob, Apache, Flash", "Servidor Linux multiprocessador e clientes em rede"],
        ["von Behren, Condit e Brewer (2003)", "Análise conceitual e experimento",
         "Threads de usuário (Capriccio), Knot", "Servidor Linux uniprocessador"],
        ["Pariag <i>et al.</i> (2007)", "<i>Benchmark</i> comparativo com ajuste",
         "µserver, Knot, WatPipe, <i>sendfile</i>", "1 Xeon 3,06 GHz, Linux 2.6, 4 clientes"],
        ["Harji, Buhr e Brecht (2012)", "<i>Benchmark</i> comparativo",
         "µserver, WatPipe, nginx, lighttpd, Apache", "4 núcleos, conteúdo estático"],
        ["Zhou <i>et al.</i> (2018)", "Proposta, produção e experimentos",
         "DAGOR, fila e prioridades", "Microsserviços do WeChat"],
        ["Enberg, Rao e Tarkoma (2019)", "Protótipo comparativo",
         "Thread-per-core, Memcached", "Hardware comum (<i>commodity</i>)"],
        ["Cho <i>et al.</i> (2020)", "Proposta e avaliação experimental",
         "Breakwater, Shenango, DAGOR, SEDA", "Servidores de <i>datacenter</i>, RPC em µs"],
        ["Jeffery, Jensen e Mortier (2024)", "Análise e protótipo",
         "cgroups, Go, Java, Rust, <i>friendlypool</i>", "Linux 6.2, 2× Xeon Silver 4112"],
    ], [0.25, 0.23, 0.28, 0.24], pequeno=True)
    s += quadro(13, "Comparação dos trabalhos: métricas, resultados, vantagens e limitações", [
        ["Trabalho", "Métricas", "Principal resultado", "Vantagens", "Limitações"],
        ["Welsh (2001)", "Vazão, tempo de resposta, justiça",
         "Estabilidade e justiça sob carga alta", "Controle explícito de sobrecarga",
         "Custo das filas; ajuste dos controladores"],
        ["von Behren (2003)", "Vazão, nº de threads",
         "100 mil threads; iguala a SEDA", "Programação mais simples",
         "Uniprocessador; avaliação curta"],
        ["Pariag (2007)", "Vazão, tempo de resposta",
         "Eventos ≈ 18% acima de threads", "Comparação justa e ajustada",
         "1 núcleo; só conteúdo estático"],
        ["Harji (2012)", "Vazão (Mbps), conexões/s",
         "Diferença ≤ 10%; implementação importa", "Multinúcleo; servidores reais",
         "Sem latência de cauda; sem VMs"],
        ["Zhou (2018)", "Taxa de sucesso, justiça",
         "Estável em produção por 5 anos", "Independente do serviço",
         "Lento em escala de µs"],
        ["Enberg (2019)", "Latência de cauda",
         "Até 71% menos latência de cauda", "Menos sincronização",
         "Uma única aplicação"],
        ["Cho (2020)", "Vazão útil, p99, convergência",
         "Converge em &lt; 20 ms sem colapso", "Rápido e sem colapso",
         "Exige Shenango e novo RPC"],
        ["Jeffery (2024)", "Latência máxima, vazão",
         "Latência 6,7× menor; vazão 1,4× menor", "Considera cotas e vizinhos",
         "<i>Preprint</i>; uma máquina"],
    ], [0.14, 0.19, 0.24, 0.21, 0.22], pequeno=True)
    s += [p("A comparação evidencia três tendências. Primeiro, as <b>métricas</b> mudaram: "
            "os trabalhos clássicos medem sobretudo a vazão, e os recentes medem a latência "
            "de cauda e o tempo de recuperação. Segundo, os <b>ambientes</b> mudaram: "
            "máquinas dedicadas deram lugar a ambientes compartilhados, com vizinhos e "
            "cotas de CPU. Terceiro, as <b>tecnologias</b> recentes dependem de "
            "ambientes de execução especializados (Shenango, Caladan), enquanto a maioria "
            "dos servidores em produção ainda usa modelos convencionais sobre o Linux.")]

    s += subsecao("3.4 Identificação de lacunas")
    s += [p("A partir da comparação, foram identificadas as lacunas do Quadro 14, "
            "classificadas segundo os tipos sugeridos no roteiro do trabalho.")]
    s += quadro(14, "Lacunas identificadas", [
        ["Tipo", "Lacuna", "Evidência"],
        ["Cenário não avaliado",
         "Entre os trabalhos analisados, as comparações entre processos, threads e "
         "eventos foram feitas em máquinas dedicadas. Nenhum deles repete essa comparação "
         "em contêineres com cotas de CPU.",
         "Pariag <i>et al.</i> (2007) e Harji, Buhr e Brecht (2012) usam máquinas "
         "dedicadas; Jeffery, Jensen e Mortier (2024) estudam cotas, mas não comparam "
         "arquiteturas."],
        ["Métrica não analisada",
         "As comparações de arquiteturas medem principalmente a vazão, sem latência de "
         "cauda (p99), memória por conexão e taxa de erros sob sobrecarga.",
         "Quadro 13."],
        ["Tecnologia não comparada",
         "O io_uring foi estudado em armazenamento e bancos de dados, mas não foi "
         "comparado ao epoll dentro dos três modelos de servidor.",
         "Didona <i>et al.</i> (2022); Jasny <i>et al.</i> (2025)."],
        ["Resultados divergentes",
         "Threads iguais ou melhores (2003) × eventos 18% melhores (2007) × diferença de "
         "até 10% dependente da implementação (2012).",
         "von Behren, Condit e Brewer (2003); Pariag <i>et al.</i> (2007); Harji, Buhr e "
         "Brecht (2012)."],
        ["Limitação apontada pelos autores",
         "Falta avaliar o comportamento em máquinas virtuais e com restrição de núcleos, "
         "e falta um ajuste automático dos servidores.",
         "Harji, Buhr e Brecht (2012); Pariag <i>et al.</i> (2007)."],
    ], [0.20, 0.47, 0.33])

    s += subsecao("3.5 Lacuna escolhida e proposta de continuidade")
    s += [p("A lacuna escolhida combina as duas primeiras linhas do Quadro 14:"),
          Paragraph("<i>Não foi encontrada, entre os trabalhos analisados, uma avaliação "
                    "comparativa dos modelos baseados em processos, threads e eventos sob "
                    "sobrecarga em ambiente conteinerizado com cotas de CPU (cgroups) que "
                    "meça, além da vazão, a latência de cauda (p99), o consumo de memória "
                    "e a taxa de erros.</i>", CITACAO_LONGA),
          p("A lacuna é relevante porque a maior parte dos servidores atuais roda em "
            "contêineres, e Jeffery, Jensen e Mortier (2024) mostram que as cotas de CPU "
            "alteram o comportamento das threads. Para uma etapa futura, propõem-se as "
            "seguintes hipóteses:")]
    s += itens([
        "<b>H1</b> – sob cotas de CPU, os modelos com muitas threads sofrem maior aumento "
        "do p99 que o modelo de eventos;",
        "<b>H2</b> – o modelo com número fixo de processos apresenta o maior tempo de "
        "espera na fila do kernel e a maior taxa de erros sob sobrecarga;",
        "<b>H3</b> – a vazão máxima dos três modelos difere pouco, como indicam Pariag "
        "<i>et al.</i> (2007) e Harji, Buhr e Brecht (2012).",
    ], marcador="")
    s += [p("Como método, sugere-se executar servidores representativos (Apache nos modos "
            "<i>prefork</i> e <i>event</i>, Nginx e um servidor com threads) em contêineres "
            "Docker com diferentes limites de CPU, gerar carga com uma ferramenta de "
            "taxa constante (carga aberta, como o wrk2) e medir vazão, p50, p99, memória e "
            "erros. A demonstração da Seção 4 é uma versão simplificada desse "
            "experimento.")]
    return s


# ------------------------------------------------------------ 4 DEMONSTRAÇÃO
def demonstracao():
    s = secao("4 DEMONSTRAÇÃO PRÁTICA")
    s += [p("Para ilustrar o problema na apresentação, a equipe desenvolveu um código em "
            "Python, disponível na pasta <i>codigo/</i> que acompanha este trabalho. Ele "
            "implementa o mesmo serviço de três formas e mede o comportamento de cada uma "
            "sob carga crescente.")]
    s += subsecao("4.1 Descrição do experimento")
    s += itens([
        "<b>Serviço:</b> cada requisição HTTP espera 50 ms, simulando uma consulta a banco "
        "de dados, e usa 1 ms de CPU. Cada conexão atende até 20 requisições "
        "(<i>keep-alive</i>);",
        "<b>Modelo de processos:</b> um conjunto fixo de 8 processos que aceitam conexões "
        "do mesmo socket, cada um atendendo uma conexão por vez (como o Apache "
        "<i>prefork</i>);",
        "<b>Modelo de threads:</b> uma thread do SO criada para cada conexão;",
        "<b>Modelo de eventos:</b> um único laço de eventos (<i>asyncio</i>), como no "
        "Nginx ou no Node.js;",
        "<b>Carga:</b> 10, 50, 100, 250 e 500 clientes simultâneos, 6 segundos por nível. "
        "Uma requisição sem resposta em 5 segundos é contada como erro;",
        "<b>Medições:</b> vazão, latência (p50 e p99), erros e, por meio da biblioteca "
        "<i>psutil</i>, a memória, as threads e os processos que o SO atribuiu ao "
        "servidor;",
        "<b>Ambiente:</b> AMD Ryzen 7 5700X (8 núcleos e 16 threads), 32 GB de RAM, "
        "Windows 11 e Python 3.14.",
    ])
    s += subsecao("4.2 Resultados")
    s += [p("A Tabela 1 resume os resultados para 10, 100 e 500 clientes. As Figuras 1 a 4 "
            "mostram todos os níveis.")]
    dados = [["Modelo", "Clientes", "Vazão (req/s)", "p99 (ms)", "Erros (%)",
              "Memória (MB)", "Threads do SO"],
             ["Processos", "10", "128,7", "171,5", "0,0", "238,4", "37"],
             ["Processos", "100", "133,3", "3.418,5", "7,7", "238,5", "37"],
             ["Processos", "500", "133,3", "3.658,7", "55,5", "238,5", "37"],
             ["Threads", "10", "175,0", "74,4", "0,0", "25,3", "14"],
             ["Threads", "100", "946,2", "239,2", "0,0", "28,2", "104"],
             ["Threads", "500", "937,0", "1.543,7", "0,0", "41,0", "504"],
             ["Eventos", "10", "155,7", "86,3", "0,0", "25,6", "5"],
             ["Eventos", "100", "725,5", "205,7", "0,0", "31,5", "5"],
             ["Eventos", "500", "901,7", "571,5", "0,0", "59,3", "5"]]
    s += tabela(1, "Resultados da demonstração (valores selecionados)", dados,
                [0.15, 0.12, 0.15, 0.13, 0.13, 0.16, 0.16])
    s += figura(1, "Vazão por número de clientes simultâneos", "grafico_vazao.png")
    s += figura(2, "Latência p99 por número de clientes (escala logarítmica)",
                "grafico_latencia_p99.png")
    s += figura(3, "Taxa de requisições com erro ou <i>timeout</i>", "grafico_erros.png")
    s += figura(4, "Memória máxima usada pelo servidor", "grafico_memoria.png")
    s += [p("<b>Processos.</b> A vazão fica limitada a cerca de 133 req/s em qualquer "
            "carga, próxima do teto teórico de 8 processos ÷ 0,051 s ≈ 157 req/s. Com "
            "mais clientes do que processos, as conexões esperam na fila do kernel "
            "(<i>backlog</i>). O p99 salta para mais de 3 segundos já com 50 clientes e, "
            "com 500 clientes, 55,5% das requisições excedem o limite de 5 s. É o colapso "
            "sob sobrecarga descrito por Welsh, Culler e Brewer (2001). Esse modelo também "
            "consome mais memória (cerca de 238 MB), pois cada processo tem seu próprio "
            "espaço de endereçamento."),
          p("<b>Threads.</b> A vazão cresce até cerca de 946 req/s, porque uma thread "
            "bloqueada em E/S libera a CPU para as outras. O número de threads do SO "
            "acompanha o número de clientes (504 threads com 500 clientes). Com a CPU "
            "saturada, o escalonador e a trava global do Python (GIL) formam uma fila "
            "invisível: o p99 passa de 74 ms para 1.544 ms, cerca de 20 vezes mais."),
          p("<b>Eventos.</b> Esse modelo usa apenas 5 threads em qualquer carga e alcança "
            "vazão próxima à do modelo de threads (902 req/s com 500 clientes, 4% a menos). "
            "O p99 com 500 clientes é 2,7 vezes menor que o das threads, pois o laço atende "
            "as conexões em ordem. Contrariando a expectativa comum, a memória foi maior "
            "que a das threads com 500 clientes. No Python, cada conexão <i>asyncio</i> "
            "mantém objetos no <i>heap</i>, enquanto a pilha das threads é reservada, mas "
            "pouco usada. Esse resultado confirma a conclusão de Harji, Buhr e Brecht "
            "(2012) de que a implementação importa tanto quanto a arquitetura."),
          p("Em conjunto, os resultados reproduzem em pequena escala o que a literatura "
            "descreve. Sob sobrecarga, a vazão dos modelos de threads e de eventos é "
            "parecida, e a diferença está em <i>onde a espera se acumula</i> e no efeito "
            "sobre a latência de cauda e os erros.")]
    s += subsecao("4.3 Limitações da demonstração")
    s += itens([
        "o cliente e o servidor rodam na mesma máquina e disputam a CPU;",
        "o Python possui GIL, o que impede o paralelismo real entre threads; em "
        "linguagens como C, Go, Java ou Rust os números seriam diferentes;",
        "o gerador de carga é fechado (cada cliente só envia após receber a resposta), o "
        "que tende a subestimar a latência sob sobrecarga;",
        "o experimento foi feito sem contêineres e sem cotas de CPU, justamente o cenário "
        "apontado como lacuna na Seção 3.5.",
    ])
    return s


def consideracoes():
    s = secao("5 CONSIDERAÇÕES FINAIS")
    s += [p("Este trabalho apresentou as Fases 1 e 2 de uma pesquisa sobre o comportamento "
            "de servidores sob sobrecarga, com foco nos modelos de execução baseados em "
            "processos, threads e eventos. Na Fase 1, foram levantados temas atuais em "
            "Sistemas Operacionais, identificados os problemas em discussão e realizada "
            "uma busca em cinco bases, que resultou em 14 trabalhos, dos quais oito foram "
            "fichados."),
          p("Na Fase 2, a comparação mostrou que as arquiteturas diferem pouco em vazão "
            "quando bem implementadas, mas se comportam de forma muito diferente em latência "
            "de cauda, consumo de recursos e estabilidade sob sobrecarga. A pesquisa "
            "recente concentra-se em controle de admissão, escalonamento fino e ambientes "
            "compartilhados. A lacuna escolhida é a falta de uma comparação dos três "
            "modelos em contêineres com cotas de CPU, medindo latência de cauda, memória e "
            "erros, além da vazão."),
          p("A demonstração prática confirmou, em pequena escala, os pontos centrais da "
            "revisão: o modelo com número fixo de processos colapsa quando a demanda supera "
            "o número de trabalhadores, o modelo de threads escala a vazão ao custo de uma "
            "cauda de latência maior e o modelo de eventos oferece latência mais previsível "
            "com poucas threads. Como continuidade, propõe-se executar o experimento "
            "descrito na Seção 3.5 com servidores reais em contêineres Docker com "
            "diferentes limites de CPU.")]
    return s


def referencias():
    refs = [
        "CHO, I.; SAEED, A.; FRIED, J.; PARK, S. J.; ALIZADEH, M.; BELAY, A. Overload "
        "control for µs-scale RPCs with Breakwater. <i>In</i>: USENIX SYMPOSIUM ON "
        "OPERATING SYSTEMS DESIGN AND IMPLEMENTATION, 14., 2020, [<i>s. l.</i>]. "
        "<b>Proceedings</b> [...]. Berkeley: USENIX Association, 2020. Disponível em: "
        "https://www.usenix.org/conference/osdi20/presentation/cho. Acesso em: 28 set. 2026.",

        "DIDONA, D.; PFEFFERLE, J.; IOANNOU, N.; METZLER, B.; TRIVEDI, A. Understanding "
        "modern storage APIs: a systematic study of libaio, SPDK, and io_uring. <i>In</i>: "
        "ACM INTERNATIONAL CONFERENCE ON SYSTEMS AND STORAGE (SYSTOR), 15., 2022, Haifa. "
        "<b>Proceedings</b> [...]. New York: ACM, 2022. p. 120-127. DOI: "
        "10.1145/3534056.3534945.",

        "ENBERG, P.; RAO, A.; TARKOMA, S. The impact of thread-per-core architecture on "
        "application tail latency. <i>In</i>: ACM/IEEE SYMPOSIUM ON ARCHITECTURES FOR "
        "NETWORKING AND COMMUNICATIONS SYSTEMS (ANCS), 15., 2019, Cambridge. "
        "<b>Proceedings</b> [...]. [<i>S. l.</i>]: IEEE, 2019. Disponível em: "
        "https://ieeexplore.ieee.org/document/8901874. Acesso em: 28 set. 2026.",

        "FRIED, J.; RUAN, Z.; OUSTERHOUT, A.; BELAY, A. Caladan: mitigating interference "
        "at microsecond timescales. <i>In</i>: USENIX SYMPOSIUM ON OPERATING SYSTEMS "
        "DESIGN AND IMPLEMENTATION, 14., 2020, [<i>s. l.</i>]. <b>Proceedings</b> [...]. "
        "Berkeley: USENIX Association, 2020. Disponível em: "
        "https://www.usenix.org/conference/osdi20/presentation/fried. Acesso em: 28 set. 2026.",

        "HARJI, A. S.; BUHR, P. A.; BRECHT, T. Comparing high-performance multi-core "
        "web-server architectures. <i>In</i>: ANNUAL INTERNATIONAL SYSTEMS AND STORAGE "
        "CONFERENCE (SYSTOR), 5., 2012, Haifa. <b>Proceedings</b> [...]. New York: ACM, "
        "2012. p. 2:1-2:12. DOI: 10.1145/2367589.2367591.",

        "JASNY, M.; EL-HINDI, M.; ZIEGLER, T.; LEIS, V.; BINNIG, C. High-performance "
        "DBMSs with io_uring: when and how to use it. <b>arXiv</b>, 2025. Preprint "
        "arXiv:2512.04859. Disponível em: https://arxiv.org/abs/2512.04859. "
        "Acesso em: 28 set. 2026.",

        "JEFFERY, A.; JENSEN, C.; MORTIER, R. Reducing tail latencies through "
        "environment- and neighbour-aware thread management. <b>arXiv</b>, 2024. Preprint "
        "arXiv:2407.11582. Disponível em: https://arxiv.org/abs/2407.11582. "
        "Acesso em: 28 set. 2026.",

        "KAFFES, K.; CHONG, T.; HUMPHRIES, J. T.; BELAY, A.; MAZIÈRES, D.; KOZYRAKIS, C. "
        "Shinjuku: preemptive scheduling for µsecond-scale tail latency. <i>In</i>: USENIX "
        "SYMPOSIUM ON NETWORKED SYSTEMS DESIGN AND IMPLEMENTATION, 16., 2019, Boston. "
        "<b>Proceedings</b> [...]. Berkeley: USENIX Association, 2019. Disponível em: "
        "https://www.usenix.org/conference/nsdi19/presentation/kaffes. Acesso em: 28 set. 2026.",

        "OUSTERHOUT, A.; FRIED, J.; BEHRENS, J.; BELAY, A.; BALAKRISHNAN, H. Shenango: "
        "achieving high CPU efficiency for latency-sensitive datacenter workloads. "
        "<i>In</i>: USENIX SYMPOSIUM ON NETWORKED SYSTEMS DESIGN AND IMPLEMENTATION, 16., "
        "2019, Boston. <b>Proceedings</b> [...]. Berkeley: USENIX Association, 2019. "
        "p. 361-378. Disponível em: "
        "https://www.usenix.org/conference/nsdi19/presentation/ousterhout. "
        "Acesso em: 28 set. 2026.",

        "PAI, V. S.; DRUSCHEL, P.; ZWAENEPOEL, W. Flash: an efficient and portable web "
        "server. <i>In</i>: USENIX ANNUAL TECHNICAL CONFERENCE, 1999, Monterey. "
        "<b>Proceedings</b> [...]. Berkeley: USENIX Association, 1999. Disponível em: "
        "https://www.usenix.org/legacy/event/usenix99/full_papers/pai/pai.pdf. "
        "Acesso em: 28 set. 2026.",

        "PARIAG, D.; BRECHT, T.; HARJI, A.; BUHR, P.; SHUKLA, A. Comparing the "
        "performance of web server architectures. <i>In</i>: EUROPEAN CONFERENCE ON "
        "COMPUTER SYSTEMS (EUROSYS), 2007, Lisboa. <b>Proceedings</b> [...]. New York: "
        "ACM, 2007. p. 231-243. DOI: 10.1145/1272996.1273021.",

        "SILBERSCHATZ, A.; GALVIN, P. B.; GAGNE, G. <b>Fundamentos de sistemas "
        "operacionais</b>. 9. ed. Rio de Janeiro: LTC, 2015.",

        "TANENBAUM, A. S.; BOS, H. <b>Sistemas operacionais modernos</b>. 4. ed. São "
        "Paulo: Pearson, 2016.",

        "VON BEHREN, R.; CONDIT, J.; BREWER, E. Why events are a bad idea (for "
        "high-concurrency servers). <i>In</i>: WORKSHOP ON HOT TOPICS IN OPERATING "
        "SYSTEMS (HotOS IX), 9., 2003, Lihue. <b>Proceedings</b> [...]. Berkeley: USENIX "
        "Association, 2003. Disponível em: https://www.usenix.org/conference/hotos-ix/"
        "why-events-are-bad-idea-high-concurrency-servers. Acesso em: 28 set. 2026.",

        "WELSH, M.; CULLER, D.; BREWER, E. SEDA: an architecture for well-conditioned, "
        "scalable internet services. <i>In</i>: ACM SYMPOSIUM ON OPERATING SYSTEMS "
        "PRINCIPLES (SOSP), 18., 2001, Banff. <b>Proceedings</b> [...]. New York: ACM, "
        "2001. p. 230-243. DOI: 10.1145/502034.502057.",

        "ZHOU, H.; CHEN, M.; LIN, Q.; WANG, Y.; SHE, X.; LIU, S.; GU, R.; OOI, B. C.; "
        "YANG, J. Overload control for scaling WeChat microservices. <i>In</i>: ACM "
        "SYMPOSIUM ON CLOUD COMPUTING (SoCC), 2018, Carlsbad. <b>Proceedings</b> [...]. "
        "New York: ACM, 2018. p. 149-161. DOI: 10.1145/3267809.3267823.",
    ]
    s = [PageBreak(), Titulo("REFERÊNCIAS", TITULO_SEM_NUM, 0)]
    s += [Paragraph(r, REFERENCIA) for r in refs]
    return s


def montar():
    doc = Documento(SAIDA)
    story = []
    story += capa()
    story += folha_de_rosto()
    story += resumo()
    story += sumario()
    story += introducao()
    story += fase1()
    story += fase2()
    story += demonstracao()
    story += consideracoes()
    story += referencias()
    doc.multiBuild(story)
    print(f"PDF gerado: {SAIDA}")


if __name__ == "__main__":
    montar()
