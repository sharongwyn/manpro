import re

# Game
GAME = [
    # Spesifik Game
    ("game", 3), ("games", 3), ("serious game", 3), ("war game", 3), ("board game", 3),
    ("game based learning", 3), ("game-based learning", 3), ("space shooter", 3), ("tactical shooter", 3),
    ("dynamic difficulty adjustment", 3), ("action adventure", 3), ("roguelike", 3), ("rogue-like", 3),
    ("platformer", 3), ("visual novel", 3), ("role-playing game", 3), ("procedural content generation", 3),
    ("procedural content generator", 3), ("level design", 3), ("non-playable character", 3),
    ("non playable character", 3), ("playtester", 3), ("multiplayer online", 3),

    ("permainan", 1), ("multiplayer", 1), ("unity", 1), ("unreal engine", 1), ("godot", 1), ("metaverse", 1),
    ("virtual reality", 1), ("augmented reality", 1), ("mixed reality", 1), ("virtual tour", 1),
    ("gamifikasi", 1), ("gamification", 1),
]

GAME_CASE_SENSITIVE = [
    ("NPC", 3), ("RPG", 3), ("DDA", 3), ("PCG", 3), ("VR", 1), ("AR", 1)
]

# Cyber Security
CYBER = [
    # Spesifik Cyber
    ("enkripsi", 3), ("dekripsi", 3), ("encryption", 3), ("honey encryption", 3),
    ("steganografi", 3), ("steganography", 3), ("spread spectrum", 3),
    ("digital signature", 3), ("tanda tangan digital", 3), ("phishing", 3), ("phising", 3), ("fake account", 3),
    ("reputasi akun", 3), ("verifikasi ijazah", 3), ("legalitas ijazah", 3),
    ("malware", 3), ("ransomware", 3), ("intrusion detection", 3),
    ("firewall", 3), ("honeypot", 3), ("forensic", 3), ("forensik", 3),
    ("digital forensics", 3), ("incident response", 3), ("antivirus", 3),
    ("cryptography", 3), ("kriptografi", 3),
    ("penetration testing", 3), ("pentest", 3), ("exploit", 3), ("eksploitasi", 3),
    ("vulnerability", 3), ("kerentanan", 3), ("cyber security", 3), ("cybersecurity", 3),
    ("keamanan siber", 3), ("keamanan jaringan", 3), ("keamanan data", 3), ("keamanan website", 3),
    ("keamanan web", 3), ("keamanan informasi", 3), ("keamanan sistem", 3),
    ("brute force", 3), ("sql injection", 3), ("zero trust", 3), ("blockchain", 3), ("smart contract", 3),
    ("owasp", 3), ("seccomp", 3), ("hardening", 3),
 
    # Umum
    ("password", 1), ("kata sandi", 1), ("privasi", 1), ("privacy", 1), ("security", 1), ("keamanan", 1),
    ("authentication", 1), ("autentikasi", 1), ("authorization", 1), ("otorisasi", 1),
    ("biometrik", 1), ("biometric", 1), ("access control", 1), ("kontrol akses", 1), ("single sign-on", 1),
    ("multi-factor", 1), ("attack", 1), ("threat", 1), ("ancaman", 1), ("serangan", 1),
    ("risk assessment", 1), ("hash", 1), ("hashing", 1), ("secure", 1),
]

CYBER_CASE_SENSITIVE = [
    ("AES", 3),
    ("RSA", 3),
    ("SHA-256", 3),
    ("IDS", 3),
    ("SIEM", 3),
    ("SOC", 3),
    ("DDoS", 3),
    ("XSS", 3),
    ("IPS", 1),
    ("OTP", 1),
    ("VPN", 1),
    ("JWT", 1),
]

