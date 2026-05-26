#!/usr/bin/env python3
"""简单本地服务器 - 提供静态文件 + Stooq API 代理（解决跨域）"""

import http.server
import urllib.request
import urllib.parse
import json
import os
import sys
import ssl

PORT = int(os.environ.get("PORT", 8765))
STOOQ_BASE = "https://stooq.com/q/l/"

# 跳过 SSL 验证（仅用于代理公开数据）
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Proxy /api/stooq?symbol=XAUUSD to Stooq
        if parsed.path == "/api/stooq":
            params = urllib.parse.parse_qs(parsed.query)
            symbol = params.get("symbol", ["XAUUSD"])[0]
            stooq_url = f"{STOOQ_BASE}?s={symbol}&f=sd2t2ohlcv&e=json"

            try:
                req = urllib.request.Request(stooq_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                    data = resp.read()
                # Stooq 返回的 JSON 中 volume 字段可能为空值，修复为 null
                data = data.replace(b'"volume":}', b'"volume":null}')
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        # Default: serve static files
        super().do_GET()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"""
╔══════════════════════════════════════════════════╗
║   贵金属实时行情 - 本地服务器                     ║
║   打开浏览器访问: http://localhost:{PORT}          ║
║   按 Ctrl+C 停止服务器                            ║
╚══════════════════════════════════════════════════╝
""")
    with http.server.HTTPServer(("", PORT), ProxyHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止。")
            sys.exit(0)
