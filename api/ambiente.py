"""GET /api/ambiente -> kernel, distribuicao, CPU, memoria e limites dos testes."""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _executor  # noqa: E402
from benchmark import responder  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            responder(self, 200, _executor.ambiente())
        except Exception as e:
            responder(self, 500, {"erro": str(e)})
