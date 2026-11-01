# Pencarian kemiripan skripsi: Hybrid SBERT + BM25

Proyek Python/Colab untuk mencari kandidat skripsi relevan, dengan exact cosine NumPy dan BM25. Model tunggal: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Tidak ada API berbayar atau vector database. Antarmuka HTML memakai server lokal Python sederhana sebagai penghubung ke mesin pencarian. File sumber disalin utuh ke `reference/`; proyek asal tidak diubah.

## Tampilan HTML, CSS, dan JavaScript

Antarmuka lokal tersedia untuk memasukkan proposal, memilih konfigurasi, melihat bukti, dan mengunduh JSON/CSV. Dari folder proyek setelah dependensi terpasang:

```bash
python -m skripsi_search.web --root . --port 8765
```

Buka `http://127.0.0.1:8765` pada browser. Windows juga dapat menjalankan `jalankan_web.bat`. Tunggu indikator **Database siap**; model dan indeks dimuat sekali pada awal proses. Tekan Ctrl+C pada terminal untuk menghentikan server. HTML/CSS/JS berada di `skripsi_search/web_static/`. Server penghubung memakai pustaka standar Python, tanpa dependensi web tambahan; file HTML perlu dibuka melalui server tersebut agar pencarian dapat berjalan.

Pilihan antarmuka dibatasi pada **Legacy (`legacy`), Weighted 0,7 (`plain_w07`), dan RRF (`plain_rrf`)**, tiga konfigurasi hybrid terbaik pada evaluasi awal. Ini tiga konfigurasi fusion, bukan tiga encoder berbeda. Semua memakai model SBERT yang sama. UI memilih Legacy saat awal dibuka sesuai hasil evaluasi awal; default CLI/notebook pada `default_config.json` tetap `plain_rrf`. Reranking aspek nonaktif pada ketiga pilihan UI. Skor fusion konfigurasi berbeda tidak boleh dibandingkan sebagai persentase kemiripan; bandingkan urutan dan bukti kandidat.

Gunakan **Isi contoh**, pilih konfigurasi dan jumlah kandidat, lalu klik **Cari kemiripan**. Buka **Lihat bukti dan rincian skor** untuk memeriksa potongan teks, aspek cocok/berbeda/unknown, sumber file/sheet/baris, serta skor mentah, transformasi, dan kontribusi fusion. Input proposal tidak ditulis ke berkas atau riwayat; query dan embedding-nya dapat tersimpan dalam cache memori selama proses berjalan. Hasil diunduh hanya ketika tombol ekspor dipilih. Tidak ada pengiriman input ke API eksternal. Endpoint hanya bind ke loopback komputer ini; tidak ada deployment publik.

## Menjalankan lokal

