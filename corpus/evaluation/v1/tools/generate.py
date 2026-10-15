"""Deterministic synthetic extraction corpus. No customer data or API calls."""
from __future__ import annotations
import copy
import argparse
import hashlib
import json
import math
import random
import shutil
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pdfplumber
import pypdfium2
from PIL import Image, ImageDraw, ImageFilter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

OUT = Path(__file__).resolve().parents[1]
SEED = 20261014
W,H = 595.2756,841.8898
FAMILIES = {'A':'Klassische Rechnung', 'B':'Rechnung mit Seitenleiste',
            'C':'Feldformular', 'D':'Mehrseitige Abrechnung',
            'E':'Gutschrift als Brief', 'F':'Rechnung mit englischen Feldnamen'}
KEYS=['belegnummer','belegdatum','gesamtbetrag','nettobetrag','steuerbetrag','waehrung','ust_idnr','dokumentart','absender']
NAMES=['Fiktivwerk Alpha GmbH','Fiktivwerk Beta GmbH','Fiktivwerk Gamma GmbH',
       'Fiktivwerk Delta GmbH','Fiktivwerk Epsilon GmbH','Fiktivwerk Zeta GmbH']
LABELS={'belegnummer':'Belegnummer','belegdatum':'Belegdatum','gesamtbetrag':'Gesamtbetrag',
        'nettobetrag':'Nettobetrag','steuerbetrag':'Umsatzsteuer','waehrung':'Währung',
        'ust_idnr':'USt-IdNr.','dokumentart':'Dokumentart','absender':'Aussteller'}
EN={'belegnummer':'Invoice number','belegdatum':'Invoice date','gesamtbetrag':'Grand total',
    'nettobetrag':'Subtotal','steuerbetrag':'Tax','waehrung':'Currency','ust_idnr':'VAT ID',
    'dokumentart':'Document type','absender':'Issued by'}

def money(value, en=False):
    s=f'{Decimal(value):,.2f}'
    return s if en else s.replace(',','@').replace('.',',').replace('@','.')

def build_truth(family,j):
    fi=ord(family)-65
    rng=random.Random(SEED+fi*100+j)
    items=[]
    for i in range(3+j%3):
        quantity=rng.randint(1,9)
        price=Decimal(rng.randint(375,249999))/100
        items.append({'name':f'Testartikel {i+1:02d}', 'quantity':quantity,
                      'unit_price':str(price), 'line_total':str(price*quantity)})
    net=sum(Decimal(i['line_total']) for i in items)
    rate=Decimal('0.07') if j%3==0 else Decimal('0.19')
    tax=(net*rate).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    sign=-1 if family=='E' else 1
    vals={'belegnummer':f'{"GS" if family=="E" else "INV"}-{family}-26-{j+1:04d}',
          'belegdatum':f'2026-{j+1:02d}-{10+fi:02d}',
          'gesamtbetrag':f'{sign*(net+tax):.2f}', 'nettobetrag':f'{sign*net:.2f}',
          'steuerbetrag':f'{sign*tax:.2f}', 'waehrung':'USD' if family=='F' else 'EUR',
          'ust_idnr':f'DE{970000000+fi*100+j}',
          'dokumentart':'Gutschrift' if family=='E' else 'Rechnung', 'absender':NAMES[fi]}
    if j==8:
        vals['ust_idnr']=None
    if j==9:
        vals['belegnummer']=None
        vals['belegdatum']=None
    printed={k:v for k,v in vals.items()}
    for k in ['gesamtbetrag','nettobetrag','steuerbetrag']:
        printed[k]=money(vals[k],family=='F')
    if vals['belegdatum'] and family!='F':
        y,m,d=vals['belegdatum'].split('-'); printed['belegdatum']=f'{d}.{m}.{y}'
    if family=='F': printed['dokumentart']='Invoice'
    return vals,printed,items,str(rate)


