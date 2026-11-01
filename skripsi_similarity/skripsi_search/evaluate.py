import csv
import importlib.metadata
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from .engine import CONFIGS, order
from .ingest import write_json

def metrics(ranked, judgments, graded=False):
    """Unjudged != negative. Metrics refer only to known positive targets."""
    relevant={k:v for k,v in judgments.items() if v>0}
    if not relevant: return None
    found=[i+1 for i,d in enumerate(ranked) if d in relevant]
    out={'Hit@5':float(any(r<=5 for r in found)), 'Recall@5':sum(r<=5 for r in found)/len(relevant),'Recall@10':sum(r<=10 for r in found)/len(relevant),'MRR':1/min(found) if found else 0.}
    if graded:
        dcg=sum((2**judgments.get(d,0)-1)/np.log2(i+2) for i,d in enumerate(ranked[:5]))
        ideal=sum((2**g-1)/np.log2(i+2) for i,g in enumerate(sorted(relevant.values(),reverse=True)[:5]))
        out['nDCG@5']=float(dcg/ideal) if ideal else None
    return out

def write_csv(path,rows,fields=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or sorted({k for r in rows for k in r})
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items() if k in fields})

def grouped_components(queries):
    # Connected source components prevent sharing any target across different folds.
    groups=[]
    for q in queries:
        targets=set(q.get('source_ids',[]))
        if not targets: continue
        overlap=[g for g in groups if targets&g['sources']]
        new={'sources':targets,'queries':{q['id']}}
        for g in overlap:
            new['sources']|=g['sources']; new['queries']|=g['queries']; groups.remove(g)
        groups.append(new)
    return sorted(groups,key=lambda g:sorted(g['sources']))

