"use strict";

const LINGUAGENS = [
  { id: "c", nome: "C" },
  { id: "rust", nome: "Rust" },
  { id: "python", nome: "Python" },
];

// Usado se /api/ambiente falhar; o servidor e quem manda nos limites reais.
let TESTES = {
  cpu: { rotulo: "CPU", unidade: "n", padrao: 2000000, minimo: 1000, maximo: 10000000 },
  memoria: { rotulo: "Memória", unidade: "MiB", padrao: 128, minimo: 1, maximo: 512 },
  io: { rotulo: "E/S", unidade: "MiB", padrao: 32, minimo: 1, maximo: 128 },
  threads: { rotulo: "Threads", unidade: "n", padrao: 10000000, minimo: 1000, maximo: 20000000 },
};

const CARTOES = {
  cpu: ["CPU", "Crivo de Eratóstenes. Só conta, quase sem syscalls."],
  memoria: ["Memória", "Aloca N MiB e escreve um byte em cada página de 4 KiB."],
  io: ["Arquivo", "Grava e lê N MiB em /tmp com read/write de 4 KiB."],
  threads: ["Threads", "Divide uma soma entre várias threads do SO."],
};

const EXPLICA = {
  cpu: [
    "Quase todo o tempo é <strong>CPU em modo usuário</strong>: o programa só faz contas e quase não chama o kernel.",
    "C e Rust viram instruções de máquina antes de rodar. O Python interpreta bytecode linha a linha, e cada operação passa pelo laço do interpretador, por isso fica dezenas de vezes mais lento.",
    "Compare também o tempo interno com o total: no Python, uma parte do total é só o interpretador subindo (carregar o executável, importar módulos).",
  ],
  memoria: [
    "Aqui o tempo vai para o <strong>modo kernel</strong>. O <code>malloc</code> só reserva endereços; a memória física chega quando o programa toca cada página, e cada primeiro toque gera um <strong>page fault</strong> que o kernel resolve.",
    "Com 4 KiB por página, 64 MiB dão cerca de 16 mil page faults nas três linguagens, porque quem faz o trabalho é o kernel, não a linguagem.",
    "O Python tem um pico de memória maior: o próprio interpretador já ocupa alguns MiB antes do teste começar.",
  ],
  io: [
    "Cada bloco de 4 KiB vira uma chamada <code>write()</code> e depois uma <code>read()</code>. São milhares de entradas no kernel, que aparecem como <strong>CPU em modo kernel</strong>.",
    "O custo da syscall é o mesmo para todas; a diferença entre as linguagens é o que acontece entre uma chamada e outra.",
    "Os dados ficam no page cache do kernel; por isso não há espera de disco e quase não há page faults maiores.",
  ],
  threads: [
    "Em C e Rust, as threads rodam ao mesmo tempo em núcleos diferentes: a CPU somada pode passar do tempo de parede, e a barra mostra isso.",
    "No CPython, o <strong>GIL</strong> deixa só uma thread executar bytecode por vez. As threads existem para o kernel, mas se revezam, e o número de trocas de contexto sobe.",
    "Aumente as threads e veja: C e Rust ficam mais rápidos até o limite de CPUs da máquina; o Python não.",
  ],
};

const METRICAS = [
  ["tempo_total_ms", "Tempo total", "do fork ao wait4", ms],
  ["tempo_interno_ms", "Tempo do algoritmo", "medido dentro do programa", ms],
  ["cpu_usuario_ms", "CPU em modo usuário", "ru_utime", ms],
  ["cpu_sistema_ms", "CPU em modo kernel", "ru_stime", ms],
  ["memoria_max_kib", "Pico de memória", "ru_maxrss", kib],
  ["page_faults_menores", "Page faults menores", "ru_minflt", int],
  ["page_faults_maiores", "Page faults maiores", "ru_majflt", int],
  ["trocas_voluntarias", "Trocas de contexto voluntárias", "ru_nvcsw", int],
  ["trocas_involuntarias", "Trocas de contexto involuntárias", "ru_nivcsw", int],
];

const $ = (s) => document.querySelector(s);
const fmt = new Intl.NumberFormat("pt-BR");
function ms(v) { return v >= 1000 ? `${(v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} s` : `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ms`; }
function kib(v) { return v >= 1024 ? `${(v / 1024).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MiB` : `${fmt.format(v)} KiB`; }
function int(v) { return fmt.format(Math.round(v)); }

let testeAtual = "cpu";
let resultados = {};

function guardar(chave, valor) { try { localStorage.setItem(chave, valor); } catch (_) {} }
function lerGuardado(chave) { try { return localStorage.getItem(chave); } catch (_) { return null; } }