Python 3.10+ (verifikasi lokal memakai Python 3.12, CPU). Dari folder ini:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m skripsi_search ingest
python -m skripsi_search index
python -m skripsi_search search --title "Pengenalan aksara Sunda" --description "Media belajar dari gambar tulisan tangan" --method "EfficientNetV2B0 dan YOLOv8" --top-k 5
python -m skripsi_search evaluate
python -m pytest -q
```

CLI `--root /path/to/project` dipasang sebelum subcommand. Alternatif `pip install -e .` menyediakan perintah `skripsi-search`. `index --rebuild` memaksa encoding ulang. Query dari berkas: `search --query-json evaluation/example_query.json`. Field JSON: `title`, `description`, `problem`, `method`, `dataset`. Query kosong/tanpa istilah informatif ditolak. CPU dipakai bila GPU tidak tersedia; `device` dalam `default_config.json` dapat diisi `cpu` atau `cuda`.

Internet hanya diperlukan saat instalasi dan unduhan pertama model open-source (~480 MB). Revisi model dipin dalam konfigurasi; snapshot lokal dipakai offline setelah tersedia. Tidak ada fallback TF-IDF. Kegagalan model menghasilkan error yang harus diperbaiki, bukan perubahan metode diam-diam.

`requirements.txt` menyediakan rentang lintas platform; `requirements-tested.txt` merekam versi inti yang benar-benar dipakai. `reports/environment.json` mencatat lingkungan lengkap. Pengguna Colab sebaiknya mempertahankan PyTorch bawaan yang sesuai CUDA jika memasang versi CPU lokal tidak diperlukan.

## Google Colab

1. Buka `Pencarian_Kemiripan_Skripsi.ipynb` di Google Colab.
2. Jalankan sel pertama dan upload `skripsi_similarity.zip` yang menyertai proyek.
3. Jalankan seluruh sel berurutan: dependensi → ingestion → indeks → query → bukti → evaluasi → tes → CLI.

Notebook mengimpor fungsi inti yang sama dengan CLI. Tidak ada patch atau fungsi yang didefinisikan ulang. Data, kamus, manifest, dan 30 query sudah di dalam paket. Model dan cache embedding tidak dimasukkan ke ZIP agar ukuran unduhan proyek kecil. Jalankan `python create_notebook.py` hanya jika perlu membangun ulang notebook sumber; notebook hasil eksekusi disimpan terpisah di laporan.

## Data dan provenance

`sources.json` menyebut file, sheet dan jurusan secara eksplisit: DSA/Skripsi, INFOR/Skripsi_Info, SIB/Skripsi_Batch2. Keluaran evaluasi tidak pernah ditemukan lewat glob sebagai corpus. Kolom dinormalisasi; null/sentinel tidak menjadi teks `nan`. Judul dan teks informatif cukup untuk mempertahankan entri meskipun Chapter1 kosong.

Judul ternormalisasi hanya menghasilkan kandidat duplikat. Penggabungan memeriksa ID repositori, penulis, tahun dan abstrak; konflik dipertahankan untuk tinjauan manusia. Di dalam kelompok konflik, salinan yang identik tetap digabung. NRP bukan identitas dokumen. ID menggunakan ID repositori jika tersedia, atau hash judul/identitas konflik; tidak menggunakan urutan baris. Provenance menyimpan file, sheet, baris, ID repositori, NRP dan metadata semua sumber. Teks mentah tetap tersimpan; versi yang digabung memilih field terpanjang secara deterministik dan sumber asli tetap dapat diperiksa.

`reports/data_quality.json` memuat seluruh pengecualian, penggabungan, konflik, jumlah awal/valid/akhir, kelengkapan dan status parsing. `reports/corpus.json` memuat dokumen beserta teks mentah dan parsing. `reports/source_manifest.json` berisi SHA256 berkas asli. `reports/chunks.jsonl` menyimpan seluruh pemetaan chunk, ID stabil, bagian, offset, teks dan posisi vektor chunk untuk audit.

Parser mengenali nomor dengan variasi titik/spasi, heading kapital/kecil, rumusan/perumusan/identifikasi masalah, ruang lingkup dan batasan penelitian. `not_available` berarti tidak ada petunjuk bagian; `parse_failed` berarti istilah bagian ada tetapi isi tidak berhasil diekstrak dari heading. Ini diagnosis heuristik, bukan jaminan bahwa bagian memang ada/tidak ada. Bab 1 belum pernah digunakan seluruhnya sebagai pengganti lingkup yang gagal. Noise footer/nomor halaman dibersihkan secara konservatif; OCR terputus belum direkonstruksi.

## Representasi, chunk dan fusion

Semua eksperimen memakai corpus bersih sama. `legacy` memakai parser, batas 1.500 karakter bagian, tokenisasi lama dan formula notebook aktif: judul+abstrak; lingkup terpisah; 0,5+0,5 bila lingkup ada; BM25 judul+abstrak+lingkup+rumusan; 0,7 semantik + 0,3 BM25/acuan lama (clip 0–1). Acuan lama bergantung panjang query dan menghukum kata OOV; ia bukan batas maksimum matematis maupun probabilitas. Perbedaan dengan output notebook historis mencakup corpus dan parser; tabel eksperimen baru hanya membandingkan algoritma pada corpus yang sama.

Enam hybrid perbaikan ditentukan sebelum pengujian: `plain_rrf`, `plain_w05`, `plain_w07`, `chunk_rrf`, `chunk_w05`, `chunk_w07`. Selain itu `sbert` dan `bm25` menjadi ablation tanpa chunk. Tidak ada grid ukuran chunk.

`plain` mempertahankan struktur dua bagian, tetapi membuang batas karakter buatan dan memakai tokenizer model sebenarnya. Encoder tetap memotong sesuai batas model; jumlah field yang terpotong dilaporkan. `chunk` membagi judul+abstrak dan lingkup per batas token aktual, termasuk special tokens. Overlap 16 token; kalimat dipertahankan bila muat, kalimat sangat panjang dibagi. Setiap chunk menyimpan ID, bagian, offset karakter pada teks bersih, offset token dan jumlah token. Query panjang juga dibagi. Mean embedding setiap bagian dinormalisasi kembali; cosine bagian digabung 0,5+0,5, atau judul+abstrak saja bila lingkup kosong. Skor tidak memakai max atas jumlah chunk, sehingga panjang dokumen tidak otomatis mendapat bonus. Mean dapat mengencerkan topik lokal; bukti passage terbaik ditampilkan terpisah dan tidak disamakan dengan skor dokumen.

Embedding L2-normalized; exact dot product = cosine. BM25 mempertahankan `C++`, `C#`, `Node.js`, `TF-IDF`, dan versi metode. BM25 dengan IDF positif dibuat sekali per versi corpus, bukan per query. Baseline memiliki indeks tokenisasi lama terpisah.

