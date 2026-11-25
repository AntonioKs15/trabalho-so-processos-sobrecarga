"""
Servidor local que imita o Vercel: entrega public/ e encaminha /api/* para os
mesmos handlers usados em producao. Precisa de Linux (wait4 e os binarios), por
isso no Windows rode dentro do Docker:

    sh scripts/local.sh          (abre em http://localhost:8000)

Tambem e o plano B da apresentacao se a internet falhar.
"""

import importlib
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "api"))
ROTAS = {"/api/benchmark": "benchmark", "/api/ambiente": "ambiente"}


class Roteador(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(RAIZ, "public"), **kwargs)

    def do_GET(self):
        rota = self.path.split("?", 1)[0]
        if rota in ROTAS:
            modulo = importlib.import_module(ROTAS[rota])
            return modulo.handler.do_GET(self)
        return super().do_GET()


if __name__ == "__main__":
    porta = int(os.environ.get("PORTA", "8000"))
    print(f"servindo em http://localhost:{porta}")
    ThreadingHTTPServer(("0.0.0.0", porta), Roteador).serve_forever()