// ---- tamanho: slider em escala logarítmica entre mínimo e máximo
function tamanhoDoSlider(pos) {
  const t = TESTES[testeAtual];
  const v = Math.exp(Math.log(t.minimo) + (Math.log(t.maximo) - Math.log(t.minimo)) * pos / 100);
  const passo = t.unidade === "MiB" ? 1 : Math.pow(10, Math.max(0, Math.floor(Math.log10(v)) - 1));
  return Math.max(t.minimo, Math.min(t.maximo, Math.round(v / passo) * passo));
}
function sliderDoTamanho(v) {
  const t = TESTES[testeAtual];
  return Math.round(100 * (Math.log(v) - Math.log(t.minimo)) / (Math.log(t.maximo) - Math.log(t.minimo)));
}
function rotuloTamanho(v) {
  return TESTES[testeAtual].unidade === "MiB" ? `${fmt.format(v)} MiB` : `n = ${fmt.format(v)}`;
}
function atualizarTamanho() { $("#tamanho-valor").value = rotuloTamanho(tamanhoDoSlider(+$("#tamanho").value)); }

// ---- montagem
function montarTestes() {
  const box = $("#testes");
  box.innerHTML = "";
  for (const id of Object.keys(CARTOES)) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "teste";
    b.setAttribute("role", "radio");
    b.dataset.teste = id;
    b.innerHTML = `<strong>${CARTOES[id][0]}</strong><span>${CARTOES[id][1]}</span>`;
    b.addEventListener("click", () => escolherTeste(id));
    box.appendChild(b);
  }
}

function escolherTeste(id) {
  testeAtual = id;
  guardar("teste", id);
  document.querySelectorAll(".teste").forEach((b) => {
    const sel = b.dataset.teste === id;
    b.setAttribute("aria-checked", sel);
    b.tabIndex = sel ? 0 : -1;
  });
  $("#tamanho").value = sliderDoTamanho(TESTES[id].padrao);
  atualizarTamanho();
  $("#campo-threads").hidden = id !== "threads";
  $("#explicacao").innerHTML = EXPLICA[id].map((p) => `<p>${p}</p>`).join("");
  limpar();
}

function montarRaias() {
  $("#raias").innerHTML = LINGUAGENS.map((l) => `
    <div class="raia ${l.id}" id="raia-${l.id}">
      <div class="raia-nome">${l.nome}</div>
      <div class="pista"><div class="barra"><div class="u"></div><div class="s"></div></div></div>
      <div class="raia-num"></div>
    </div>`).join("");
}

function limpar() {
  resultados = {};
  montarRaias();
  $("#conferencia").hidden = true;
  desenharTabela();
}

// ---- desenho
function desenharRaias() {
  const maior = Math.max(1, ...Object.values(resultados).map((r) => r.mediana.tempo_total_ms));
  for (const l of LINGUAGENS) {
    const r = resultados[l.id];
    const raia = $(`#raia-${l.id}`);
    if (!r) continue;
    const m = r.mediana;
    const cpu = m.cpu_usuario_ms + m.cpu_sistema_ms;
    const base = Math.max(m.tempo_total_ms, cpu); // em paralelo a CPU pode passar do tempo de parede
    raia.classList.add("feita");
    raia.querySelector(".barra").style.width = `${Math.max(1.5, 100 * m.tempo_total_ms / maior)}%`;
    raia.querySelector(".u").style.width = `${100 * m.cpu_usuario_ms / base}%`;
    raia.querySelector(".s").style.width = `${100 * m.cpu_sistema_ms / base}%`;
    const paralelo = cpu > m.tempo_total_ms * 1.15
      ? `<span>CPU ${(cpu / m.tempo_total_ms).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}× o tempo: rodou em paralelo</span>` : "";
    raia.querySelector(".raia-num").innerHTML =
      `<b>${ms(m.tempo_total_ms)}</b><span>usuário ${ms(m.cpu_usuario_ms)}</span>` +
      `<span>kernel ${ms(m.cpu_sistema_ms)}</span><span>${kib(m.memoria_max_kib)}</span>${paralelo}`;
  }
}

function desenharTabela() {
  const corpo = $("#tabela tbody");
  corpo.innerHTML = METRICAS.map(([chave, nome, origem, f]) => {
    const vals = LINGUAGENS.map((l) => resultados[l.id]?.mediana[chave]);
    const presentes = vals.filter((v) => v !== undefined);
    const menor = presentes.length > 1 ? Math.min(...presentes) : null;
    const tds = vals.map((v) => v === undefined ? `<td>–</td>`
      : `<td class="${v === menor ? "melhor" : ""}">${f(v)}</td>`).join("");
    return `<tr><th scope="row">${nome}<small>${origem}</small></th>${tds}</tr>`;
  }).join("");
}

function registrar(texto) {
  const log = $("#log");
  log.textContent += `\n${texto}`;
  log.scrollTop = log.scrollHeight;
}

