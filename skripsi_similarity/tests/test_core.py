import copy
import json
import re
from pathlib import Path
import numpy as np
import openpyxl
import pytest
from skripsi_search.text import clean,value,tokens,parse_chapter,chunk_text,digest
from skripsi_search.ingest import read_sources
from skripsi_search.aspects import Extractor,compare
from skripsi_search.engine import BM25,Index,order,percentile,fingerprint
from skripsi_search.evaluate import metrics,grouped_components

class Tokenizer:
    model_max_length=32
    def num_special_tokens_to_add(self,pair=False): return 2
    def __call__(self,text,add_special_tokens=False,return_offsets_mapping=False):
        ms=list(re.finditer(r'\S+',text)); return {'input_ids':list(range(len(ms))),'offset_mapping':[m.span() for m in ms]}
    def encode(self,text,add_special_tokens=True): return list(range(len(text.split())+(2 if add_special_tokens else 0)))

class FixtureEncoder:
    """Deterministic test fixture only. Never used as a retrieval fallback."""
    tokenizer=Tokenizer(); max_length=32; info={'name':'TEST_FIXTURE','revision':'1','max_seq_length':32}
    def encode(self,texts):
        rows=[]
        for text in texts:
            v=np.zeros(16)
            for t in tokens(text): v[int(digest(t)[:8],16)%16]+=1
            rows.append(v)
        return np.array(rows)

@pytest.fixture
def dictionary(tmp_path):
    p=tmp_path/'methods.csv'; p.write_text('method\nC++\nC#\nLinear Regression\nMultiple Linear Regression\nYOLOv8\n',encoding='utf-8')
    return Extractor([p])

def test_nan_sentinel():
    assert value(float('nan'))==value(None)==value('TIDAK DITEMUKAN')==''
    assert 'nan' not in clean(None)
    assert 'Universitas Kristen Petra' in clean('Data penelitian di Universitas Kristen Petra pada tahun 2024.')
    assert 'Universitas Kristen Petra' not in clean('isi halaman. 22 Universitas Kristen Petra --- isi berikutnya.')

@pytest.mark.parametrize('heading',['1.2 Rumusan Masalah','1.2. rumusan masalah','1 . 2 . IDENTIFIKASI MASALAH','1.2 Perumusan Masalah'])
def test_headings(heading):
    p=parse_chapter(heading+' Sulit mendeteksi objek. 1.3. ruang lingkup Metode C++. 1.4 tujuan Meningkatkan akurasi.')
    assert p['sections']['problem']['text']=='Sulit mendeteksi objek'
    assert 'C++' in p['sections']['scope']['text']
    assert 'tujuan' not in p['sections']['scope']['text']

def test_parse_status():
    assert parse_chapter('') ['sections']['scope']['status']=='not_available'
    assert parse_chapter('Ruang lingkup penelitian ini luas')['sections']['scope']['status']=='parse_failed'

def test_symbols_longest_alias(dictionary):
    a=dictionary.extract('Menggunakan C++, C# dan Multiple Linear Regression serta YOLO-v8 dan YOLO11 tanpa titik')
    assert {i['canonical'] for i in a['technology']['items']}=={'c++','c#'}
    terms={i['canonical'] for i in a['algorithm']['items']}
    assert 'multiple linear regression' in terms and 'linear regression' not in terms
    assert {'yolov8','yolov11'}<=terms
    assert tokens('C++ C# YOLOv8 Node.js TF-IDF')==['c++','c#','yolov8','node.js','tf-idf']

def test_unknown_no_false_match(dictionary):
    empty=dictionary.extract('')
    assert all(a['status']=='unknown' for a in empty.values())
    assert compare(empty,empty)['score']==0
    assert not compare(empty,empty)['similarities']

def test_roles(dictionary):
    a=dictionary.extract('Penelitian terdahulu menggunakan YOLOv8. Kami tidak menggunakan YOLO11. Menggunakan C++.')
    assert [i['role'] for i in a['algorithm']['items']]==['prior_work','rejected']
    assert a['technology']['items'][0]['role']=='used'

def test_platform_not_identity(dictionary):
    a=Extractor().extract('Kaggle citra')
    assert a['dataset_identity']['status']=='unknown'

def test_chunks_offsets():
    text=' '.join('kalimat nomor %s.'%i for i in range(80))
    c=chunk_text(text,Tokenizer(),32,'d','scope',overlap=4)
    assert len(c)>1 and all(x['token_count']<=32 for x in c)
    assert all(x['text']==text[x['start']:x['end']] and x['doc_id']=='d' for x in c)
    assert c[0]['start']==0 and c[-1]['end']==len(text)

def make_sources(tmp_path,rows):
    p=tmp_path/'source.xlsx'; wb=openpyxl.Workbook(); ws=wb.active; ws.title='data'
    ws.append(['Title','Abstract','Chapter_1','Year','ID','NRP','NamaPenulis'])
    for row in rows: ws.append(row)
    wb.save(p)
    return {'sources':[{'path':'source.xlsx','sheet':'data','department':'X'}],'dictionaries':[]}

