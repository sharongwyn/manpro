"""Extract DATA as literal AST; never execute original notebooks or their instructions."""
import ast
import json
from pathlib import Path
from skripsi_search.ingest import write_json
from skripsi_search.evaluate import write_csv
from skripsi_search.text import title_key

def prepare(root=Path('.')):
    nb=json.loads((root/'reference/Testing_Baru.ipynb').read_text(encoding='utf-8'))
    data=None
    for cell in nb['cells']:
        source=''.join(cell.get('source',[]))
        if 'DATA = [' not in source: continue
        tree=ast.parse(source)
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DATA' for t in node.targets): data=ast.literal_eval(node.value)
    if data is None: raise ValueError('Legacy DATA not found')
    docs=json.loads((root/'reports/corpus.json').read_text(encoding='utf-8'))
    queries=[]; audit=[]
    for id_,group,title,problem,method,dataset,prefix,notes in data:
        ids=[]; mappings=[]
        for pre in prefix.split(' | '):
            if not pre.strip(): continue
            # Prefix used ONCE during migration. Resolved IDs are persisted for all later evaluation.
            matches=[d for d in docs if title_key(d['title']).startswith(title_key(pre))]
            mappings.append({'legacy_prefix':pre,'matches':[{'id':d['id'],'title':d['title'],'provenance':d['provenance']} for d in matches],'status':'unique_mapping' if len(matches)==1 else 'ambiguous' if matches else 'missing'})
            if len(matches)==1: ids.append(matches[0]['id'])
        q={'id':id_,'legacy_group':group,'title':title,'description':'','problem':problem,'method':method,'dataset':dataset,'source_ids':sorted(set(ids)),'label_status':'legacy_provisional','legacy_notes':notes,'relevance_status':'unjudged' if not ids else 'legacy_source_provisional','mapping_status':'resolved' if mappings and all(m['status']=='unique_mapping' for m in mappings) else 'no_sources' if not mappings else 'needs_review'}
        queries.append(q); audit.append({'query_id':id_,'mappings':mappings,'labels_reviewed_by_human':False,'note':'Group C original/orisinal is an unverified legacy claim, not a negative relevance judgment.'})
    write_json(root/'evaluation/queries.json',queries); write_json(root/'reports/ground_truth_audit.json',audit)
    hard=[
        {'id':'HN-method','query':'Klasifikasi penyakit daun tomat menggunakan CNN pada PlantVillage.','candidate':'Klasifikasi sentimen ulasan film menggunakan CNN pada IMDb.','dimension':'method same; object, objective and dataset different'},
        {'id':'HN-object','query':'Prediksi kebutuhan darah PMI menggunakan ARIMA.','candidate':'Pengelompokan donor darah berdasarkan profil dengan K-Means.','dimension':'domain same; objective and method different'},
        {'id':'HN-platform','query':'Deteksi pneumonia pada citra ChestX-ray14 dari Kaggle.','candidate':'Klasifikasi daun PlantVillage dari Kaggle.','dimension':'platform/type same; named dataset and object different'},
        {'id':'HN-version','query':'Deteksi kendaraan menggunakan YOLOv8.','candidate':'Deteksi kendaraan menggunakan YOLO11.','dimension':'family and object same; method version different'}
    ]
    for h in hard: h.update({'review_status':'provisional_synthetic','relevance':'','evidence':'Synthetic contrast for annotation training, never a performance label.','reason':'','reviewer':''})
    write_csv(root/'evaluation/hard_negative_annotation.csv',hard)
    print('Queries:',len(queries),'mapped:',sum(bool(q['source_ids']) for q in queries),'unresolved:',[q['id'] for q in queries if q['mapping_status']=='needs_review'])

if __name__=='__main__': prepare()
