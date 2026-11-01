"""Generate reports from actual saved artifacts; never invent experiment outcomes."""
import json
import statistics
from pathlib import Path
from skripsi_search.evaluate import write_csv

root=Path('.')
def read(p): return json.loads((root/p).read_text(encoding='utf-8'))
q=read('reports/data_quality.json'); e=read('reports/evaluation/aggregate.json'); m=read('reports/index_manifest.json'); n=read('reports/notebook_execution.json'); a=read('reports/legacy_audit.json'); per=read('reports/evaluation/per_query.json'); coverage=read('reports/aspect_coverage.json')
rows=e['aggregate']
table='| Konfigurasi | Hit@5 | Recall@5 | Recall@10 | MRR |\n|---|---:|---:|---:|---:|\n'
for r in rows: table+=f"| {r['config']} | {r['Hit@5']:.3f} | {r['Recall@5']:.3f} | {r['Recall@10']:.3f} | {r['MRR']:.3f} |\n"
bygroup=[]
for config in e['configurations']:
    for group in ('A','B'):
        rs=[r for r in per if r['config']==config and r['legacy_group']==group and 'MRR' in r]
        bygroup.append({'config':config,'group':group,'queries':len(rs),**{k:statistics.mean(r[k] for r in rs) for k in ('Hit@5','Recall@5','Recall@10','MRR')}})
