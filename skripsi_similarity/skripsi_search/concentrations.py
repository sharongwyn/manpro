"""Provisional, title-only concentration rules and human-label evaluation."""
import csv
import re
from collections import Counter
from pathlib import Path

from .ingest import write_json

CATEGORIES = ('Game', 'AI', 'Cyber', 'Full Stack')
KEYWORDS = {
    'Game': (
        'game', 'games', 'permainan digital', 'gamification', 'gamifikasi',
    ),
    'AI': (
        'artificial intelligence', 'kecerdasan buatan', 'machine learning',
        'pembelajaran mesin', 'deep learning', 'deep neural network',
        'neural network', 'jaringan saraf', 'computer vision', 'visi komputer',
        'natural language processing', 'pemrosesan bahasa alami',
        'large language model', 'generative ai', 'chatbot', 'sistem pakar',
        'fuzzy logic', 'logika fuzzy', 'llm', 'nlp',
    ),
    'Cyber': (
        'cybersecurity', 'cyber security', 'keamanan informasi',
        'keamanan jaringan', 'information security', 'network security',
        'kriptografi', 'cryptography', 'enkripsi', 'encryption',
        'intrusion detection', 'malware', 'phishing', 'penetration testing',
        'penetration test', 'vulnerability', 'kerentanan', 'digital forensics',
        'forensik digital', 'firewall',
    ),
}
KEYWORD_PATTERNS = {
    category: tuple(
        (keyword, re.compile(r'(?<!\w)' + re.escape(keyword) + r'(?!\w)', re.IGNORECASE))
        for keyword in keywords
    )
    for category, keywords in KEYWORDS.items()
}


def classify_title(title):
    """Return a provisional label and the exact title evidence behind it."""
    title = title if isinstance(title, str) else ''
    matched = {
        category: [keyword for keyword, pattern in patterns if pattern.search(title)]
        for category, patterns in KEYWORD_PATTERNS.items()
    }
    matched = {category: keywords for category, keywords in matched.items() if keywords}

    if len(matched) > 1:
        category = 'Perlu validasi'
        basis = 'Judul cocok dengan lebih dari satu kategori; jangan tetapkan otomatis.'
    elif matched:
        category = next(iter(matched))
        basis = 'Dugaan dari kata kunci pada judul; perlu validasi dengan dosen.'
    else:
        category = 'Full Stack'
        basis = 'Fallback sementara karena kata kunci Game/AI/Cyber tidak ditemukan; bukan bukti Full Stack.'

    return {
        'predicted_category': category,
        'matched_categories': list(matched),
        'matched_keywords': [word for words in matched.values() for word in words],
        'decision_basis': basis,
        'needs_review': category == 'Perlu validasi' or category == 'Full Stack',
    }


def concentration_docs(docs):
    """Use only documents with an INFOR provenance record."""
    return [
        doc for doc in docs
        if any(source.get('department') == 'INFOR' for source in doc.get('provenance', []))
    ]


def _read_annotations(path, known_ids):
    if path is None:
        return {}
    annotations = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError('File anotasi harus memiliki header id dan category/human_category.')
        fields = {name.casefold(): name for name in reader.fieldnames}
        id_field = next((fields[key] for key in ('id', 'doc_id', 'document_id') if key in fields), None)
        label_field = next(
            (fields[key] for key in ('category', 'human_category') if key in fields), None
        )
        if id_field is None or label_field is None:
            raise ValueError('Header anotasi wajib memuat id dan category (atau human_category).')
        for row in reader:
            doc_id = (row.get(id_field) or '').strip()
            label = (row.get(label_field) or '').strip()
            if not doc_id or not label:
                continue
            if doc_id not in known_ids:
                raise ValueError(f'ID anotasi tidak ditemukan pada data INFOR: {doc_id}')
            normalized = next((item for item in CATEGORIES if item.casefold() == label.casefold()), None)
            if normalized is None:
                raise ValueError(f'Kategori tidak valid untuk {doc_id}: {label}. Pilihan: {", ".join(CATEGORIES)}')
            if doc_id in annotations:
                raise ValueError(f'Anotasi duplikat untuk ID: {doc_id}')
            annotations[doc_id] = normalized
    return annotations


