#!/usr/bin/env python3
"""
UNO Q 点阵控制台 - 板载服务端

在 UNO Q 的 Linux 侧运行，提供一个网页 + HTTP API，
把像素数据通过 arduino-router 的 RPC 通道发给 MCU，点亮 13x8 LED 点阵。

不依赖 Arduino App Lab。

用法：
    python3 matrix-server.py [--port 8080] [--ui ../webui/matrix-ui.html]
"""

import argparse
import json
import os
import socket
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROUTER_SOCK = "/var/run/arduino-router.sock"

COLS, ROWS = 13, 8
PIXELS = COLS * ROWS  # 104


# ---------------------------------------------------------------- msgpack

def _mp_str(s: str) -> bytes:
    b = s.encode()
    n = len(b)
    if n < 32:
        return bytes([0xA0 | n]) + b
    if n < 256:
        return bytes([0xD9, n]) + b
    return bytes([0xDA]) + struct.pack(">H", n) + b


def _mp_arr(n: int) -> bytes:
    if n < 16:
        return bytes([0x90 | n])
    return bytes([0xDC]) + struct.pack(">H", n)


def _mp_int(i: int) -> bytes:
    if 0 <= i < 128:
        return bytes([i])
    return bytes([0xD2]) + struct.pack(">i", i)


# ---------------------------------------------------------------- RPC

_lock = threading.Lock()
_next_id = [0]


def rpc_call(method: str, *params, timeout: float = 5.0):
    """调用 MCU 侧 Bridge.provide 注册的函数。

    协议：[0, msgid, method_name, [params...]]，msgpack 编码。
    响应：[1, msgid, result, error]。
    """
    with _lock:
        _next_id[0] = (_next_id[0] + 1) % 128
        msgid = _next_id[0]

        req = (
            _mp_arr(4)
            + _mp_int(0)
            + _mp_int(msgid)
            + _mp_str(method)
            + _mp_arr(len(params))
            + b"".join(_mp_str(p) for p in params)
        )

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect(ROUTER_SOCK)
            s.send(req)
            resp = s.recv(4096)
        finally:
            s.close()

        if len(resp) >= 5 and resp[0] == 0x94 and resp[3] != 0xC0:
            raise RuntimeError("MCU returned an error")
        return resp


def set_pixels(pixels: str):
    """把 104 字符的像素串（'0'-'7' 灰度）发给 MCU。"""
    if len(pixels) != PIXELS:
        raise ValueError(f"expected {PIXELS} pixels, got {len(pixels)}")
    if any(c not in "01234567" for c in pixels):
        raise ValueError("pixels must be digits 0-7")
    rpc_call("set_pixels", pixels)


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    ui_html = b"<h1>UI not loaded</h1>"
    quiet = False

    def log_message(self, fmt, *args):
        if not self.quiet:
            print(f"{self.address_string()} - {fmt % args}", flush=True)

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, self.ui_html, "text/html; charset=utf-8")
        elif self.path == "/health":
            self._send(200, b'{"ok":true}', "application/json")
        else:
            self._send(404, b'{"ok":false,"error":"not found"}', "application/json")

    def do_POST(self):
        if self.path != "/api/pixels":
            self._send(404, b'{"ok":false,"error":"not found"}', "application/json")
            return

        n = int(self.headers.get("Content-Length", 0) or 0)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
            set_pixels(data.get("pixels", ""))
            self._send(200, b'{"ok":true}', "application/json")
        except Exception as e:
            body = json.dumps({"ok": False, "error": str(e)}).encode()
            self._send(400, body, "application/json")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--ui", default=os.path.join(here, "..", "webui", "matrix-ui.html"))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if os.path.exists(args.ui):
        with open(args.ui, "rb") as f:
            Handler.ui_html = f.read()
        print(f"UI loaded: {args.ui}")
    else:
        print(f"WARNING: UI file not found: {args.ui}")

    Handler.quiet = args.quiet
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Matrix console listening on http://{args.host}:{args.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