// ---- execução
async function executar() {
  const botao = $("#executar");
  botao.disabled = true;
  botao.textContent = "Executando…";
  limpar();
  const tamanho = tamanhoDoSlider(+$("#tamanho").value);
  const repeticoes = +$("#repeticoes").value;
  const threads = +$("#threads").value;
  $("#log").textContent = `$ teste=${testeAtual} tamanho=${tamanho} repetições=${repeticoes}` +
    (testeAtual === "threads" ? ` threads=${threads}` : "");

  try {
    for (const l of LINGUAGENS) {
      const raia = $(`#raia-${l.id}`);
      raia.classList.add("rodando");
      const q = new URLSearchParams({ teste: testeAtual, tamanho, repeticoes, threads, linguagens: l.id });
      const inicio = performance.now();
      const resp = await fetch(`/api/benchmark?${q}`);
      const dados = await resp.json().catch(() => ({ erro: `resposta inválida (HTTP ${resp.status})` }));
      raia.classList.remove("rodando");
      if (!resp.ok || dados.erro) throw new Error(`${l.nome}: ${dados.erro || resp.status}`);

      const r = dados.linguagens[l.id];
      resultados[l.id] = r;
      registrar(`\n$ ${r.mediana.comando}`);
      r.execucoes.forEach((e, i) => registrar(
        `  #${i + 1} pid=${e.pid} total=${e.tempo_total_ms}ms utime=${e.cpu_usuario_ms}ms ` +
        `stime=${e.cpu_sistema_ms}ms maxrss=${e.memoria_max_kib}KiB minflt=${e.page_faults_menores} ` +
        `nvcsw=${e.trocas_voluntarias} nivcsw=${e.trocas_involuntarias}`));
      registrar(`  resultado=${r.mediana.resultado}  (requisição HTTP: ${Math.round(performance.now() - inicio)} ms)`);
      desenharRaias();
      desenharTabela();
    }
    const valores = new Set(Object.values(resultados).map((r) => String(r.mediana.resultado)));
    const conf = $("#conferencia");
    conf.hidden = false;
    conf.className = `conferencia ${valores.size === 1 ? "ok" : "erro"}`;
    conf.textContent = valores.size === 1
      ? `As três linguagens chegaram ao mesmo resultado (${[...valores][0]}), então fizeram o mesmo trabalho.`
      : "Os resultados das linguagens não conferem. Veja o registro.";
  } catch (e) {
    registrar(`\nerro: ${e.message}`);
    document.querySelectorAll(".raia").forEach((r) => r.classList.remove("rodando"));
  } finally {
    botao.disabled = false;
    botao.textContent = "Executar nas três linguagens";
  }
}

async function carregarAmbiente() {
  const dl = $("#ambiente");
  try {
    const a = await (await fetch("/api/ambiente")).json();
    if (a.testes) TESTES = a.testes;
    const itens = [
      ["Onde", a.vercel ? `Vercel${a.regiao ? ` (${a.regiao})` : ""}` : "máquina local"],
      ["Sistema", a.distribuicao || a.sistema],
      ["Kernel", `${a.sistema} ${a.kernel}`],
      ["Processador", `${a.cpu_modelo}, ${a.cpus_disponiveis} CPU`],
      ["Memória", a.memoria_total.replace(" kB", "") ? kib(parseInt(a.memoria_total, 10)) : "?"],
      ["Python", a.python],
    ];
    dl.innerHTML = itens.map(([t, d]) => `<div><dt>${t}</dt><dd>${d}</dd></div>`).join("");
  } catch (e) {
    dl.innerHTML = `<div><dt>Ambiente</dt><dd>a API não respondeu; confira se o servidor está no ar</dd></div>`;
  }
}

function iniciar() {
  montarTestes();
  for (const [id, saida] of [["tamanho", null], ["threads", "#threads-valor"], ["repeticoes", "#rep-valor"]]) {
    $(`#${id}`).addEventListener("input", (e) => saida ? ($(saida).value = e.target.value) : atualizarTamanho());
  }
  $("#testes").addEventListener("keydown", (e) => {
    const ids = Object.keys(CARTOES);
    const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!d) return;
    e.preventDefault();
    const novo = ids[(ids.indexOf(testeAtual) + d + ids.length) % ids.length];
    escolherTeste(novo);
    document.querySelector(`.teste[data-teste="${novo}"]`).focus();
  });
  $("#executar").addEventListener("click", executar);
  const salvo = lerGuardado("teste");
  escolherTeste(CARTOES[salvo] ? salvo : "cpu");
  carregarAmbiente().then(() => {
    escolherTeste(testeAtual);
    if (location.hash === "#executar") executar(); // atalho: abre a página já executando
  });
}

iniciar();