Weighted fusion memakai **midrank ECDF per query untuk kedua channel**, ditetapkan sebelum pengujian: `(jumlah skor lebih kecil + 0,5 × jumlah skor sama) / N`; skor ≤0 ditransformasi ke 0. Bobot semantik 0,5 atau 0,7. Tidak ada statistik yang dipelajari dari test; transformasi relatif terhadap corpus query tersebut, sehingga skor antarquery tetap tidak terkalibrasi. RRF menjumlahkan `1/(60+rank)` dua channel yang memiliki sinyal positif. Ikatan skor diurutkan ID stabil. RRF adalah skor ranking, bukan probabilitas atau persentase kemiripan.

JSON/CSV menyimpan cosine dan BM25 mentah, transformasi, kontribusi masing-masing channel, peringkat hybrid/final, serta bukti. Tabel utama membulatkan angka; berkas audit menyimpan presisi penuh. `--top-k` dibatasi ukuran corpus. Query tanpa kecocokan leksikal masih dapat memiliki sinyal SBERT; `no_positive_signal` menginformasikan bila kedua channel tidak memberi sinyal positif.

## Aspek dan interpretasi

Ekstraktor aturan memakai kamus lama dengan pembagian kategori eksplisit: algoritma, teknologi pendukung, metode penelitian, identitas dataset, platform, jenis data, teknik pengumpulan, objek, masalah/tujuan dan konteks lokasi/populasi/periode. Daftar ini belum lengkap. Kamus dapat dilengkapi di `aspects.py` dan CSV. Alias kanonis, frasa terpanjang dan batas simbol memperbaiki C++/C#, Google Play Store dan versi YOLO. Keluarga YOLO disimpan terpisah dari versi. Penyebutan model dipilah `used`, `prior_work`, `comparison`, `rejected`, atau `uncertain` berdasarkan klausa/kalimat bukti. Kalimat ambigu tetap dapat salah peran; tinjauan manual diperlukan.

`unknown` tidak diisi teks fallback dan tidak pernah dibuat embedding. Kaggle/BPS atau citra saja tidak menjadi identitas dataset yang sama. Kesamaan aturan membandingkan identitas kanonis persis, dengan bukti dari kedua sisi. Perbedaan hanya berarti istilah yang ditemukan berbeda, bukan bukti seluruh penelitian berbeda. Teks masalah yang diparafrasekan bisa tidak cocok sebagai aspek persis meskipun relevan secara semantik. Coverage dan ketepatan ekstraksi dilaporkan terpisah.

Strength aturan bukan probabilitas: peran metode eksplisit 0,9; terdahulu 0,8; pembanding 0,7; uncertain 0,5; observasi dataset/platform 0,8; objek leksikon 0,5. Peran terdahulu/pembanding/ditolak tidak dihitung sebagai metode utama. Skor aspek berbobot algoritma 0,45, identitas dataset 0,30, objek 0,15, masalah 0,05, konteks 0,04, teknologi 0,01, dikalikan kekuatan bukti dan Jaccard identitas. Informasi hilang tidak dihukum; tidak ada bonus teknologi dominan.

Reranking **nonaktif secara default**. Implementasi mendukung maksimal dua kekuatan eksperimental: `--rerank 0.05` dan `--rerank 0.10`. Ambil top-50 hybrid, skala dasar hybrid terhadap maksimum query, tambahkan strength × skor aspek, urutkan hanya pool tersebut. Simpan peringkat sebelumnya/sesudah dan faktor aspek. Ini belum ditetapkan sebagai default karena validation manusia belum memadai; kedua kekuatan belum diuji sebagai eksperimen kualitas pada smoke set.

Skor tidak mengukur plagiarisme, duplikasi atau orisinalitas. Tidak ada ambang 0,60/0,75 dan tidak ada keputusan aman/bahaya. Bukti semantik passage bukan pemeriksaan kutipan/salinan literal. Pada mode chunk, bukti menyimpan pasangan potongan query–dokumen dengan cosine tertinggi; pemilihan bukti ini tidak memengaruhi ranking dokumen yang memakai centroid. Penilaian kontribusi ilmiah dan tujuan memerlukan pembacaan sumber.

## Ground truth dan evaluasi

`prepare_evaluation.py` mengambil literal DATA lewat AST tanpa mengeksekusi notebook lama. Awalan judul hanya dipakai **sekali saat migrasi**, lalu disimpan sebagai ID pada `evaluation/queries.json` dan diaudit di `reports/ground_truth_audit.json`. Label A/B/C lama bersifat provisional. Kelompok C yang dulu disebut orisinal tetap unjudged, bukan negative ground truth. Sumber yang terpetakan juga belum berarti seluruh dokumen relevan sudah ditemukan.

