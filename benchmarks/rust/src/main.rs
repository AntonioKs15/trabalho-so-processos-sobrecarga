//! main.rs - testes de desempenho em Rust (mesmos algoritmos de bench.c e bench.py).
//!
//! Uso: bench_rust <teste> <tamanho> [threads]
//!   cpu      <n>      crivo de Eratostenes ate n; resultado = quantidade de primos
//!   memoria  <mb>     aloca mb MiB e escreve 1 byte por pagina de 4 KiB
//!   io       <mb>     escreve e le mb MiB em /tmp em blocos de 4 KiB (read/write)
//!   threads  <n> [t]  t threads somam (i*i) % 1000 para i em [0, n)

use std::env;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::process;
use std::thread;
use std::time::Instant;

const PAGINA: usize = 4096;
const BLOCO: usize = 4096;
const MIB: usize = 1024 * 1024;

fn teste_cpu(n: usize) -> u64 {
    let mut primo = vec![1u8; n + 1];
    primo[0] = 0;
    if n >= 1 {
        primo[1] = 0;
    }
    let mut i = 2;
    while i * i <= n {
        if primo[i] == 1 {
            let mut j = i * i;
            while j <= n {
                primo[j] = 0;
                j += i;
            }
        }
        i += 1;
    }
    primo.iter().map(|&x| x as u64).sum()
}

fn teste_memoria(mb: usize) -> u64 {
    let tamanho = mb * MIB;
    // vec![0; n] usa calloc: o SO entrega paginas zeradas sob demanda
    let mut buf = vec![0u8; tamanho];
    let paginas = tamanho / PAGINA;
    for p in 0..paginas {
        buf[p * PAGINA] = (p & 0xff) as u8;
    }
    let mut soma = 0u64;
    for p in 0..paginas {
        soma += buf[p * PAGINA] as u64;
    }
    soma
}

fn teste_io(mb: usize) -> u64 {
    let caminho = format!("/tmp/bench_rust_{}.dat", process::id());
    let blocos = mb * MIB / BLOCO;
    let mut bloco = [0u8; BLOCO];
    {
        // File nao tem buffer: cada write_all vira uma chamada write(2)
        let mut f = File::create(&caminho).expect("create");
        for b in 0..blocos {
            bloco.fill((b & 0xff) as u8);
            f.write_all(&bloco).expect("write");
        }
    }
    let mut soma = 0u64;
    {
        let mut f = File::open(&caminho).expect("open");
        loop {
            let lidos = f.read(&mut bloco).expect("read");
            if lidos == 0 {
                break;
            }
            soma += bloco[0] as u64;
        }
    }
    let _ = fs::remove_file(&caminho);
    soma
}

fn teste_threads(n: u64, t: u64) -> u64 {
    let passo = n / t;
    thread::scope(|s| {
        let alcas: Vec<_> = (0..t)
            .map(|k| {
                let inicio = k * passo;
                let fim = if k == t - 1 { n } else { (k + 1) * passo };
                s.spawn(move || {
                    let mut soma = 0u64;
                    for i in inicio..fim {
                        soma += (i.wrapping_mul(i)) % 1000;
                    }
                    soma
                })
            })
            .collect();
        alcas.into_iter().map(|a| a.join().unwrap()).sum()
    })
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("uso: {} <cpu|memoria|io|threads> <tamanho> [threads]", args[0]);
        process::exit(2);
    }
    let teste = args[1].as_str();
    let tamanho: usize = args[2].parse().expect("tamanho invalido");
    let t: u64 = args.get(3).and_then(|x| x.parse().ok()).unwrap_or(4).clamp(1, 256);

    let inicio = Instant::now();
    let r = match teste {
        "cpu" => teste_cpu(tamanho),
        "memoria" => teste_memoria(tamanho),
        "io" => teste_io(tamanho),
        "threads" => teste_threads(tamanho as u64, t),
        _ => {
            eprintln!("teste desconhecido: {}", teste);
            process::exit(2);
        }
    };
    let ms = inicio.elapsed().as_secs_f64() * 1000.0;
    println!(
        "{{\"linguagem\": \"rust\", \"teste\": \"{}\", \"resultado\": {}, \"tempo_interno_ms\": {:.3}}}",
        teste, r, ms
    );
}
