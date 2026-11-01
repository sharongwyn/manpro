import json
import os
from collections import Counter
from pathlib import Path
import numpy as np
from .text import clean, tokens, digest, TEXT_VERSION, chunk_text
from .aspects import Extractor, compare
from .ingest import read_sources, write_json
from .classifier import klasifikasi

MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
INDEX_VERSION='exact-v1'
CONFIGS=['legacy','sbert','bm25']+[f'{rep}_{fusion}' for rep in ('plain','chunk') for fusion in ('rrf','w05','w07')]

class BM25:
    """Positive Robertson IDF; preserves the original notebook formula."""
    def __init__(self,corpus,k1=1.5,b=.75):
        self.tf=[Counter(t) for t in corpus]; self.dl=np.array([len(t) for t in corpus],float)
        self.avg=float(self.dl.mean()) if len(self.dl) and self.dl.mean()>0 else 1.
        self.k1=k1; self.b=b; n=len(corpus)
        df=Counter(t for ts in corpus for t in set(ts))
        self.idf={t:np.log(1+(n-f+.5)/(f+.5)) for t,f in df.items()}
    def scores(self,q):
        out=np.zeros(len(self.tf))
        for t in set(q):
            if t not in self.idf: continue
            f=np.array([x.get(t,0) for x in self.tf],float)
            out+=self.idf[t]*f*(self.k1+1)/(f+self.k1*(1-self.b+self.b*self.dl/self.avg))
        return out
    def reference(self,q):
        return sum(self.idf.get(t,np.log(1+(len(self.tf)+.5)/.5))*f*(self.k1+1)/(f+self.k1*(1-self.b+self.b*max(len(q),1)/self.avg)) for t,f in Counter(q).items())

def unit(x):
    x=np.asarray(x,dtype=np.float32)
    return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)

def order(scores,ids):
    return np.lexsort((np.asarray(ids),-np.asarray(scores)))

def ranks(scores,ids):
    r=np.empty(len(scores),int); r[order(scores,ids)]=np.arange(1,len(scores)+1); return r

def percentile(scores):
    """Fixed per-query midrank ECDF; no fitted statistics, ties share a value.

    Zero/negative scores carry no signal. This measures relative rank, not confidence.
    """
    scores=np.asarray(scores); n=len(scores)
    if not n: return np.array([])
    sorted_scores=np.sort(scores)
    return np.where(scores>0,(np.searchsorted(sorted_scores,scores,'left')+np.searchsorted(sorted_scores,scores,'right'))/(2*n),0.)

class Encoder:
    def __init__(self,model=MODEL,revision=None,cache_folder=None,device=None):
        os.environ.setdefault('USE_TF','0')
        from sentence_transformers import SentenceTransformer
        import torch
        torch.set_num_threads(min(4,os.cpu_count() or 1))
        # Pinned snapshots can be loaded without repeated online HEAD requests.
        snapshot=Path(cache_folder or '.')/('models--'+model.replace('/','--'))/'snapshots'/str(revision)
        local=snapshot.exists() and (snapshot/'modules.json').exists()
        self.model=SentenceTransformer(str(snapshot) if local else model,revision=None if local else revision,cache_folder=cache_folder,device=device,local_files_only=local)
        self.tokenizer=self.model.tokenizer
        self.max_length=int(self.model.max_seq_length)
        self.name=model
        ref=Path(cache_folder or '.')/('models--'+model.replace('/','--'))/'refs'/'main'
        self.revision=getattr(self.model[0].auto_model.config,'_commit_hash',None) or revision or (ref.read_text().strip() if ref.exists() else 'local-unresolved')
        self.info={'name':model,'revision':self.revision,'max_seq_length':self.max_length,'tokenizer_model_max_length':self.tokenizer.model_max_length,'special_tokens':self.tokenizer.num_special_tokens_to_add(pair=False),'device':str(self.model.device)}
    def encode(self,texts):
        if not texts: return np.empty((0,self.model.get_sentence_embedding_dimension()),np.float32)
        return self.model.encode(texts,normalize_embeddings=True,convert_to_numpy=True,batch_size=32,show_progress_bar=False)

def fingerprint(docs,extractor,encoder,source_report):
    return digest({'format':INDEX_VERSION,'text':TEXT_VERSION,'corpus':docs,'sources':source_report['sources'],'dictionary':extractor.fingerprint,'model':encoder.info,'chunk':{'max_length':encoder.max_length,'overlap':16,'aggregation':'normalized_mean_per_section'},'preprocessing_code':{p.name:digest(p.read_text(encoding='utf-8')) for p in [Path(__file__).with_name(n) for n in ('text.py','ingest.py','aspects.py')]}})

