"""Score predictions without making model calls. Python standard library only."""
import argparse
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import statistics

ROOT=Path(__file__).resolve().parent
DEFAULT_FIELDS=['belegnummer','belegdatum','gesamtbetrag','ust_idnr']

def canonical(key,value):
    if value is None: return None
    if not isinstance(value,str): return ('invalid_type',repr(value))
    value=value.strip()
    if not value: return ('empty_string',)
    if key in ('gesamtbetrag','nettobetrag','steuerbetrag'):
        v=re.sub(r'\s|EUR|USD|€|\$', '',value,flags=re.I)
        if ',' in v and '.' in v:
            v=v.replace('.','').replace(',','.') if v.rfind(',')>v.rfind('.') else v.replace(',','')
        elif ',' in v:v=v.replace(',','.')
        try:
            n=Decimal(v)
            return n if n.is_finite() else ('invalid_amount',value)
        except InvalidOperation:return ('invalid_amount',value)
    if key=='belegdatum':
        for fmt in ('%Y-%m-%d','%d.%m.%Y'):
            try:return datetime.strptime(value,fmt).date().isoformat()
            except ValueError:pass
        return ('invalid_date',value)
    if key=='ust_idnr':return re.sub(r'\s+','',value).upper()
    if key=='waehrung':return value.upper()
    return value

def evaluate(truth,predictions,fields):
    ids={r['id'] for r in truth}
    supplied={}
    for p in predictions:
        if p['id'] in supplied:raise ValueError('Duplicate prediction ID: '+p['id'])
        if p['id'] not in ids:raise ValueError('Unknown prediction ID: '+p['id'])
        if not isinstance(p.get('fields'),dict):raise ValueError('fields must be an object')
        supplied[p['id']]=p
    groups=defaultdict(lambda:dict(documents=0,fields=0,correct=0,present=0,present_correct=0,
        absent=0,absent_correct=0,hallucinated_absent=0,complete_documents=0,
        missing_predictions=0,review_flagged=0,incorrect_without_review=0))
    details=[]
    for r in truth:
        p=supplied.get(r['id']);vals=p['fields'] if p else {};review=set(p.get('review_fields',[])) if p else set()
        per=[]
        for k in fields:
            e=r['fields'][k]['value'];v=vals.get(k)
            correct=k in vals and canonical(k,e)==canonical(k,v)
            per.append((k,correct,e,v,k in review))
            details.append({'id':r['id'],'field':k,'expected':e,'predicted':v,
                            'supplied':k in vals,'correct':correct,'review_flagged':k in review})
        for group in ['all','split:'+r['split'],'family:'+r['family'],'variant:'+r['variant']]:
            s=groups[group];s['documents']+=1;s['fields']+=len(fields)
            s['missing_predictions']+=int(p is None)
            s['complete_documents']+=int(all(x[1] for x in per))
            for k,correct,e,v,flag in per:
                s['correct']+=int(correct);s['review_flagged']+=int(flag)
                if e is None:
                    s['absent']+=1;s['absent_correct']+=int(correct)
                    s['hallucinated_absent']+=int(k in vals and v is not None)
                else:s['present']+=1;s['present_correct']+=int(correct)
                s['incorrect_without_review']+=int(k in vals and v is not None and not correct and not flag)
    return {'fields_evaluated':fields,'summary':dict(groups),'details':details,
      'note':'incorrect_without_review assumes every supplied non-null field without a review flag would be accepted. It is not a measured human error rate. Missing documents and missing keys count as errors. Null is correct only for absent fields.'}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('predictions',type=Path)
    a.add_argument('--split',choices=['all','setup','known_layout','unseen_layout'],default='all')
    a.add_argument('--fields',default=','.join(DEFAULT_FIELDS))
    a.add_argument('--output',type=Path,default=Path('scores.json'))
    args=a.parse_args()
    truth=[json.loads(l) for l in (ROOT/'ground_truth/expected.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    predictions=[json.loads(l) for l in args.predictions.read_text(encoding='utf-8').splitlines() if l.strip()]
    selected=[r for r in truth if args.split=='all' or r['split']==args.split]
    # Reject unknown or duplicate IDs even if they would be filtered from this split.
    all_ids={r['id'] for r in truth};seen=set()
    for p in predictions:
        if p['id'] not in all_ids or p['id'] in seen:raise ValueError('Unknown or duplicate prediction ID: '+p['id'])
        seen.add(p['id'])
    ids={r['id'] for r in selected}
    result=evaluate(selected,[p for p in predictions if p['id'] in ids],args.fields.split(','))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