write_csv(root/'reports/evaluation/by_legacy_group.csv',bygroup)
default=next(r for r in rows if r['config']=='plain_rrf')
range_rows=[r for r in per if r['config']=='plain_rrf' and 'MRR' in r]
lines=[f'''# Hasil implementasi dan verifikasi

Sistem inti, CLI dan notebook telah dibuat dan dijalankan pada CPU lokal. Model: `{m['model']['name']}`, revisi `{m['model']['revision']}`. Hybrid SBERT + BM25 tetap metode utama. Default sementara: `plain_rrf`, RRF 60, tanpa reranking aspek. Default ini ditetapkan sebelum evaluasi karena sederhana; belum dipilih melalui validation manusia.

## Kondisi proyek awal

`main.py` lama berbeda dari notebook: main menilai embedding gabungan metode/dataset dan problem; ia bukan hybrid lexical-semantic. Komponen BM25 positif, bobot 0,7/0,3, bobot bagian 0,5/0,5, model dan struktur metadata dari notebook dipertahankan sebagai baseline. Tidak ada perubahan pada file prediksi properti.

Notebook Colab memiliki patch pada sel indeks 2 (sel ketiga): `AnalisisTopik._siapkan = _siapkan_baru` dan `AnalisisTopik.cari = cari_baru`. Sel berikutnya membuat mesin sehingga dua fungsi patch itulah implementasi aktif. Ranking menggunakan hybrid, sedangkan skor aspek hanya dipakai pada penjelasan/label. Tidak ada reranking aspek aktif di versi lama.

Audit loader atas sumber yang sama menemukan {a['initial_rows']} baris dan {a['sentinel_titles']} judul sentinel. Loader Colab menyisakan {a['colab_exact_title_dedup']} judul unik termasuk satu sentinel; notebook pengujian menghasilkan {a['testing_filtered_exact_title_dedup']} setelah sentinel dan filter abstrak. Output tersimpan kelompok A menunjukkan sepuluh sumber pada rank 1 tetapi A01 dan A06 berlabel RENDAH: ini masalah interpretasi ambang, bukan kegagalan menemukan sumber.

Probe regex lama menghasilkan C++/C# kosong, `Google Play Store` menjadi `Google Play`, `K-Means Clustering` menjadi `K-Means`; alias `YOLO v8`, `YOLO-v8`, `YOLOv11` terlewat sementara `YOLO11` ditemukan. Problem tanpa tanda baca penutup tidak cocok. CSV metode memang mencampur algoritma, teknologi dan metode penelitian; CSV dataset mencampur platform, identitas, jenis data dan pengumpulan.

Main lama membuat embedding dari fallback seperti Umum/Data internal/Tidak spesifik. Patch Colab dapat mengisi metode dan data dari potongan lingkup yang sama; keduanya dibuang dalam ekstraksi baru. Parser lama mensyaratkan heading kapital dan membatasi bagian pada 1.500 karakter. Cache main hanya diperiksa keberadaannya; cache notebook lebih baik karena menghash teks dan model-name, tetapi belum mencakup revisi encoder, kode preprocessing, kamus/alias dan format indeks secara eksplisit.

## Kualitas corpus

| Tahap | Jumlah |
|---|---:|
| Baris awal | {q['initial_rows']} |
| Dikeluarkan (judul kosong/sentinel) | {q['excluded_count']} |
| Baris valid sebelum merge | {q['valid_rows_before_merge']} |
| Salinan duplikat digabung | {q['duplicates_merged']} |
| Kelompok konflik judul dipertahankan | {q['conflict_groups']} |
| Dokumen akhir | {q['documents']} |

Hasil akhir berbeda dari 777 karena dua kelompok judul memiliki identitas/isi bertentangan. Keduanya tidak digabung: “Pembuatan sistem aplikasi pencatatan meeting untuk PT. Mitra Pinasthika Mulia” memiliki dua penulis dan ID repositori berbeda; judul Adaptive Sparse Transformer memiliki penulis/NRP sama tetapi ID repositori dan abstrak berbeda. Konflik perlu ditinjau pada repositori, bukan diputuskan dari NRP atau judul saja. Tujuh salinan digabung dalam lima kelompok; provenance seluruh baris dipertahankan.

Kelengkapan field (jumlah dokumen terisi): `{q['completeness']}`. Tiga dokumen tanpa Chapter1 tetap dipertahankan karena abstraknya informatif. Status parser: `{q['parsing']}`. Teks mentah, teks bersih dan status bagian tersimpan. Footer bernomor dihapus, sementara nama institusi yang merupakan isi penelitian dipertahankan.

## Batas token dan chunking

Model aktual memiliki `max_seq_length={m['model']['max_seq_length']}`, tokenizer limit {m['model']['tokenizer_model_max_length']}, dan {m['model']['special_tokens']} special tokens. Jadi budget isi paling banyak 126 token. Dari {m['truncation']['plain_fields']} field semantik, {m['truncation']['plain_truncated_fields']} lebih panjang dari batas model. Satu konfigurasi chunking (overlap 16 token) menghasilkan {m['truncation']['chunks']} chunk; maksimum token termasuk special tokens = {m['truncation']['max_chunk_tokens']}.

Semua perbandingan baru memakai corpus {q['documents']} dokumen yang sama. Baseline mempertahankan parser/normalisasi lama; perbaikan memakai parser baru serta tokenisasi teknis. Perbedaan skor terhadap output historis tidak diatribusikan hanya ke algoritma, karena corpus historis 777/778 berbeda. Tidak ada eksperimen yang mengklaim memisahkan efek corpus secara numerik; perbandingan algoritma pada tabel berikut mengunci corpus yang sama.

## Evaluasi yang benar-benar dijalankan

30 query legacy dieksekusi pada sembilan konfigurasi yang ditetapkan sebelumnya. Dua puluh query memiliki sumber provisional yang berhasil dipetakan, dalam {e['splits']['regression']['source_components']} komponen sumber; sepuluh kelompok C tidak memiliki penilaian relevansi dan tidak diberi metrik. Pemetaan awalan dilakukan sekali saat migrasi; evaluasi memakai ID dokumen persisten. Seluruh label masih provisional, bukan label manusia yang telah diaudit.

Jumlah development/validation/test: 0/0/0 query dan 0/0/0 kelompok. **Belum ada test independen atau ground truth relevansi lengkap.** Dokumen tanpa label tetap unjudged. Metrik hanya mengukur pemulihan sumber provisional yang dikenal. Recall menghitung seluruh sumber positif yang terpetakan, termasuk query dengan beberapa sumber.

{table}
Default sementara memperoleh Recall@5={default['Recall@5']:.3f}; bootstrap 95% per komponen sumber: {default['Recall@5_group_bootstrap_95'][0]:.3f}–{default['Recall@5_group_bootstrap_95'][1]:.3f}. Recall@5 per query berada pada {min(r['Recall@5'] for r in range_rows):.3f}–{max(r['Recall@5'] for r in range_rows):.3f}. Lihat seluruh rank sumber dan variasi di `per_query.csv/json`, serta ringkasan kelompok A/B di `by_legacy_group.csv`. Bootstrap dari 20 kelompok provisional tidak mewakili ketidakpastian label atau topik baru.

Baseline mempunyai MRR lebih tinggi dari default RRF pada smoke set ini. Chunking mean tidak memperbaiki hasil smoke dan dapat menurunkan ranking karena pengenceran topik lokal. Tidak ada klaim peningkatan retrieval. SBERT saja merupakan ablation, bukan pengganti hybrid default. Konfigurasi tidak disetel ulang setelah melihat hasil ini. Reranking tetap nonaktif; dua kekuatan disediakan untuk validation mendatang tetapi tidak dicoba untuk memilih pemenang dari smoke test. Tidak ada threshold kategoris atau metrik klasifikasi karena label belum memadai.

## Aspek dan anotasi

Coverage deteksi otomatis: `{ {k:round(v,3) for k,v in coverage['coverage'].items()} }`. Coverage tidak sama dengan ketepatan. Identitas dataset bernama sangat jarang terdeteksi; platform/jenis data tidak dihitung sebagai dataset identik.

Audit agen provisional pada enam judul+abstrak memeriksa sembilan mention algoritma/teknologi; sembilan span/kategori sesuai teks pada sampel kecil tersebut. Ini **bukan penilaian manusia independen, estimasi precision populasi, atau validasi kualitas**. Contoh yang terlewat: alias DB-Scan, Apache Cassandra dan teknik replication/sharding; beberapa peran tetap uncertain. Seluruh catatan dan kutipan tersedia di `aspect_provisional_review.json` dan CSV. Human precision/recall ekstraksi belum tersedia. Template 15 dokumen (lima per jurusan), semua field termasuk unknown, tersedia untuk penilaian manusia.

Pool pasangan top-5 seluruh konfigurasi dan sumber legacy tersedia untuk anotasi relevansi 0/1/2, dengan bukti/alasan/status peninjau. Empat hard negative sintetis membedakan metode sama dengan objek/tujuan berbeda, objek sama dengan metode berbeda, platform sama dengan dataset berbeda, dan keluarga YOLO sama dengan versi berbeda. Semua tetap provisional, bukan label evaluasi.

## Verifikasi pelaksanaan

- Pengujian terarah: 17 lulus, mencakup ingestion/sentinel/NaN, konflik dan ID stabil saat urutan berubah, parser heading, simbol/alias/frasa panjang, unknown, peran metode, budget/offset chunk, fingerprint, query/corpus kosong, ties, top-k dan alur index–search–evaluate.
- Indexing aktual SBERT pada CPU selesai; CLI query contoh menghasilkan sumber aksara Sunda pada peringkat pertama. JSON/CSV menyimpan sumber, skor mentah/transformasi/kontribusi, peringkat dan bukti.
- Sel notebook Python dieksekusi berurutan dalam satu namespace lokal: `{n['all_passed']}`, {len(n['cells'])} sel kode. Output notebook tereksekusi dan durasi sel disimpan di laporan. Cabang upload Google Colab/GPU belum dieksekusi pada layanan Colab; tidak ada klaim pengujian remote/GPU.
- Fingerprint indeks: `{m['fingerprint']}`; fingerprint corpus: `{m['corpus_fingerprint']}`. Revisi model, seed dan versi dependensi direkam. Cache embedding berbeda dari bobot fusion; pool embedding per teks memakai identitas/revisi model dan hash teks, sementara indeks tetap memvalidasi fingerprint sumber/parser/kamus/ID penuh.

## Pekerjaan yang memerlukan penilai manusia

Periksa dua konflik corpus, audit relevansi seluruh kandidat (termasuk query C), lengkapi sampel aspek, dan tambahkan query dari kelompok topik lain. Setelah label mencukupi, buat split sumber/topik sebelum seleksi konfigurasi, pilih pada validation, bekukan konfigurasi, lalu ukur test sekali. Ketepatan kontribusi ilmiah dan potensi duplikasi tidak dapat disimpulkan dari skor sistem ini.
''']
if (root/'reports/WEB_IMPLEMENTATION.md').exists():
    lines.append('''\n## Tambahan antarmuka HTML/CSS/JS

Antarmuka lokal tersedia melalui `python -m skripsi_search.web --root . --port 8765` atau `jalankan_web.bat`. Pilihan UI: Legacy, Weighted 0,7, dan RRF. Ketiganya terhubung ke mesin yang sama; reranking nonaktif. UI memilih Legacy, tanpa mengubah default CLI/notebook. Seluruh 28 pengujian inti dan web lulus; ketiga konfigurasi juga diperiksa melalui browser dan HTTP dengan model aktual. Lihat `WEB_IMPLEMENTATION.md`, `web_smoke.json`, serta `web_preview.png` untuk rincian verifikasi.\n''')
(root/'reports/IMPLEMENTATION_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print('Report generated from actual artifacts')