def run_evaluation(index,root,query_path=None,annotations=None):
    root=Path(root); out=root/'reports/evaluation'; out.mkdir(parents=True,exist_ok=True)
    queries=json.loads(Path(query_path or root/'evaluation/queries.json').read_text(encoding='utf-8'))
    known=set(index.ids)
    if any(not set(q.get('source_ids',[]))<=known for q in queries): raise ValueError('Ground truth references missing corpus IDs')
    human=defaultdict(dict)
    query_ids={q['id'] for q in queries}
    if annotations:
        with Path(annotations).open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                if r.get('review_status')=='human_reviewed' and r.get('relevance') in ('0','1','2'):
                    if r['query_id'] not in query_ids: raise ValueError('Unknown annotation query ID')
                    if r['doc_id'] not in known: raise ValueError('Unknown annotation document ID')
                    existing=human[r['query_id']].get(r['doc_id'])
                    if existing is not None and existing!=int(r['relevance']): raise ValueError('Conflicting reviewed relevance labels')
                    human[r['query_id']][r['doc_id']]=int(r['relevance'])
    groups=grouped_components(queries)
    group_map={qid:i for i,g in enumerate(groups) for qid in g['queries']}
    rows=[]; per=[]; pools=defaultdict(set)
    # No configuration selection on regression data. All nine were fixed before execution.
    for config in CONFIGS:
        for q in queries:
            s=index.score(q,config); ids=[index.ids[i] for i in order(s['hybrid'],index.ids)]
            pools[q['id']].update(ids[:5])
            judgments={d:1 for d in q.get('source_ids',[])}
            m=metrics(ids,judgments)
            row={'config':config,'query_id':q['id'],'legacy_group':q['legacy_group'],'source_component':group_map.get(q['id']),'label_status':'legacy_provisional','source_ids':q.get('source_ids',[]),'source_ranks':{d:ids.index(d)+1 for d in judgments},'top_ids':ids[:10],'top_score':float(s['hybrid'].max()),'metrics_status':'known_source_smoke_only' if m else 'unjudged_no_metrics'}
            if m: row.update(m)
            rows.append(row)
            if human[q['id']]:
                hm=metrics(ids,human[q['id']],graded=True)
                if hm: per.append({'config':config,'query_id':q['id'],**hm})
    aggregate=[]
    rng=np.random.default_rng(20261020)
    for config in CONFIGS:
        rs=[r for r in rows if r['config']==config and 'MRR' in r]
        metrics_out={k:float(np.mean([r[k] for r in rs])) for k in ('Hit@5','Recall@5','Recall@10','MRR')} if rs else {}
        # Resample source components, preserving dependent paraphrases within component.
        components=sorted({r['source_component'] for r in rs})
        samples=[]
        if components:
            for _ in range(1000):
                chosen=rng.choice(components,len(components),replace=True)
                vals=[r['Recall@5'] for g in chosen for r in rs if r['source_component']==g]
                samples.append(float(np.mean(vals)))
        aggregate.append({'config':config,'queries':len(rs),'source_components':len(components),**metrics_out,'Recall@5_group_bootstrap_95':np.quantile(samples,[.025,.975]).tolist() if samples else None})
    versions={p:importlib.metadata.version(p) for p in ('numpy','openpyxl','sentence-transformers','transformers','torch') if importlib.util.find_spec(p.replace('-','_')) is not None}
    report={'scope':'Preliminary grouped regression only. Legacy labels and source relevance are provisional; unjudged documents are not negatives. No independent test set. Metrics are against mapped known sources, not complete corpus relevance.','fingerprint':index.fingerprint,'model':index.encoder.info,'seed':20261020,'dependencies':versions,'configurations':CONFIGS,'weighted_normalization':'Per-query midrank ECDF, <=0 maps to zero. No fitted statistics.','splits':{'regression':{'queries':len(queries),'queries_with_provisional_sources':sum(bool(q.get('source_ids')) for q in queries),'source_components':len(groups)},'development':{'queries':0,'source_components':0},'validation':{'queries':0,'source_components':0},'test':{'queries':0,'source_components':0}},'groups':[{'component':i,'source_ids':sorted(g['sources']),'query_ids':sorted(g['queries'])} for i,g in enumerate(groups)],'aggregate':aggregate,'selection':{'default':'plain_rrf','basis':'Predeclared simple provisional default; regression scores are not validation evidence','reranking':'Disabled; no adequate human validation. Two strengths 0.05/0.10 supported for future validation only.'},'classification':'Not evaluated: no adequate reviewed classification labels','human_reviewed_query_count':sum(any(v>0 for v in h.values()) for h in human.values()),'aspect_accuracy':'Not estimable without completed manual annotations'}
    write_json(out/'aggregate.json',report); write_json(out/'per_query.json',rows); write_csv(out/'per_query.csv',rows)
    write_csv(out/'human_judged_metrics.csv',per,fields=['config','query_id','Hit@5','Recall@5','Recall@10','MRR','nDCG@5'])
    annotation=[]
    by_id={d['id']:d for d in index.docs}
    for q in queries:
        for did in sorted(pools[q['id']]|set(q.get('source_ids',[]))):
            annotation.append({'query_id':q['id'],'query_title':q['title'],'query_text':q,'doc_id':did,'document_title':by_id[did]['title'],'document_abstract':by_id[did]['abstract'],'provenance':by_id[did]['provenance'],'suggested_relevance':1 if did in q.get('source_ids',[]) else '', 'relevance':'','review_status':'provisional' if did in q.get('source_ids',[]) else 'unjudged','evidence':'','reason':'','reviewer':''})
    template=root/'evaluation/relevance_annotation.csv'
    if not template.exists(): write_csv(template,annotation)
    write_csv(out/'relevance_pool_current.csv',annotation)
    coverage={field:sum(a[field]['status']=='found' for a in index.aspects)/len(index.docs) for field in index.aspects[0]}
    write_json(root/'reports/aspect_coverage.json',{'documents':len(index.docs),'coverage':coverage,'precision':None,'reason':'Coverage is automatic detection, not extraction correctness; fill manual sample first.'})
    sample=[]
    # Deterministic stratified sample across departments for manual review.
    for dep in sorted({d['department'] for d in index.docs}):
        for i in [i for i,d in enumerate(index.docs) if d['department']==dep][:5]:
            for field,a in index.aspects[i].items():
                sample.append({'doc_id':index.docs[i]['id'],'title':index.docs[i]['title'],'department':dep,'aspect':field,'extracted':a,'correct_items':'','missed_items':'','evidence':'','review_status':'unjudged','reviewer':''})
    aspect_template=root/'evaluation/aspect_annotation.csv'
    if not aspect_template.exists(): write_csv(aspect_template,sample)
    return report
