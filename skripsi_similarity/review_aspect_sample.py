"""Small, explicitly provisional agent audit; not independent human ground truth."""
import json
from pathlib import Path
from skripsi_search.aspects import Extractor
from skripsi_search.ingest import write_json
from skripsi_search.evaluate import write_csv
root=Path('.')
docs={d['id']:d for d in json.loads((root/'reports/corpus.json').read_text(encoding='utf-8'))}
extractor=Extractor([root/'kamus'/f'kamus_{n}.csv' for n in ('method','problem','dataset')])
review={
    'thesis-071d0aa25ad3b6e04529':{'expected':[('algorithm','fp-growth')],'missed':['DB-Scan (alias DBSCAN missing)'],'note':'FP-Growth is explicitly implemented in the abstract; uncertain role is conservative.'},
    'thesis-17dd5d9ea7ab3f39a1af':{'expected':[('technology','postgresql')],'missed':['Apache Cassandra (technology not in lexicon)','replication/sharding (database techniques not modeled)'],'note':'PostgreSQL is correctly categorized as supporting technology; comparison roles remain uncertain. No named public dataset.'},
    'thesis-0015a1fe7f6d766ea7c3':{'expected':[('technology','c++')],'missed':[],'note':'Abstract explicitly states the educational game uses C++; technology, not a main learning algorithm.'},
    'thesis-0035f8827bc2f5adb307':{'expected':[],'missed':[],'note':'No named algorithm or software stack in title/abstract; unknown is appropriate within this scope.'},
    'thesis-000a6ba338c882875a95':{'expected':[('algorithm','svm')],'missed':[],'note':'Support Vector Machine is the classifier in title and abstract; Instagram is a platform, not named dataset identity.'},
    'thesis-002f8d7c12e221ce2d13':{'expected':[('technology','laravel'),('technology','postgresql')],'missed':[],'note':'Laravel and PostgreSQL are explicit implementation technologies; SUS is research evaluation, not main prediction algorithm.'},
}
items=[]; categories=0; correct=0
for did,r in review.items():
    d=docs[did]; a=extractor.extract(d['title']+'. '+d['abstract'])
    for field in ('algorithm','technology'):
        for item in a[field]['items']:
            ok=(field,item['canonical']) in r['expected']; categories+=1; correct+=int(ok)
            items.append({'doc_id':did,'department':d['department'],'title':d['title'],'aspect':field,'canonical':item['canonical'],'original':item['original'],'evidence':item['evidence'],'role':item['role'],'span_and_category_correct_provisional':ok,'review_status':'agent_reviewed_provisional','reason':r['note']})
report={'status':'agent_reviewed_provisional_not_human','scope':'Six deterministic source documents, title+abstract only; algorithm and technology mention/category checks, not full-corpus aspect accuracy. No changes tuned from these labels.','documents':len(review),'mentions_checked':categories,'mentions_correct_provisional':correct,'mention_category_precision_provisional':correct/categories if categories else None,'limitations':'Tiny nonrandom sample, model reviewed its own output; no independent human verification, no population estimate or calibrated confidence. Missing items below demonstrate incomplete coverage; do not use as quality validation.','reviews':review,'coverage_reference':'reports/aspect_coverage.json','human_precision':None}
write_json(root/'reports/aspect_provisional_review.json',report)
write_csv(root/'evaluation/aspect_provisional_review.csv',items)
print({k:v for k,v in report.items() if k not in ('reviews','limitations')})