class PageWriter:
    def __init__(self,path,fields):
        self.c=canvas.Canvas(str(path),pagesize=(W,H),invariant=1)
        self.c.setTitle('Synthetischer Extraktions-Testbeleg')
        self.fields=fields; self.page=0; self.boxes=[]
    def text(self,x,y,text,size=10,bold=False,color='#182D3A',key=None):
        if text is None: return
        font='Helvetica-Bold' if bold else 'Helvetica'
        self.c.setFillColor(color); self.c.setFont(font,size)
        self.c.drawString(x,H-y,str(text))
        box=[x,y-size,x+stringWidth(str(text),font,size),y+size*.25]
        assert box[0]>=0 and box[2]<W-15 and box[1]>=0 and box[3]<H-15,(text,box)
        self.boxes.append(box)
        if key:
            self.fields[key]['locators'].append({'page':self.page,'bbox':box,'unit':'pt','origin':'top-left'})
    def line(self,x,y,x2,y2,color='#A7B5BF'):
        self.c.setStrokeColor(color); self.c.setLineWidth(.5)
        self.c.line(x,H-y,x2,H-y2)
    def rect(self,x,y,w,h,color='#EFF3F5'):
        self.c.setFillColor(color); self.c.rect(x,H-y-h,w,h,fill=1,stroke=0)
    def footer(self):
        self.line(40,790,555,790)
        self.text(40,807,'SYNTHETISCHE TESTDATEN - KEIN GESCHAEFTSBELEG',8,color='#667984')
        self.text(510,807,f'Seite {self.page+1}',8,color='#667984')
    def next(self):
        self.footer(); self.c.showPage(); self.page+=1
    def save(self):
        self.footer(); self.c.save(); return self.page+1


def original(path,f,j,vals,printed,items,rate):
    fields={k:{'value':v,'printed':printed[k],'status':'absent' if v is None else 'present','locators':[]} for k,v in vals.items()}
    p=PageWriter(path,fields); labels=EN if f=='F' else LABELS
    def field(k,x,y,vertical=False,size=10):
        p.text(x,y,labels[k]+':',9,color='#526674')
        if vertical:
            p.text(x,y+18,printed[k],size,True,key=k)
        else:
            p.text(x+112,y,printed[k],size,key=k)
    def title(x=40,y=55):
        p.text(x,y,printed['dokumentart'],23,True,key='dokumentart')
    def issuer(x=40,y=95):
        p.text(x,y,printed['absender'],13,True,key='absender')
        p.text(x,y+17,'Testweg 12 | 00000 Musterstadt',9)
        p.text(x,y+32,'kontakt@example.invalid',9)
    def recipient(x=40,y=175):
        p.text(x,y,'Empfänger: Beispielkunde Testbetrieb',11,True)
        p.text(x,y+18,'Musterallee 8 | 00000 Beispielort',9)
    def distractions(y=270):
        p.text(40,y,f'Bestellung / PO: PO-{f}-{900+j}    Kundennummer: K-{1500+j}',9)
        p.text(40,y+16,f'Lieferdatum / Delivery: {11+ord(f)-65:02d}.12.2025',9)
    def table(y=325,rows=None):
        rows=items if rows is None else rows
        p.rect(40,y-15,515,23)
        for x,t in [(45,'Pos.'),(80,'Artikel / Item'),(300,'Menge'),(370,'Einzelpreis'),(470,'Zeilensumme')]: p.text(x,y,t,9,True)
        for n,item in enumerate(rows):
            yy=y+28+n*25
            for x,t in [(45,str(n+1)),(80,item['name']),(300,str(item['quantity'])),
                        (370,money(item['unit_price'],f=='F')),(470,money(item['line_total'],f=='F'))]:p.text(x,yy,t,9)
            p.line(40,yy+9,555,yy+9)
    def totals(y=560):
        for n,k in enumerate(['nettobetrag','steuerbetrag','gesamtbetrag','waehrung']):
            yy=y+n*25
            if k=='gesamtbetrag':p.rect(315,yy-17,240,24,'#E2EDF1')
            p.text(325,yy,labels[k],10,k=='gesamtbetrag')
            p.text(455,yy,printed[k],10,k=='gesamtbetrag',key=k)
        p.text(325,y+108,'Steuersatz / Tax rate: '+str(int(Decimal(rate)*100))+' %',9)
    if f=='A':
        title();issuer();recipient();field('belegnummer',330,175);field('belegdatum',330,198)
        distractions();table();totals();field('ust_idnr',40,735)
    elif f=='B':
        p.rect(25,25,190,250,'#E2EDF1');title(40,65);issuer(235,65)
        field('belegnummer',40,115,True);field('belegdatum',40,170,True)
        field('ust_idnr',235,135,True);recipient(235,210)
        distractions(295);table(355);totals(570)
    elif f=='C':
        title();issuer();recipient(40,170)
        for k,x,y in [('belegnummer',40,235),('belegdatum',310,235),('ust_idnr',40,300),('waehrung',310,300)]:
            p.rect(x,y-18,245,58);field(k,x+10,y,True)
        table(405);totals(595)
    elif f=='D':
        title();issuer();recipient();field('belegnummer',330,175);field('belegdatum',330,198)
        distractions();table(345)
        p.text(40,610,'Fortsetzung und endgültiger Gesamtbetrag auf der Folgeseite.',11,True)
        p.text(40,645,'Zwischensumme Positionen 1-2: '+money(sum(Decimal(i['line_total']) for i in items[:2]))+' EUR',10)
        p.next();p.text(40,60,'Abschluss der Abrechnung',20,True)
        p.text(40,95,'Die folgende Summe umfasst alle Positionen der vorherigen Seite.',10)
        totals(240);field('ust_idnr',40,470)
        p.text(40,540,'Zahlungsziel: 30 Tage. Bitte nur den Endbetrag überweisen.',10)
    elif f=='E':
        issuer(40,55);recipient(40,145);title(40,235)
        field('belegnummer',40,275);field('belegdatum',40,298);field('ust_idnr',40,321)
        p.text(40,365,'Sehr geehrte Damen und Herren,',11)
        p.text(40,390,'wir schreiben die folgenden zurückgegebenen Testartikel gut.',11)
        p.text(40,412,f'Bezug: ursprüngliche Rechnung ALT-{j+1:04d} vom 02.01.2025.',10)
        table(455);totals(635)
    elif f=='F':
        p.rect(25,25,545,65,'#E6EEF2');title(40,65);issuer(40,125)
        field('belegnummer',330,125,True);field('belegdatum',330,180,True)
        recipient(40,225);field('ust_idnr',330,245,True)
        distractions(305);table(370);totals(590)
    pages=p.save()
    for k,field_data in fields.items():
        assert bool(field_data['locators']) == (field_data['status']=='present'),k
    return fields,pages


