'use strict';

const $ = id => document.getElementById(id);
const names = { legacy: 'Legacy', plain_w07: 'Weighted 0,7', plain_rrf: 'RRF' };
const aspectNames = { problem: 'Masalah / tujuan', algorithm: 'Algoritma', technology: 'Teknologi', research_method: 'Metode penelitian', object: 'Objek', dataset_identity: 'Identitas dataset', platform: 'Platform sumber', data_type: 'Jenis data', collection: 'Pengumpulan data', context: 'Lokasi / populasi / periode' };
let ready = false;
let busy = false;
let currentResult = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function number(value, digits = 3) {
  return Number.isFinite(value) ? value.toLocaleString('id-ID', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—';
}
function error(message) {
  $('form-error').textContent = message || '';
  $('form-error').hidden = !message;
}
function updateButton() {
  $('search-button').disabled = !ready || busy;
  $('search-button-text').textContent = busy ? 'Sedang mencari…' : 'Cari kemiripan';
}
async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Permintaan tidak berhasil. Coba lagi.');
  return data;
}
async function status() {
  try {
    const data = await request('/api/status');
    ready = data.state === 'ready';
    $('connection').className = 'connection ' + (ready ? 'ready' : data.state === 'error' ? 'error' : '');
    $('connection-text').textContent = ready ? 'Database siap' : data.state === 'error' ? 'Perlu pemeriksaan' : 'Menyiapkan database';
    $('startup-note').hidden = ready;
    $('startup-note').classList.toggle('error', data.state === 'error');
    $('startup-note').textContent = data.message;
    $('document-count').textContent = ready ? data.documents.toLocaleString('id-ID') : '—';
    if (data.model) $('runtime-label').textContent = 'SBERT + BM25 · ' + data.model.device.toUpperCase() + ' · Lokal';
    updateButton();
    if (data.state === 'loading') window.setTimeout(status, 1800);
  } catch (_) {
    ready = false;
    $('connection').className = 'connection error';
    $('connection-text').textContent = 'Koneksi terputus';
    $('startup-note').hidden = false;
    $('startup-note').className = 'startup-note error';
    $('startup-note').textContent = 'Aplikasi belum terhubung. Pastikan server Python tetap berjalan; koneksi akan dicoba kembali.';
    updateButton();
    window.setTimeout(status, 4000);
  }
}
function countDescription() { $('description-count').textContent = $('description').value.length.toLocaleString('id-ID') + ' karakter'; }
async function fillExample() {
  try {
    const query = await request('/api/example');
    for (const key of ['title', 'description', 'problem', 'method', 'dataset']) $(key).value = query[key] || '';
    document.querySelector('.optional-fields').open = true;
    countDescription();
    error('');
    $('title').focus({ preventScroll: true });
    if (window.innerWidth < 761) $('search-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) { error(err.message); }
}
function scoreRow(table, label, value, digits = 3) {
  const row = element('tr'); row.append(element('td', '', label), element('td', '', number(value, digits))); table.append(row);
}
function renderCard(row) {
  const card = element('article', 'result-card');
  const head = element('div', 'result-card-head');
  const heading = element('div');
  const deptText = row.department + (row.konsentrasi && row.konsentrasi !== '-' ? ' (' + row.konsentrasi + ')' : '');
  const metaText = [deptText, row.year].filter(Boolean).join(' · ');
  heading.append(element('h3', 'result-title', row.title), element('div', 'result-meta', metaText));
  head.append(element('span', 'rank-number', row.final_rank), heading);
  const scores = element('div', 'result-score');
  scores.append(element('span', 'fusion-score', number(row.hybrid_score, row.config === 'plain_rrf' ? 4 : 3)), element('span', 'score-label', 'Skor ranking'), element('span', 'raw-score', 'SBERT ' + number(row.sbert_raw) + ' · BM25 ' + number(row.bm25_raw, 2)));
  card.append(head, scores);
  const comparison = row.aspect_comparison;
  const tags = element('div', 'similarity-tags');
  for (const same of comparison.similarities) {
    const values = same.values.length > 4 ? [...same.values.slice(0, 4), '…'] : same.values;
    tags.append(element('span', 'tag', (aspectNames[same.aspect] || same.aspect) + ': ' + values.join(', ')));
  }
  card.append(tags.childElementCount ? tags : element('p', 'no-aspect', 'Kesamaan aspek belum dikonfirmasi.'));
  const details = element('details', 'result-detail');
  details.append(element('summary', '', 'Lihat bukti dan rincian skor'));
  const content = element('div', 'detail-content');
  content.append(element('p', '', row.explanation));
  content.append(element('h4', '', 'Bukti kesamaan aspek'));
  if (!comparison.similarities.length) content.append(element('p', '', 'Belum ada kecocokan aspek yang didukung aturan.'));
  for (const same of comparison.similarities) {
    const quote = element('blockquote', 'evidence-block');
    quote.append(element('strong', '', aspectNames[same.aspect] || same.aspect));
    const seen = new Set();
    for (const item of same.document_evidence) {
      if (!seen.has(item.evidence) && seen.size < 2) { quote.append(element('div', '', item.evidence)); seen.add(item.evidence); }
    }
    content.append(quote);
  }
  if (comparison.differences.length) {
    content.append(element('h4', '', 'Perbedaan istilah yang teramati'));
    for (const diff of comparison.differences) {
      const q = [...new Set(diff.query_evidence.map(i => i.canonical))].join(', ');
      const d = [...new Set(diff.document_evidence.map(i => i.canonical))].join(', ');
      content.append(element('p', '', (aspectNames[diff.aspect] || diff.aspect) + ' — proposal: ' + q + '; dokumen: ' + d + '.'));
    }
    content.append(element('p', '', 'Istilah yang berbeda belum membuktikan seluruh aspek penelitian berbeda.'));
  }
  content.append(element('h4', '', 'Aspek belum diketahui'));
  content.append(element('p', '', comparison.unknown.length ? comparison.unknown.map(k => aspectNames[k] || k).join(' · ') : 'Tidak ada aspek unknown pada perbandingan ini.'));
  content.append(element('h4', '', 'Potongan teks yang dibandingkan'));
  for (const evidence of row.evidence) {
    const block = element('blockquote', 'evidence-block');
    const section = evidence.section === 'title_abstract' ? 'Judul + abstrak' : 'Ruang lingkup';
    block.append(element('strong', '', section + (evidence.truncated ? ' · dipotong sesuai batas token' : '')));
    block.append(element('div', '', evidence.text));
    const queryText = evidence.query_text || evidence.query_chunk?.text;
    if (queryText) block.append(element('p', '', 'Potongan proposal: ' + queryText));
    content.append(block);
  }
  content.append(element('h4', '', 'Jejak perhitungan'));
  const table = element('table', 'score-table');
  table.setAttribute('aria-label', 'Rincian skor kandidat');
  scoreRow(table, 'SBERT / cosine dokumen', row.sbert_raw);
  scoreRow(table, 'BM25 mentah', row.bm25_raw, 2);
  scoreRow(table, 'Semantik setelah transformasi', row.semantic_transformed, 5);
  scoreRow(table, 'BM25 setelah transformasi', row.bm25_transformed, 5);
  scoreRow(table, 'Kontribusi semantik', row.semantic_contribution, 5);
  scoreRow(table, 'Kontribusi BM25', row.bm25_contribution, 5);
  scoreRow(table, 'Skor hybrid', row.hybrid_score, 5);
  scoreRow(table, 'Skor aspek (penjelasan)', row.aspect_score);
  content.append(table, element('p', '', 'Peringkat hybrid ' + row.hybrid_rank + ' → peringkat akhir ' + row.final_rank + '. Reranking aspek nonaktif.'));
  content.append(element('h4', '', 'Sumber dokumen'));
  content.append(element('p', 'source-line', 'ID: ' + row.id));
  for (const source of row.sources) {
    content.append(element('p', 'source-line', [source.file, source.sheet, 'baris ' + source.row, source.repository_id ? 'repositori ' + source.repository_id : ''].filter(Boolean).join(' · ')));
  }
  details.append(content); card.append(details);
  return card;
}
function render(result) {
  currentResult = result;
  $('results-list').replaceChildren(...result.results.map(renderCard));
  $('result-count').hidden = false;
  $('result-count').textContent = result.results.length;
  $('results-toolbar').hidden = false;
  $('result-meta').textContent = names[result.config] + ' · ' + result.documents_searched + ' dokumen · ' + number(result.elapsed_ms / 1000, 2) + ' detik';
  $('query-caption').hidden = false;
  $('query-caption').textContent = 'Proposal: ' + result.request.query.title;
  $('empty-state').hidden = true;
  if (!result.results.length) {
    const empty = element('div', 'empty-state');
    empty.append(element('h3', '', 'Belum ada kandidat dengan sinyal positif'), element('p', '', 'Tambahkan konteks atau istilah penelitian yang lebih informatif, lalu coba lagi.'));
    $('results-list').append(empty);
  }
}
async function search(event) {
  event.preventDefault();
  if (busy || !ready || !$('search-form').reportValidity()) return;
  busy = true; error(''); updateButton();
  $('results-panel').setAttribute('aria-busy', 'true');
  $('empty-state').hidden = true;
  $('results-list').hidden = true;
  $('search-progress').hidden = false;
  $('results-toolbar').hidden = true;
  $('query-caption').hidden = true;
  $('result-count').hidden = true;
  const query = Object.fromEntries(['title', 'description', 'problem', 'method', 'dataset'].map(key => [key, $(key).value.trim()]));
  const payload = { query, configuration: document.querySelector('input[name="configuration"]:checked').value, top_k: Number($('top-k').value) };
  try {
    const result = await request('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    render(result);
    if (window.innerWidth < 761) $('results-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    error(err.message);
    if (currentResult) render(currentResult); else $('empty-state').hidden = false;
  } finally {
    busy = false; updateButton();
    $('results-panel').setAttribute('aria-busy', 'false');
    $('search-progress').hidden = true;
    $('results-list').hidden = false;
  }
}
function download(type) {
  if (!currentResult) return;
  let data;
  if (type === 'json') data = JSON.stringify(currentResult, null, 2);
  else {
    const fields = ['id', 'title', 'department', 'year', 'config', 'hybrid_rank', 'final_rank', 'sbert_raw', 'bm25_raw', 'semantic_transformed', 'bm25_transformed', 'semantic_contribution', 'bm25_contribution', 'hybrid_score', 'aspect_score', 'rerank_strength', 'sources', 'aspect_comparison', 'evidence'];
    const cell = value => {
      let text = typeof value === 'object' ? JSON.stringify(value) : String(value ?? '');
      if (/^[=+@-]/.test(text)) text = "'" + text;
      return '"' + text.replaceAll('"', '""') + '"';
    };
    data = '\uFEFF' + [fields.join(','), ...currentResult.results.map(row => fields.map(key => cell(row[key])).join(','))].join('\r\n');
  }
  const blob = new Blob([data], { type: type === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = 'hasil-skripsi-' + currentResult.config + '.' + type;
  document.body.append(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('search-form').addEventListener('submit', search);
$('description').addEventListener('input', countDescription);
$('example-button').addEventListener('click', fillExample);
$('empty-example-button').addEventListener('click', fillExample);
$('export-json').addEventListener('click', () => download('json'));
$('export-csv').addEventListener('click', () => download('csv'));
status();
