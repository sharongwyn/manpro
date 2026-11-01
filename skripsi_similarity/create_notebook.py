"""Build one sequential notebook; no redefinitions or monkey patches."""
import json
from pathlib import Path

cells=[]
def md(s): cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
def code(s): cells.append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':s.splitlines(True)})
md('''# Pencarian Kemiripan Skripsi — SBERT + BM25
Jalankan sel berurutan. CPU didukung, CUDA dipilih otomatis jika tersedia. Tidak ada API berbayar.
Upload `skripsi_similarity.zip` hasil proyek (berisi modul, data, kamus, dan evaluasi) ke Colab.
Skor bukan persentase plagiarisme atau bukti orisinalitas. Label kategoris belum dikalibrasi.
Notebook ini memakai modul yang sama dengan CLI, tanpa patch tersembunyi.
''')
code('''# 1. Lokasi proyek. Pada Colab upload ZIP; lokal jalankan dari folder proyek.
from pathlib import Path
import os, sys, zipfile
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
if IN_COLAB:
    from google.colab import files
    if not Path('/content/skripsi_similarity/sources.json').exists():
        uploads = files.upload()
        name = next(n for n in uploads if n.endswith('.zip'))
        with zipfile.ZipFile(name) as z:
            target = Path('/content').resolve()
            if any(not (target / n).resolve().is_relative_to(target) for n in z.namelist()):
                raise ValueError('ZIP memiliki path tidak valid')
            z.extractall(target)
    ROOT = Path('/content/skripsi_similarity')
else:
    ROOT = Path.cwd()
    if not (ROOT/'sources.json').exists(): ROOT = ROOT/'skripsi_similarity'
assert (ROOT/'sources.json').exists(), 'Jalankan notebook dari folder proyek'
os.chdir(ROOT)
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
print(ROOT)
''')
code('''# 2. Dependensi (internet hanya diperlukan saat instalasi/unduhan model pertama).
import subprocess
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'])
''')
code('''# 3. Ingestion dengan daftar sumber eksplisit dan laporan kualitas.
import json
from skripsi_search.ingest import read_sources, write_json
sources = json.loads(Path('sources.json').read_text())
docs, quality = read_sources(sources, ROOT)
write_json('reports/data_quality.json', quality)
write_json('reports/corpus.json', docs)
print({k:quality[k] for k in ['initial_rows','valid_rows_before_merge','documents','excluded_count','duplicates_merged','conflict_groups']})
print(quality['parsing'])
''')
code('''# 4. Model aktual, tokenizer, embedding cache, serta indeks BM25.
from skripsi_search.engine import load_index
index = load_index(ROOT)
print(index.encoder.info)
print(index.truncation)
print('Fingerprint:', index.fingerprint)
''')
code('''# 5. Input proposal. Judul/deskripsi utama; field lain opsional.
query = {
    'title': 'Aplikasi pembelajaran aksara Sunda dengan pengenalan karakter',
    'description': 'Media interaktif untuk membantu generasi muda belajar aksara Sunda dari gambar tulisan tangan.',
    'problem': '',
    'method': 'EfficientNetV2B0 dan YOLOv8',
    'dataset': 'Gambar aksara Sunda dari dataset publik dan responden'
}
settings = json.loads(Path('default_config.json').read_text())
result = index.search(query, top_k=5, config=settings['configuration'], rerank=settings['rerank_strength'])
from skripsi_search.evaluate import write_csv
write_json('reports/search_notebook.json', result)
write_csv('reports/search_notebook.csv', result['results'])
import pandas as pd
display(pd.DataFrame(result['results'])[['final_rank','id','title','department','year','sbert_raw','bm25_raw','hybrid_score']].round(3))
print(result['interpretation'])
''')
code('''# 6. Bukti aspek terpisah dari bukti passage; seluruh detail ada pada JSON audit.
for row in result['results']:
    print('\\n', row['final_rank'], row['title'])
    print('Sama:', [(x['aspect'],x['values']) for x in row['aspect_comparison']['similarities']])
    print('Unknown:', row['aspect_comparison']['unknown'])
    print('Perbedaan teramati:', [x['aspect'] for x in row['aspect_comparison']['differences']])
    for evidence in row['evidence']:
        print(evidence['section'], evidence['start'], evidence['end'], evidence['text'])
''')
md('''## Evaluasi awal
30 proposal lama hanya regression/smoke test. Sumber dipetakan sekali dan disimpan sebagai ID.
Label lama belum ditinjau manusia. Dokumen tanpa label tetap unjudged. Tidak ada test independen.
Default sederhana ditetapkan sebelum evaluasi; hasil smoke tidak dipakai memilih konfigurasi.
Sembilan konfigurasi: baseline lama, SBERT, BM25, serta enam hybrid yang ditentukan sebelumnya.
Reranking dan ambang kategoris tetap dinonaktifkan sampai ada validation manusia memadai.
''')
code('''# 7. Jalankan regression yang tersedia dan buat lembar anotasi.
from skripsi_search.evaluate import run_evaluation
report = run_evaluation(index, ROOT)
display(pd.DataFrame(report['aggregate']))
print(report['splits'])
print(report['scope'])
''')
code('''# 8. Pengujian terarah.
subprocess.check_call([sys.executable, '-m', 'pytest', '-q'])
''')
code('''# 9. Contoh CLI menggunakan indeks yang sama.
subprocess.check_call([sys.executable, '-m', 'skripsi_search', 'search',
                       '--title', query['title'], '--description', query['description'],
                       '--method', query['method'], '--dataset', query['dataset'],
                       '--output', 'reports/search_cli_colab.json'])
''')
md('''Isi `evaluation/relevance_annotation.csv` dengan relevansi 0/1/2, bukti, alasan, reviewer, dan `review_status=human_reviewed`.
Jangan menimpa hasil anotasi asli ketika menjalankan ulang evaluasi: salin lembar terisi ke nama baru.
Gunakan `evaluate --annotations evaluation/relevance_reviewed.csv` untuk metrik judged-only.
Lihat README untuk kebijakan kelompok sumber, batasan, cache, dan reproduksi lokal.
''')
for i,cell in enumerate(cells): cell['id']=f'skripsi-cell-{i:02d}'
nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'},'colab':{'name':'Pencarian_Kemiripan_Skripsi.ipynb'}},'nbformat':4,'nbformat_minor':5}
Path('Pencarian_Kemiripan_Skripsi.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')

if __name__=='__main__': print('Notebook built:',len(cells),'cells')
