"""Loopback-only HTML interface for the existing exact hybrid search engine.

Run: python -m skripsi_search.web --root . --port 8765
No additional server dependency; the model/index is loaded once per process.
"""
import argparse
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

CONFIGURATIONS = [
    {'id': 'legacy', 'name': 'Legacy', 'subtitle': 'Baseline hybrid', 'description': '70% semantik + 30% BM25, dengan normalisasi baseline lama.'},
    {'id': 'plain_w07', 'name': 'Weighted 0,7', 'subtitle': 'Hybrid perbaikan', 'description': '70% semantik + 30% BM25 setelah normalisasi peringkat kedua channel.'},
    {'id': 'plain_rrf', 'name': 'RRF', 'subtitle': 'Fusion peringkat', 'description': 'Gabungan peringkat SBERT dan BM25 dengan konstanta RRF 60.'},
]
ALLOWED = {c['id'] for c in CONFIGURATIONS}
WEB_ROOT = Path(__file__).parent / 'web_static'


def validate_search(payload):
    if not isinstance(payload, dict):
        raise ValueError('Permintaan harus berupa objek JSON.')
    config = payload.get('configuration', 'legacy')
    if not isinstance(config, str) or config not in ALLOWED:
        raise ValueError('Pilih salah satu dari tiga konfigurasi yang tersedia.')
    top_k = payload.get('top_k', 10)
    if type(top_k) is not int or not 1 <= top_k <= 20:
        raise ValueError('Jumlah hasil harus bilangan bulat antara 1 dan 20.')
    query = payload.get('query')
    if not isinstance(query, dict):
        raise ValueError('Input proposal belum tersedia.')
    normalized = {}
    for field in ('title', 'description', 'problem', 'method', 'dataset'):
        text = query.get(field, '')
        if not isinstance(text, str):
            raise ValueError('Semua input proposal harus berupa teks.')
        limit = 20000 if field == 'description' else 6000
        if len(text) > limit:
            raise ValueError(f'Input {field} terlalu panjang (maksimal {limit} karakter).')
        normalized[field] = text.strip()
    if not normalized['title'] or not normalized['description']:
        raise ValueError('Isi judul dan deskripsi proposal terlebih dahulu.')
    return normalized, config, top_k


class SearchApplication:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.state = 'loading'
        self.index = None
        self.error = ''
        self.search_lock = threading.Lock()

    def load(self):
        try:
            from .engine import load_index
            self.index = load_index(self.root)
            self.state = 'ready'
            logging.info('Indeks siap: %s dokumen', len(self.index.docs))
        except Exception:
            logging.exception('Gagal menyiapkan mesin pencarian')
            self.error = 'Indeks belum dapat disiapkan. Periksa dependensi, file sumber, dan model pada terminal, lalu jalankan ulang aplikasi.'
            self.state = 'error'

    def status(self):
        index = self.index if self.state == 'ready' else None
        return {
            'state': self.state,
            'message': self.error if self.state == 'error' else 'Database siap digunakan.' if index else 'Menyiapkan model dan indeks. Proses pertama dapat memerlukan unduhan model.',
            'documents': len(index.docs) if index else None,
            'model': index.encoder.info if index else None,
            'fingerprint': index.fingerprint if index else None,
            'configurations': CONFIGURATIONS,
            'reranking': False,
        }


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            logging.info(fmt, *args)

        def send(self, status, data, mime='application/json; charset=utf-8'):
            if isinstance(data, (dict, list)):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def trusted_host(self):
            port = self.server.server_address[1]
            return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

        def do_GET(self):
            if not self.trusted_host():
                self.send(403, {'error': 'Aplikasi hanya tersedia melalui localhost.'}); return
            path = urlsplit(self.path).path
            if path == '/api/status':
                self.send(200, app.status()); return
            if path == '/api/example':
                self.send(200, json.loads((app.root / 'evaluation/example_query.json').read_text(encoding='utf-8'))); return
            assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'), '/styles.css': ('styles.css', 'text/css; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
            if path not in assets:
                self.send(404, {'error': 'Halaman tidak ditemukan.'}); return
            name, mime = assets[path]
            self.send(200, (WEB_ROOT / name).read_bytes(), mime)

        def do_POST(self):
            if not self.trusted_host():
                self.send(403, {'error': 'Host tidak diizinkan.'}); return
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                self.send(403, {'error': 'Origin tidak diizinkan.'}); return
            if urlsplit(self.path).path != '/api/search':
                self.send(404, {'error': 'Endpoint tidak ditemukan.'}); return
            if self.headers.get_content_type() != 'application/json':
                self.send(415, {'error': 'Gunakan input JSON.'}); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536:
                    self.send(413, {'error': 'Ukuran permintaan tidak valid atau terlalu besar.'}); return
                payload = json.loads(self.rfile.read(length))
                query, config, top_k = validate_search(payload)
            except (ValueError, UnicodeDecodeError):
                self.send(400, {'error': 'Input tidak valid. Pastikan judul, deskripsi, konfigurasi, dan jumlah hasil terisi dengan benar.'}); return
            if app.state != 'ready':
                self.send(503, {'error': app.error or 'Model dan indeks masih disiapkan. Coba lagi setelah database siap.'}); return
            if not app.search_lock.acquire(blocking=False):
                self.send(409, {'error': 'Pencarian lain sedang diproses. Silakan coba lagi.'}); return
            try:
                started = time.perf_counter()
                result = app.index.search(query, top_k=top_k, config=config, rerank=0.)
                result['request'] = {'query': query, 'configuration': config, 'top_k': top_k}
                result['elapsed_ms'] = round((time.perf_counter() - started) * 1000)
                result['documents_searched'] = len(app.index.docs)
                self.send(200, result)
            except ValueError as exc:
                self.send(400, {'error': str(exc)})
            except Exception:
                logging.exception('Pencarian gagal')
                self.send(500, {'error': 'Pencarian belum berhasil. Periksa pesan pada terminal, lalu coba lagi.'})
            finally:
                app.search_lock.release()
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Tampilan lokal pencarian skripsi (HTML/CSS/JS)')
    parser.add_argument('--root', default='.', help='Folder proyek berisi sources.json')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port harus antara 1 dan 65535')
    app = SearchApplication(args.root)
    if not (app.root / 'sources.json').is_file():
        parser.error('sources.json tidak ditemukan. Gunakan --root atau jalankan dari folder proyek.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(app))
    threading.Thread(target=app.load, daemon=True, name='index-loader').start()
    print(f'Buka aplikasi: http://127.0.0.1:{args.port}', flush=True)
    print('Model dimuat sekali. Tekan Ctrl+C untuk menghentikan aplikasi.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
