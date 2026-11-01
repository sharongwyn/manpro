import re

# Game 
GAME = [
    "game", "war game", "serious game", "space shooter", "dynamic difficulty adjustment", "action adventure", 
    "game mobile", "Unity", "tactical shooter", "multiplayer online", "metaverse", "virtual tour", "NPC", "VR", "virtual reality", "procedural content generation"
]

# Cyber Security
CYBER = [
    # Spesifik Cyber
    ("password", 3), ("enkripsi", 3), ("encryption", 3), ("honey encryption", 3),
    ("steganografi", 3), ("steganography", 3), ("spread spectrum", 3),
    ("digital signature", 3), ("phishing", 3), ("fake account", 3),
    ("reputasi akun", 3), ("verifikasi ijazah", 3), ("legalitas ijazah", 3),
    ("malware", 3), ("ransomware", 3), ("intrusion detection", 3),
    ("firewall", 3), ("honeypot", 3), ("forensic", 3), ("forensik", 3),
    ("digital forensics", 3), ("incident response", 3), ("antivirus", 3),
    ("cryptography", 3), ("kriptografi", 3), ("privasi", 3), ("privacy", 3),
    ("penetration testing", 3), ("pentest", 3), ("exploit", 3),
    ("security", 3), ("keamanan", 3), ("vulnerability", 3), ("kerentanan", 3),
    
    # Autentikasi & Akses
    ("authentication", 2), ("autentikasi", 2), ("authorization", 2), ("otorisasi", 2),
    ("biometrik", 2), ("biometric", 2), ("access control", 2), ("single sign-on", 2),
    ("multi-factor", 2), ("attack", 2), ("threat", 2), ("ancaman", 2), ("serangan", 2),
    ("risk assessment", 2), ("blockchain", 1), ("smart contract", 1),
    
    # Umum
    ("hash", 1), ("secure", 1)
]

CYBER_CASE_SENSITIVE = [
    ("AES", 3), ("RSA", 3), ("SHA-256", 3), ("IDS", 3), ("IPS", 3), 
    ("SIEM", 3), ("SOC", 3), ("OTP", 2), ("VPN", 2), ("DDoS", 3), ("XSS", 3)
]

# Artificial Intelligence (AI)
AI = [
    # Algoritma
    ("yolov4-tiny", 3), ("yolov4", 3), ("vgg16", 3), ("faster r-cnn", 3),
    ("xception", 3), ("inception-resnet-v2", 3), ("resnet", 3), ("bert", 3),
    ("bilstm", 3), ("lstm", 3), ("gru", 3), ("transformer", 3), ("pix2pix", 3),
    ("cgan", 3), ("gan", 3), ("random forest", 3), ("xgboost", 3), ("c5.0", 3),
    ("decision tree", 3), ("naive bayes", 3), ("k-means", 3), ("arima", 3),
    ("textrank", 3), ("lda", 3), ("tf-idf", 3), ("word2vec", 3), ("infersent", 3),
    ("siamese network", 3), ("neat", 3), ("reinforcement learning", 3),
    ("deep learning", 3), ("machine learning", 3), ("artificial intelligence", 3),
    ("kecerdasan buatan", 3), ("pembelajaran mesin", 3), ("neural network", 3),
    ("natural language processing", 3), ("pemrosesan bahasa alami", 3),
    ("collaborative filtering", 3), ("content-based", 3),("YOLO", 3), ("YOLOv12", 3),
    
    # Domain AI
    ("computer vision", 3), ("object detection", 3), ("pose estimation", 3),
    ("lip reading", 3), ("hand gesture", 3), ("pengenalan rambu", 3),
    ("pengenalan wajah", 3), ("face recognition", 3), ("sentiment analysis", 3),
    ("analisis sentimen", 3), ("aspect-based", 3), ("text classification", 3),
    ("text summarization", 3), ("topic labeling", 3), ("chatbot", 3), ("intent", 3),
    ("essay scoring", 3), ("transkripsi musik", 3), ("deteksi objek", 3),
    ("sistem rekomendasi", 3), ("recommender", 3), ("recommendation system", 3),
    
    # Istilah Umum
    ("klasifikasi", 2), ("classification", 2), ("klasterisasi", 2), ("clustering", 2),
    ("segmentasi", 2), ("segmentation", 2), ("forecasting", 2), ("prediksi", 2),
    ("peramalan", 2), ("rekomendasi", 2)
]

AI_CASE_SENSITIVE = [
    ("CNN", 3), ("3D CNN", 3), ("SVM", 3), ("KNN", 3), ("NLP", 3),
    ("OCR", 3), ("LLM", 3), ("GAN", 3)
]

def compile_kw(keyword, case_sensitive=False):
    escaped_kw = re.escape(keyword)
    pattern = r"(?<![A-Za-z0-9])" + escaped_kw + r"(?![A-Za-z0-9])"
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)

GAME_RE = [compile_kw(k) for k in GAME]

CYBER_RE = [(compile_kw(k), w, k) for k, w in CYBER] + \
           [(compile_kw(k, True), w, k) for k, w in CYBER_CASE_SENSITIVE]

AI_RE = [(compile_kw(k), w, k) for k, w in AI if k not in {kk.lower() for kk, _ in AI_CASE_SENSITIVE}] + \
        [(compile_kw(k, True), w, k) for k, w in AI_CASE_SENSITIVE]

THRESHOLD = 2  # Skor minimal untuk masuk kategori Cyber / AI

def skor(judul, daftar):
    total, ditemukan = 0, []
    for rx, bobot, nama in daftar:
        if rx.search(judul):
            total += bobot
            ditemukan.append(nama)
    return total, ditemukan

def klasifikasi(judul):
    """
    Mengklasifikasikan judul skripsi ke dalam konsentrasi:
    'Game', 'Cyber', 'AI', atau 'Full Stack'
    """
    judul = str(judul)

    # Prioritas 1: Game
    for rx in GAME_RE:
        if rx.search(judul):
            return "Game", rx.pattern

    # Prioritas 2: Cyber dan AI
    s_cyber, k_cyber = skor(judul, CYBER_RE)
    s_ai, k_ai = skor(judul, AI_RE)

    if s_cyber >= THRESHOLD and s_cyber >= s_ai:
        return "Cyber", ", ".join(k_cyber)
    if s_ai >= THRESHOLD:
        return "AI", ", ".join(k_ai)

    # Default / Sisa otomatis Full Stack
    return "Full Stack", ""