def validation_metrics(rows, annotations):
    """Score only determinate automatic predictions and expose their coverage."""
    labeled = [row for row in rows if row['id'] in annotations]
    scored = [
        row for row in labeled
        if row['predicted_category'] in CATEGORIES
    ]
    matrix = {actual: {predicted: 0 for predicted in CATEGORIES} for actual in CATEGORIES}
    for row in scored:
        matrix[annotations[row['id']]][row['predicted_category']] += 1

    per_category = {}
    f1_values = []
    for category in CATEGORIES:
        true_positive = matrix[category][category]
        predicted_count = sum(matrix[actual][category] for actual in CATEGORIES)
        support = sum(matrix[category].values())
        precision = true_positive / predicted_count if predicted_count else 0.0 if support else None
        recall = true_positive / support if support else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else 0.0 if support and (precision is not None or recall is not None)
            else None
        )
        if f1 is not None and support:
            f1_values.append(f1)
        per_category[category] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'support': support,
        }

    correct = sum(matrix[category][category] for category in CATEGORIES)
    count = len(scored)
    return {
        'labeled_count': len(labeled),
        'scored_count': count,
        'withheld_for_multiple_category_matches': len(labeled) - count,
        'accuracy_on_scored': correct / count if count else None,
        'macro_f1_on_categories_with_support': sum(f1_values) / len(f1_values) if f1_values else None,
        'per_category': per_category,
        'confusion_matrix': matrix,
        'note': 'Metrik hanya memakai judul yang menghasilkan satu kategori atau fallback; judul yang cocok dengan beberapa kategori ditahan untuk validasi manual.',
    }


def run_classification(root, annotations_path=None, output_path='reports/concentration_review.csv'):
    root = Path(root)
    corpus_path = root / 'reports' / 'corpus.json'
    if not corpus_path.is_file():
        raise FileNotFoundError(f'{corpus_path} tidak ditemukan. Jalankan perintah ingest terlebih dahulu.')

    import json
    docs = concentration_docs(json.loads(corpus_path.read_text(encoding='utf-8')))
    rows = []
    for doc in docs:
        rows.append({
            'id': doc['id'],
            'title': doc.get('title', ''),
            **classify_title(doc.get('title', '')),
        })

    annotations = _read_annotations(
        root / annotations_path if annotations_path and not Path(annotations_path).is_absolute() else annotations_path,
        {row['id'] for row in rows},
    )
    for row in rows:
        row['human_category'] = annotations.get(row['id'], '')

    output = root / output_path if not Path(output_path).is_absolute() else Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=(
            'id', 'title', 'predicted_category', 'matched_categories',
            'matched_keywords', 'decision_basis', 'needs_review', 'human_category',
        ))
        writer.writeheader()
        for row in rows:
            writer.writerow({
                **row,
                'matched_categories': '; '.join(row['matched_categories']),
                'matched_keywords': '; '.join(row['matched_keywords']),
            })

    counts = Counter(row['predicted_category'] for row in rows)
    report = {
        'scope': 'INFOR titles only',
        'method': 'Provisional title-only keyword rules; no model inference.',
        'keyword_rules': {category: list(keywords) for category, keywords in KEYWORDS.items()},
        'document_count': len(rows),
        'prediction_counts': {category: counts.get(category, 0) for category in (*CATEGORIES, 'Perlu validasi')},
        'annotations_file': str(annotations_path) if annotations_path else None,
        'validation': validation_metrics(rows, annotations) if annotations_path else None,
        'csv_output': str(output),
    }
    json_output = output.with_suffix('.json')
    write_json(json_output, report)
    return report, json_output