Data saat ini tidak cukup untuk development–validation–test manusia independen. Evaluasi awal memakai komponen sumber terhubung; query yang berbagi salah satu sumber masuk komponen sama. Dokumen sumber tetap berada di indeks. Tidak ada test independen, pemilihan parameter berdasarkan test, atau klaim peningkatan final. Default `plain_rrf` ditetapkan karena sederhana sebelum membaca hasil regression, bukan karena memenangi smoke test.

`reports/evaluation/aggregate.json` dan `per_query.csv/json` mencatat sembilan konfigurasi, seed, versi dependensi, fingerprint corpus/model, jumlah query dan kelompok, variasi per query dan bootstrap per kelompok. Hit@5 berarti satu atau lebih target dikenal ditemukan; Recall@k menghitung proporsi **seluruh target positif berlabel** yang ditemukan. MRR memakai target positif pertama. Query tanpa positif dikenal tidak memiliki metrik, bukan diberi nol. Semua metrik smoke hanya terhadap target provisional yang dipetakan, tidak mengukur recall keseluruhan corpus.

Anotasi bertingkat tersedia pada `evaluation/relevance_annotation.csv`: 0 tidak relevan, 1 berkaitan, 2 sangat relevan. Isi bukti, alasan, reviewer dan `review_status=human_reviewed`. Kolom saran tidak dianggap label manusia. Pool berasal dari top-5 seluruh konfigurasi dan seluruh sumber lama; dokumen di luar pool tetap unjudged. Simpan lembar terisi ke **nama lain** sebelum menjalankan ulang evaluasi:

```bash
python -m skripsi_search evaluate --annotations evaluation/relevance_reviewed.csv
```

Metrik terhadap label manusia akan diekspor ke `human_judged_metrics.csv`, termasuk nDCG@5 dari gain `2^grade−1`. Relevance yang belum dinilai menyumbang nol gain saat menghitung ranking judged-only, tetapi tidak diubah menjadi label negatif; metrik tetap dibatasi pooling. `evaluation/hard_negative_annotation.csv` berisi contoh kontras metode/objek/tujuan/dataset **sintetis provisional** untuk pelatihan penilai, bukan bukti performa. `evaluation/aspect_annotation.csv` menyediakan sampel manual 15 dokumen (lima per jurusan), termasuk aspek unknown untuk mencatat false negative; `reports/aspect_coverage.json` hanya coverage otomatis, precision belum dapat dihitung sebelum anotasi manusia selesai. Tidak ada precision/recall/F1 klasifikasi tanpa label yang memadai.

Template anotasi yang sudah ada tidak ditimpa saat evaluasi dijalankan lagi. Pool terbaru disimpan di `reports/evaluation/relevance_pool_current.csv`; gabungkan pasangan tambahan ke lembar penilaian secara sadar jika corpus berubah. `reports/aspect_provisional_review.json` dan CSV pasangannya mencatat audit kecil oleh agen pada enam judul+abstrak, termasuk contoh yang terlewat. Audit ini **bukan penilaian manusia independen** dan tidak dipakai memilih konfigurasi atau mengklaim ketepatan seluruh corpus.

Setelah label manusia cukup, tentukan split menurut sumber atau kelompok topik **sebelum** eksperimen berikutnya; pilih hybrid pada validation dengan prioritas Recall@5 lalu MRR/nDCG@5, uji dua strength rerank pada validation, bekukan konfigurasi, lalu buka test sekali. Evaluator saat ini sengaja tidak melakukan pemilihan otomatis dari label regression. Kalibrasi ambang juga memerlukan validation untuk konfigurasi/model/representasi yang tepat.

## Cache dan audit

Embedding cache `.embedding_cache/<fingerprint>.npz` terpisah dari fusion. Fingerprint mencakup dokumen beserta urutan ID, isi/hash sumber, model dan revisi, tokenizer/max token, versi/kode preprocessing-parsing, kamus-alias, konfigurasi chunk dan format indeks. Perubahan sumber/kamus/parser memicu cache baru; perubahan bobot fusion tidak memerlukan encoding ulang. File lama tidak dimuat dengan fingerprint berbeda. Snapshot model tersimpan di `.model_cache`. Cache metadata dan ukuran diperiksa saat pemuatan; `--rebuild` tersedia.

Laporan hasil dan keterbatasan aktual ada pada `reports/IMPLEMENTATION_REPORT.md`. `reference/` mempertahankan notebook dengan output asli; `reports/*_cells.txt` menyediakan teks seluruh sel/output untuk inspeksi patch. `audit_legacy.py` membuat audit kebijakan loader dan probe regex lama.
