"""GET /api/benchmark?teste=cpu&tamanho=2000000&repeticoes=3&threads=4&linguagens=c,rust,python"""

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _executor  # noqa: E402


def responder(req, status, corpo):
    dados = json.dumps(corpo, ensure_ascii=False).encode()
    req.send_response(status)
    req.send_header("Content-Type", "application/json; charset=utf-8")
    req.send_header("Cache-Control", "no-store")
    req.send_header("Content-Length", str(len(dados)))
    req.end_headers()
    req.wfile.write(dados)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        try:
            linguagens = q.get("linguagens")
            corpo = _executor.comparar(
                q.get("teste", "cpu"),
                tamanho=q.get("tamanho"),
                repeticoes=q.get("repeticoes", 3),
                threads=q.get("threads", 4),
                linguagens=linguagens.split(",") if linguagens else None,
            )
            responder(self, 200, corpo)
        except ValueError as e:
            responder(self, 400, {"erro": str(e)})
        except Exception as e:
            responder(self, 500, {"erro": str(e), "detalhe": traceback.format_exc()[-800:]})