def rotated_box(box,angle,width,height):
    a=math.radians(angle); c,s=math.cos(a),math.sin(a); cx,cy=width/2,height/2
    points=[]
    for x,y in [(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])]:
        dx,dy=x-cx,y-cy
        points.append([cx+c*dx+s*dy,cy-s*dx+c*dy])
    return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]


def scan(source,dest,fields,variant,seed):
    rng=np.random.default_rng(seed); dpi=150 if variant=='scan' else 110
    angle=1.7 if variant=='scan' else -2.6
    doc=pypdfium2.PdfDocument(str(source)); c=canvas.Canvas(str(dest),pagesize=(W,H),invariant=1)
    for page in doc:
        im=page.render(scale=dpi/72).to_pil().convert('L')
        im=im.rotate(angle,resample=Image.Resampling.BICUBIC,fillcolor=255)
        ar=np.asarray(im,dtype=np.float32)
        strength=7 if variant=='scan' else 15
        ar=255-(255-ar)*(.88 if variant=='scan' else .7)
        ar+=rng.normal(0,strength,ar.shape)
        if variant=='photo':ar-=np.linspace(0,36,ar.shape[1])[None,:]
        im=Image.fromarray(np.uint8(np.clip(ar,0,255)))
        if variant=='photo':im=im.filter(ImageFilter.GaussianBlur(.38))
        c.drawImage(ImageReader(im),0,0,width=W,height=H);c.showPage()
    c.save();doc.close()
    result=copy.deepcopy(fields)
    for field in result.values():
        for loc in field['locators']:
            loc['bbox']=rotated_box(loc['bbox'],angle,W,H)
    return result,{'dpi':dpi,'rotation_degrees':angle,'noise_sigma':strength,
                   'blur_sigma':.38 if variant=='photo' else 0,
                   'description':'simulated degradation, not a real camera capture'}


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    OUT=parser.parse_args().output.resolve()
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for f in FAMILIES:
        for j in range(10):
            split='unseen_layout' if f in 'DEF' else ('setup' if j<6 else 'known_layout')
            group=f'{f}{j+1:02d}';vals,printed,items,rate=build_truth(f,j)
            folder=OUT/'inputs'/split;folder.mkdir(parents=True,exist_ok=True)
            target=folder/f'{group}_digital.pdf'
            fields,pages=original(target,f,j,vals,printed,items,rate)
            def record(path,variant,fs,transform=None):
                records.append({'id':path.stem,'group_id':group,'split':split,'family':f,
                    'family_description':FAMILIES[f], 'variant':variant,'path':path.relative_to(OUT).as_posix(),
                    'pages':pages,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'fields':fs,'items':items,'tax_rate':rate,'transform':transform,
                    'tags':(['missing_vat'] if j==8 else ['missing_id_and_date'] if j==9 else [])+
                           (['credit_negative_amounts'] if f=='E' else [])+
                           (['multipage'] if pages>1 else [])})
            record(target,'digital',fields)
            if j in (2,7):
                for variant in ['scan','photo']:
                    dest=folder/f'{group}_{variant}.pdf'
                    fs,trans=scan(target,dest,fields,variant,SEED+ord(f)*100+j)
                    record(dest,variant,fs,trans)
    truth=OUT/'ground_truth';truth.mkdir(exist_ok=True)
    (truth/'expected.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in records)+'\n',encoding='utf-8')
    (OUT/'manifest.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ('fields','items','tax_rate')} for r in records],ensure_ascii=False,indent=2),encoding='utf-8')
    schema={'type':'object','additionalProperties':False,'properties':{k:{'type':['string','null']} for k in KEYS},'required':KEYS}
    schema['properties']['dokumentart']['description']='Canonical German category: Rechnung or Gutschrift.'
    schema['properties']['belegdatum']['description']='ISO date YYYY-MM-DD, or null if no document issue date is printed. Do not substitute delivery date.'
    schema['properties']['gesamtbetrag']['description']='Final gross document amount as decimal string with two decimal places. Preserve the printed negative sign for credit notes; do not substitute line totals or subtotals.'
    schema['properties']['ust_idnr']['description']='Issuer VAT identifier exactly as printed, even if synthetically invalid. Null when absent.'
    (OUT/'field-schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
    # Validate independently through PDF extraction, arithmetic and group membership.
    counts={}; page_count=0
    for r in records:
        counts[r['split']]=counts.get(r['split'],0)+1;page_count+=r['pages']
        with pdfplumber.open(OUT/r['path']) as pdf:
            assert len(pdf.pages)==r['pages']
            texts=[p.extract_text() or '' for p in pdf.pages]
            if r['variant']=='digital':
                for k,field in r['fields'].items():
                    for loc in field['locators']:
                        assert field['printed'] in texts[loc['page']],(r['id'],k,field['printed'])
            else:assert not any(texts),'Scan unexpectedly contains selectable text'
        vals={k:v['value'] for k,v in r['fields'].items()}
        assert Decimal(vals['nettobetrag'])+Decimal(vals['steuerbetrag'])==Decimal(vals['gesamtbetrag'])
        for field in r['fields'].values():
            for loc in field['locators']:
                x0,y0,x1,y1=loc['bbox'];assert 0<=x0<x1<=W and 0<=y0<y1<=H
    assert len(records)==84
    assert all(len({r['split'] for r in records if r['group_id']==g})==1 for g in {r['group_id'] for r in records})
    stats={'documents':len(records),'source_documents':60,'layout_families':6,
           'pages':page_count,'split_counts':counts,'seed':SEED,'fields_per_document':len(KEYS),
           'absent_field_instances':sum(f['status']=='absent' for r in records for f in r['fields'].values()),
           'validation':'All document hashes, native PDF field strings, page counts, amount sums, coordinate bounds, image-only scan PDFs and group-disjoint splits checked.'}
    (OUT/'validation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