def test_ingestion_stability_conflicts(tmp_path):
    a=['Metode C++','Teks penelitian yang informatif','',2024,'1','nrp','A']
    b=['Judul lain','Teks penelitian lain informatif','',2024,'2','nrp','A']
    conflict=['Metode C++','Abstrak berbeda dengan objek lainnya','',2024,'3','nrp2','B']
    rows=[a,a,b,conflict,['TIDAK DITEMUKAN',None,None,None,None,None,None]]
    c=make_sources(tmp_path,rows); docs,r=read_sources(c,tmp_path)
    assert len(docs)==3 and r['excluded_count']==1 and r['duplicates_merged']==1 and r['conflict_groups']==1
    assert max(len(d['provenance']) for d in docs)==2
    make_sources(tmp_path,list(reversed(rows))); docs2,_=read_sources(c,tmp_path)
    assert {d['id'] for d in docs}=={d['id'] for d in docs2}

def fixture_index(tmp_path,dictionary):
    c=make_sources(tmp_path,[['Sistem aksara sunda','Pengenalan citra aksara dengan metode penelitian','1.3 Ruang Lingkup Menggunakan C++.',2024,'1','','A'],['Prediksi penjualan','Analisis peramalan transaksi toko masa depan','',2024,'2','','B']])
    docs,report=read_sources(c,tmp_path); enc=FixtureEncoder(); fp=fingerprint(docs,dictionary,enc,report)
    return Index(docs,dictionary,enc,tmp_path/'cache',fp),report

def test_search_edges_and_cache(tmp_path,dictionary):
    idx,report=fixture_index(tmp_path,dictionary)
    with pytest.raises(ValueError): idx.search({'title':' '})
    with pytest.raises(ValueError): idx.search({'title':'!!!'})
    with pytest.raises(ValueError): idx.search({'title':'dan yang untuk'})
    with pytest.raises(ValueError): Index([],dictionary,FixtureEncoder(),tmp_path,'x')
    r=idx.search({'title':'aksara sunda C++'},100)
    assert len(r['results'])==2
    assert r['results'][0]['evidence'][0]['doc_id']==r['results'][0]['id']
    assert order([1,1],['b','a']).tolist()==[1,0]
    assert np.allclose(percentile([0,2,2]),[0,2/3,2/3])
    old=idx.fingerprint; changed=copy.deepcopy(idx.docs); changed[0]['abstract']+=' changed'
    assert fingerprint(changed,dictionary,idx.encoder,report)!=old
    rep=copy.deepcopy(report); rep['sources'][0]['sha256']='changed'
    assert fingerprint(idx.docs,dictionary,idx.encoder,rep)!=old
    assert fingerprint(list(reversed(idx.docs)),dictionary,idx.encoder,report)!=old
    assert fingerprint(idx.docs,Extractor(),idx.encoder,report)!=old
    with pytest.raises(ValueError): idx.search({'title':'aksara'},0)
    for config in ['legacy','sbert','bm25','plain_rrf','chunk_rrf','plain_w05','chunk_w07']:
        out=idx.search({'title':'aksara'},config=config)
        assert all(np.isfinite(r['hybrid_score']) for r in out['results'])
    reranked=idx.search({'title':'Menggunakan C++ untuk aksara'},rerank=.05)
    assert all(r['rerank_strength']==.05 for r in reranked['results'])
    assert set(r['hybrid_rank'] for r in reranked['results'])=={1,2}
    chunked=idx.search({'title':'aksara sunda'},config='chunk_rrf')
    assert 'query_chunk' in chunked['results'][0]['evidence'][0]
    no_signal=idx.search({'title':'zzzzzzunseen'},config='bm25')
    assert no_signal['no_positive_signal'] and no_signal['results']==[]

def test_metrics_multiple_relevance():
    m=metrics(['a','x','y','z','q','b'],{'a':2,'b':1,'c':1,'x':0},True)
    assert m['Recall@5']==1/3 and m['Recall@10']==2/3 and m['MRR']==1
    assert metrics(['a'],{'b':0}) is None

def test_components_no_leakage():
    groups=grouped_components([{'id':'q1','source_ids':['a']},{'id':'q2','source_ids':['b']},{'id':'q3','source_ids':['a','b']}])
    assert len(groups)==1 and len(groups[0]['queries'])==3

def test_zero_bm25():
    assert BM25([[],[]]).scores(['x']).tolist()==[0,0]

def test_index_search_evaluation(tmp_path,dictionary):
    from skripsi_search.evaluate import run_evaluation
    idx,_=fixture_index(tmp_path,dictionary)
    (tmp_path/'evaluation').mkdir()
    q={'id':'q','title':'aksara sunda','source_ids':[idx.docs[0]['id']],'legacy_group':'A'}
    (tmp_path/'evaluation/queries.json').write_text(json.dumps([q]))
    report=run_evaluation(idx,tmp_path)
    assert len(report['aggregate'])==9 and report['splits']['test']['queries']==0
    assert (tmp_path/'reports/evaluation/per_query.csv').exists()