# Artificial Intelligence (AI)
AI = [
    # Algoritma
    ("yolo", 3),
    ("yolov3", 3),
    ("yolov4", 3),
    ("yolov4-tiny", 3),
    ("yolov5", 3),
    ("yolov7", 3),
    ("yolov8", 3),
    ("yolov9", 3),
    ("yolov10", 3),
    ("yolov11", 3),
    ("yolo11", 3),
    ("yolov12", 3),
    ("you only look once", 3),
    ("vgg16", 3),
    ("faster r-cnn", 3),
    ("efficientnet", 3),
    ("mobilenet", 3),
    ("xception", 3),
    ("inception-resnet-v2", 3),
    ("resnet", 3),
    ("bert", 3),
    ("indobert", 3),
    ("bilstm", 3),
    ("lstm", 3),
    ("gru", 3),
    ("transformer", 3),
    ("pix2pix", 3),
    ("cgan", 3),
    ("random forest", 3),
    ("xgboost", 3),
    ("c5.0", 3),
    ("decision tree", 3),
    ("naive bayes", 3),
    ("k-means", 3),
    ("k-nearest neighbor", 3),
    ("support vector", 3),
    ("arima", 3),
    ("sarima", 3),
    ("prophet", 3),
    ("textrank", 3),
    ("lda", 3),
    ("tf-idf", 3),
    ("word2vec", 3),
    ("infersent", 3),
    ("siamese network", 3),
    ("neat", 3),
    ("neuroevolution", 3),
    ("reinforcement learning", 3),
    ("deep learning", 3),
    ("machine learning", 3),
    ("artificial intelligence", 3),
    ("kecerdasan buatan", 3),
    ("pembelajaran mesin", 3),
    ("neural network", 3),
    ("natural language processing", 3),
    ("pemrosesan bahasa alami", 3),
    ("collaborative filtering", 3),
    ("content-based filtering", 3),
    ("large language model", 3),
    ("genetic algorithm", 3),
    ("algoritma genetika", 3),
    ("particle swarm", 3),
    ("fuzzy", 3),
    ("sistem pakar", 3),
    ("expert system", 3),
    ("mediapipe", 3),
    ("facenet", 3),
    ("apriori", 3),
    ("fp-growth", 3),
    ("market basket", 3),
    ("minimax", 3),
    ("transfer learning", 3),
    ("inception", 3),
    ("inceptionv3", 3),
    ("dcgan", 3),
    ("generative adversarial network", 3),
    ("generative ai", 3),
    ("ai agent", 3),
    ("gated recurrent unit", 3),
    ("perceptron", 3),
    ("tabu search", 3),
    ("case-based reasoning", 3),
    ("fine tuning", 3),
    ("fine-tuning", 3),
    ("ollama", 3),
    ("topic modelling", 3),
    ("topic modeling", 3),
    ("anomaly detection", 3),
    ("deep embedded clustering", 3),
    ("optical character recognition", 3),
    # Domain AI
    ("computer vision", 3),
    ("object detection", 3),
    ("pose estimation", 3),
    ("depth estimation", 3),
    ("lip reading", 3),
    ("hand gesture", 3),
    ("pengenalan rambu", 3),
    ("pengenalan wajah", 3),
    ("face recognition", 3),
    ("speech recognition", 3),
    ("pengenalan tulisan", 3),
    ("pengenalan karakter", 3),
    ("image processing", 3),
    ("pengolahan citra", 3),
    ("sentiment analysis", 3),
    ("analisis sentimen", 3),
    ("aspect-based", 3),
    ("text classification", 3),
    ("text summarization", 3),
    ("ringkasan otomatis", 3),
    ("topic labeling", 3),
    ("chatbot", 3),
    ("essay scoring", 3),
    ("transkripsi musik", 3),
    ("deteksi objek", 3),
    ("sistem rekomendasi", 3),
    ("recommender", 3),
    ("recommendation system", 3),
    # Istilah Umum
    ("klasifikasi", 1),
    ("classification", 1),
    ("klasterisasi", 1),
    ("clustering", 1),
    ("segmentasi", 1),
    ("segmentation", 1),
    ("forecasting", 1),
    ("prediksi", 1),
    ("peramalan", 1),
    ("rekomendasi", 1),
    ("deteksi", 1),
    ("recognition", 1),
    ("regresi", 1),
    ("intent", 1),
    ("gesture", 1),
    ("cosine similarity", 1),
]

AI_CASE_SENSITIVE = [
    ("CNN", 3), ("3D CNN", 3), ("SVM", 3), ("KNN", 3), ("NLP", 3),
    ("OCR", 3), ("LLM", 3), ("GAN", 3), ("PSO", 3), ("RNN", 3)
]

def compile_kw(keyword, case_sensitive=False):
    escaped_kw = re.escape(keyword)
    pattern = r"(?<![A-Za-z0-9])" + escaped_kw + r"(?![A-Za-z0-9])"
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)

def build(daftar, daftar_case_sensitive):
    huruf_besar = {k.lower() for k, _ in daftar_case_sensitive}
    return [(compile_kw(k), w, k) for k, w in daftar if k not in huruf_besar] + [
        (compile_kw(k, True), w, k) for k, w in daftar_case_sensitive
    ]

GAME_RE = build(GAME, GAME_CASE_SENSITIVE)
CYBER_RE = build(CYBER, CYBER_CASE_SENSITIVE)
AI_RE = build(AI, AI_CASE_SENSITIVE)

THRESHOLD = (
    3  # Skor minimal untuk masuk AI / Cyber / Game (= satu kata spesifik di judul)
)
BOBOT_ABSTRAK = 1 / 3  # Kata yang hanya ada di abstrak bernilai sepertiga dari di judul

def skor(judul, abstrak, daftar):
    total, ditemukan = 0, []
    for rx, bobot, nama in daftar:
        if rx.search(judul):
            total += bobot
        elif rx.search(abstrak):
            total += bobot * BOBOT_ABSTRAK
        else:
            continue
        ditemukan.append(nama)
    return round(total, 2), ditemukan

def klasifikasi(judul, abstrak=""):
    """
    Mengklasifikasikan judul skripsi ke dalam konsentrasi:
    'Game', 'Cyber', 'AI', atau 'Full Stack'
    """
    judul = str(judul or "")
    abstrak = str(abstrak or "")

    s_ai, k_ai = skor(judul, abstrak, AI_RE)
    s_cyber, k_cyber = skor(judul, abstrak, CYBER_RE)
    s_game, k_game = skor(judul, abstrak, GAME_RE)

    skor_semua = {"AI": s_ai, "Cyber": s_cyber, "Game": s_game}
    terbesar = max(skor_semua.values())

    # Sisa otomatis Full Stack
    if terbesar < THRESHOLD:
        return "Full Stack", ""

    pemenang = [k for k, v in skor_semua.items() if v == terbesar]
    kata = {"AI": k_ai, "Cyber": k_cyber, "Game": k_game}
    kw = ", ".join(k for p in pemenang for k in kata[p])
    return "/".join(pemenang), kw
