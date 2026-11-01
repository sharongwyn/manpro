import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest
from skripsi_search.web import SearchApplication, handler_for, validate_search


@pytest.mark.parametrize('configuration', ['legacy', 'plain_w07', 'plain_rrf'])
def test_web_configurations(configuration):
    q, config, count = validate_search({'query': {'title': ' Judul ', 'description': 'Deskripsi penelitian'}, 'configuration': configuration, 'top_k': 10})
    assert q['title'] == 'Judul' and config == configuration and count == 10


@pytest.mark.parametrize('payload', [None, {}, {'query': {}}, {'query': {'title': 'a', 'description': 'b'}, 'configuration': 'sbert'}, {'query': {'title': 'a', 'description': 'b'}, 'top_k': True}, {'query': {'title': 'a', 'description': 'b'}, 'top_k': 100}, {'query': {'title': 'a', 'description': []}}])
def test_web_bad_requests(payload):
    with pytest.raises(ValueError): validate_search(payload)


def test_http_routes_loading_and_search(tmp_path):
    app = SearchApplication(tmp_path)
    (tmp_path / 'evaluation').mkdir()
    (tmp_path / 'evaluation/example_query.json').write_text(json.dumps({'title': 'Contoh', 'description': 'Deskripsi'}))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    def get(path):
        with urllib.request.urlopen(base + path) as response: return response.read(), response.headers
    def post(payload, headers=None):
        req = urllib.request.Request(base + '/api/search', data=json.dumps(payload).encode(), headers=headers or {'Content-Type': 'application/json'})
        return urllib.request.urlopen(req)
    try:
        page, headers = get('/')
        assert b'Temu Skripsi' in page and "script-src 'self'" in headers['Content-Security-Policy']
        assert b'legacy' in get('/app.js')[0]
        assert json.loads(get('/api/status')[0])['state'] == 'loading'
        assert json.loads(get('/api/example')[0])['title'] == 'Contoh'
        payload = {'query': {'title': 'Judul', 'description': 'Deskripsi penelitian'}, 'configuration': 'legacy'}
        with pytest.raises(urllib.error.HTTPError) as err: post(payload)
        assert err.value.code == 503
        calls = []
        def fake_search(query, **options):
            calls.append((query, options)); return {'results': [], 'config': options['config'], 'no_positive_signal': True}
        app.index = SimpleNamespace(docs=[{'id': '1'}], search=fake_search, encoder=SimpleNamespace(info={'device': 'cpu'}), fingerprint='fixture')
        app.state = 'ready'
        with post(payload) as response: result = json.load(response)
        assert result['documents_searched'] == 1 and result['request']['configuration'] == 'legacy'
        assert calls[0][1]['rerank'] == 0
        assert calls[0][1]['top_k'] == 10
        assert json.loads(get('/api/status')[0])['documents'] == 1
        with pytest.raises(urllib.error.HTTPError) as err: post(payload, {'Content-Type': 'application/json', 'Origin': 'https://example.com'})
        assert err.value.code == 403
        with pytest.raises(urllib.error.HTTPError) as err: get('/reports/corpus.json')
        assert err.value.code == 404
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