class Index:
    def __init__(self,docs,extractor,encoder,cache_dir,fp,rebuild=False):
        if not docs: raise ValueError('Corpus kosong: tidak dapat membuat indeks')
        self.docs=docs; self.ids=[d['id'] for d in docs]; self.encoder=encoder; self.extractor=extractor; self.fingerprint=fp
        self.cache_dir=Path(cache_dir); self.cache_dir.mkdir(parents=True,exist_ok=True)
        self.sections=[]; self.chunks=[]; self.plain=[]; self.legacy=[]
        self.aspects=[]; legacy_lex=[]; lex=[]
        for d in docs:
            dept = str(d.get('department', '')).upper()
            if 'INFOR' in dept:
                konsentrasi, kw_terdeteksi = klasifikasi(d['title'], d['abstract'])
                d['konsentrasi'] = konsentrasi
                d['keyword_terdeteksi'] = kw_terdeteksi
            else:
                d['konsentrasi'] = '-'
                d['keyword_terdeteksi'] = ''
            sec={'title_abstract':clean(d['title']+'. '+d['abstract']),**{k:v['text'] for k,v in d['parsed']['sections'].items()}}
            self.sections.append(sec)
            lex.append(tokens(' '.join(sec.values())))
            old=d['legacy_sections']; legacy_lex.append(tokens(' '.join([d['title'],d['abstract'],old['scope'],old['problem']]),legacy=True))
            self.legacy.extend([d['title']+'. '+d['abstract'],old['scope']])
            self.plain.extend([sec['title_abstract'],sec['scope']])
            for section in ('title_abstract','scope'):
                self.chunks.extend(chunk_text(sec[section],encoder.tokenizer,encoder.max_length,d['id'],section))
            self.aspects.append(extractor.extract(' '.join(sec.values())))
        self.bm25=BM25(lex); self.legacy_bm25=BM25(legacy_lex)
        for i,c in enumerate(self.chunks):
            c['chunk_id']='chunk-'+digest({k:c[k] for k in ('doc_id','section','start','end','text')})[:20]
            c['chunk_vector_row']=i
        texts=self.plain+self.legacy+[x['text'] for x in self.chunks]
        file=self.cache_dir/(fp+'.npz')
        model_key=digest({'model':encoder.info,'normalized':True,'format':'text-pool-v1'})
        pool_path=self.cache_dir/('model-pool-'+model_key+'.npz')
        pool={}
        if pool_path.exists() and not rebuild:
            with np.load(pool_path,allow_pickle=False) as stored:
                pool=dict(zip(stored['keys'].tolist(),stored['vectors']))
        if file.exists() and not rebuild:
            with np.load(file,allow_pickle=False) as cache:
                if str(cache['fingerprint'])!=fp: raise ValueError('Cache fingerprint mismatch; rebuild required')
                vectors=cache['vectors']
                if len(vectors)!=len(texts): raise ValueError('Cache shape mismatch; rebuild required')
        else:
            # Deduplicate identical texts to avoid redundant encoding; blanks stay zero vectors.
            unique=sorted(set(t for t in texts if t.strip()))
            missing=[t for t in unique if digest(t) not in pool]
            if missing:
                enc=unit(encoder.encode(missing))
                pool.update({digest(t):e for t,e in zip(missing,enc)})
            dimension=len(next(iter(pool.values())))
            vectors=np.stack([pool.get(digest(t),np.zeros(dimension,np.float32)) if t.strip() else np.zeros(dimension,np.float32) for t in texts])
            np.savez_compressed(file,vectors=vectors,fingerprint=fp)
        before=len(pool)
        pool.update({digest(t):e for t,e in zip(texts,vectors) if t.strip()})
        if len(pool)!=before or not pool_path.exists() or rebuild:
            pool_keys=sorted(pool)
            np.savez_compressed(pool_path,keys=np.array(pool_keys),vectors=np.stack([pool[k] for k in pool_keys]))
        n=len(docs); self.plain_vectors=vectors[:2*n].reshape(n,2,-1)
        self.legacy_vectors=vectors[2*n:4*n].reshape(n,2,-1)
        self.chunk_vectors=vectors[4*n:]
        self.chunk_rows={(d['id'],sec):[i for i,c in enumerate(self.chunks) if c['doc_id']==d['id'] and c['section']==sec] for d in docs for sec in ('title_abstract','scope')}
        self.chunk_centroids=np.zeros_like(self.plain_vectors)
        for i,d in enumerate(docs):
            for j,sec in enumerate(('title_abstract','scope')):
                rows=self.chunk_rows[(d['id'],sec)]
                if rows: self.chunk_centroids[i,j]=unit(self.chunk_vectors[rows].mean(axis=0))
        self.truncation={'model':encoder.info,'plain_truncated_fields':sum(len(encoder.tokenizer.encode(t,add_special_tokens=True))>encoder.max_length for t in self.plain),'plain_fields':len(self.plain),'chunks':len(self.chunks),'max_chunk_tokens':max(c['token_count'] for c in self.chunks),'aggregation':'cosine of normalized mean chunk embeddings per section; fixed section weights, no max score bonus for length'}
        self.query_cache={}

    def _query(self,q):
        fields={k:clean(q.get(k,'')) for k in ('title','description','problem','method','dataset')}
        text='. '.join(fields[k] for k in ('title','problem','method','dataset','description') if fields[k])
        if not text: raise ValueError('Query kosong')
        if not tokens(text): raise ValueError('Query tanpa sinyal: isi istilah penelitian yang informatif')
        scope='. '.join(fields[k] for k in ('title','method','dataset') if fields[k]) if fields['method'] or fields['dataset'] else text
        key=digest(fields)
        if key not in self.query_cache:
            qchunks=[chunk_text(t,self.encoder.tokenizer,self.encoder.max_length,'query',s) for s,t in [('query',text),('query_scope',scope)]]
            alltexts=[text,scope]+[c['text'] for cs in qchunks for c in cs]
            emb=unit(self.encoder.encode(alltexts)); offset=2; means=[]; passage_vectors=[]
            for cs in qchunks:
                passage_vectors.append(emb[offset:offset+len(cs)])
                means.append(unit(emb[offset:offset+len(cs)].mean(axis=0))); offset+=len(cs)
            self.query_cache[key]={'text':text,'scope':scope,'plain':emb[:2],'chunk':np.stack(means),'aspects':self.extractor.extract(text),'chunks':qchunks,'passage_vectors':passage_vectors}
        return self.query_cache[key]

    def score(self,q,config='plain_rrf'):
        if config not in CONFIGS: raise ValueError(f'Unknown configuration {config}')
        query=self._query(q); n=len(self.docs)
        legacy=config=='legacy'; rep='chunk' if config.startswith('chunk') else 'plain'
        vectors=self.legacy_vectors if legacy else self.chunk_centroids if rep=='chunk' else self.plain_vectors
        qe=query[rep]; cos=np.einsum('nsd,sd->ns',vectors,qe)
        if legacy: cos=np.clip(cos,0,1)
        available=np.array([bool((d['legacy_sections'] if legacy else self.sections[i])['scope']) for i,d in enumerate(self.docs)])
        sem=np.where(available,.5*cos[:,0]+.5*cos[:,1],cos[:,0])
        bm_index=self.legacy_bm25 if legacy else self.bm25
        qt=tokens(query['text'],legacy=legacy); bm=bm_index.scores(qt)
        st=percentile(sem); bt=percentile(bm)
        if legacy:
            st=sem; ref=bm_index.reference(qt); bt=np.clip(bm/ref,0,1) if ref else np.zeros(n)
            sc=.7*st; bc=.3*bt
        elif config=='sbert': st=sem; sc=sem; bc=np.zeros(n)
        elif config=='bm25': bt=bm; sc=np.zeros(n); bc=bm
        elif config.endswith('rrf'):
            st=np.where(sem>0,1/(60+ranks(sem,self.ids)),0); bt=np.where(bm>0,1/(60+ranks(bm,self.ids)),0)
            sc=st; bc=bt
        else:
            alpha=.5 if config.endswith('w05') else .7; sc=alpha*st; bc=(1-alpha)*bt
        return {'query':query,'sbert_raw':sem,'abstract_cosine':cos[:,0],'scope_cosine':cos[:,1],'bm25_raw':bm,'semantic_transformed':st,'bm25_transformed':bt,'semantic_contribution':sc,'bm25_contribution':bc,'hybrid':sc+bc,'representation':rep}

    def search(self,q,top_k=5,config='plain_rrf',rerank=0.):
        if top_k<1: raise ValueError('top_k harus positif')
        if rerank not in (0,.05,.10): raise ValueError('Only two experimental strengths: 0.05 and 0.10')
        s=self.score(q,config); idx=order(s['hybrid'],self.ids); hr=ranks(s['hybrid'],self.ids)
        final=s['hybrid'].copy(); comparisons={}
        candidates=idx[:min(50,len(idx))]
        # Relative hybrid base for rerank keeps RRF score scale from amplifying aspect bonus.
        base=final/max(float(final.max()),1e-12)
        if rerank:
            final=base.copy()
            for i in candidates:
                comparisons[i]=compare(s['query']['aspects'],self.aspects[i]); final[i]=base[i]+rerank*comparisons[i]['score']
            # Only the top-50 candidate pool may be reranked.
            idx=np.concatenate([candidates[order(final[candidates],[self.ids[i] for i in candidates])],idx[len(candidates):]])
        positive_signal=bool(np.any(s['hybrid']>0))
        if not positive_signal: idx=np.array([],dtype=int)
        rows=[]
        for rank,i in enumerate(idx[:min(top_k,len(idx))],1):
            d=self.docs[i]; a=comparisons.get(i) or compare(s['query']['aspects'],self.aspects[i])
            # Passage evidence always reports the actual compared text; truncated plain vectors use token offsets.
            evidence=[]
            for j,section in enumerate(('title_abstract','scope')):
                if s['representation']=='chunk':
                    cr=self.chunk_rows[(d['id'],section)]
                    if cr:
                        pairs=self.chunk_vectors[cr]@s['query']['passage_vectors'][j].T
                        di,qi=np.unravel_index(np.argmax(pairs),pairs.shape)
                        best=cr[di]; c=self.chunks[best]
                        evidence.append({**c,'query_chunk':s['query']['chunks'][j][qi],'passage_cosine':float(pairs[di,qi]),'selection':'Maximum passage pair for evidence only; document ranking uses section centroids.'})
                else:
                    txt=(d['title']+'. '+d['abstract']) if config=='legacy' and j==0 else d['legacy_sections']['scope'] if config=='legacy' else self.sections[i][section]
                    if not txt: continue
                    off=self.encoder.tokenizer(txt,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
                    budget=self.encoder.max_length-self.encoder.tokenizer.num_special_tokens_to_add(pair=False)
                    end=off[min(len(off),budget)-1][1] if off else 0
                    qt=s['query']['text'] if j==0 else s['query']['scope']
                    qo=self.encoder.tokenizer(qt,add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
                    qend=qo[min(len(qo),budget)-1][1] if qo else 0
                    evidence.append({'doc_id':d['id'],'section':section,'start':0,'end':end,'text':txt[:end],'truncated':end<len(txt),'query_text':qt[:qend],'query_start':0,'query_end':qend,'query_truncated':qend<len(qt),'cosine':float(s['abstract_cosine'][i] if j==0 else s['scope_cosine'][i])})
            row={
                'id':d['id'],
                'title':d['title'],
                'department':d['department'],
                'year':d['year'],
                'konsentrasi': d.get('konsentrasi', '-'),
                'keyword_terdeteksi': d.get('keyword_terdeteksi', ''),
                'sources':d['provenance'],
                'hybrid_rank':int(hr[i]),
                'final_rank':rank,
                'config':config,
                'hybrid_score':float(s['hybrid'][i]),
                'final_score':float(final[i]),
                'aspect_score':a['score'],
                'rerank_strength':rerank,
                'rerank_contribution':rerank*a['score'] if i in candidates else 0.,
                'aspect_comparison':a,
                'document_aspects':self.aspects[i],
                'evidence':evidence,
                'explanation':'Kandidat berdasarkan kemiripan topik SBERT dan istilah BM25. '+ ('Ada aspek yang cocok berdasarkan bukti aturan.' if a['similarities'] else 'Kesamaan aspek belum dikonfirmasi.')+' Tujuan dan kontribusi perlu ditinjau pada dokumen sumber.'
            }
            rows.append(row)
        return {'results':rows,'query_aspects':s['query']['aspects'],'fingerprint':self.fingerprint,'config':config,'label_status':'belum dikalibrasi','interpretation':'Skor ranking bukan persentase plagiarisme, probabilitas duplikasi, atau bukti orisinalitas. Kesimpulan terbatas pada corpus ini.','no_positive_signal':not positive_signal}

def load_index(root,encoder=None,rebuild=False):
    root=Path(root); source=json.loads((root/'sources.json').read_text(encoding='utf-8'))
    settings=json.loads((root/'default_config.json').read_text(encoding='utf-8'))
    docs,report=read_sources(source,root)
    extractor=Extractor([root/p for p in source['dictionaries']])
    if encoder is None: encoder=Encoder(settings['model'],settings.get('revision'),str(root/'.model_cache'),settings.get('device'))
    fp=fingerprint(docs,extractor,encoder,report)
    write_json(root/'reports/data_quality.json',report); write_json(root/'reports/corpus.json',docs)
    index=Index(docs,extractor,encoder,root/'.embedding_cache',fp,rebuild)
    with (root/'reports/chunks.jsonl').open('w',encoding='utf-8') as f:
        for chunk in index.chunks: f.write(json.dumps(chunk,ensure_ascii=False)+'\n')
    write_json(root/'reports/index_manifest.json',{'fingerprint':fp,'model':encoder.info,'truncation':index.truncation,'dictionary':extractor.fingerprint,'corpus_fingerprint':digest(docs),'index_version':INDEX_VERSION})
    return index
