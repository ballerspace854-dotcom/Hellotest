from pathlib import Path
from html import escape
import json, re, os, sys, subprocess
from PIL import Image
import layoutlib as L

ROOT=Path(__file__).parent
L.ROOT=ROOT
TEMPLATES={1:1,2:6,3:7,4:8,5:23,6:18,7:2,8:10,9:5,10:9,11:19,12:16,13:13,14:12,15:4,16:21,17:24,18:15,19:3,20:27}
LIMITS={1:340,6:195,7:245,8:340,23:240,18:300,2:470,10:245,5:540,9:180,19:245,16:190,13:175,12:235,4:245,21:245,24:235,15:210,3:245,27:180}
ORIGINAL_BLOCK=L.block
ORIGINAL_IMAGE=L.image
CURRENT_HEAD=''
CURRENT_TEMPLATE=1
CURRENT_AD=1

def fit_block(s,x,y,width,size=80,color=L.NAVY,weight=700,serif=False,lineheight=1.08,maxheight=None):
    if s==CURRENT_HEAD:
        maxheight=min(maxheight or 9999,LIMITS[CURRENT_TEMPLATE])
    return ORIGINAL_BLOCK(s,x,y,width,size,color,weight,serif,lineheight,maxheight)

def fit_image(file,x,y,w,h,cover=True,align='xMidYMid',radius=0):
    # Flat lays remain wholly visible; a close crop would remove sensory items.
    if CURRENT_AD in {3,6,11,15,18} and h<1000:
        cover=False
    if CURRENT_AD in {2,17} and align=='xMidYMid':align='xMidYMin'
    return ORIGINAL_IMAGE(file,x,y,w,h,cover,align,radius)

L.block=fit_block
L.image=fit_image

def checklist(h,s):
    r=L.rect;t=L.text;b=L.block
    v=[r(0,0,1080,1350,'white'),b(h,60,110,960,88,maxheight=185),r(40,294,478,710,'#F0F2F2',10),r(550,294,490,710,L.BLUE,10),t('THICK OINTMENT',75,350,30,weight=700),L.image('scene-13.png',62,390,434,440,radius=6),t('Thick texture',75,925,34),t('AFTERWELL',585,350,30,weight=700)]
    for i,label in enumerate(['Light feel','Soaks in fast','No added fragrance','No steroids']):
        yy=429+i*61
        v.extend([t('✓',586,yy,31,weight=700),t(label,628,yy,30)])
    v += [L.jar(702,697,270),b(s,60,1105,690,34,weight=400),L.logo(60,1278,245)]
    return ''.join(v)

def schedule(h,s):
    # The diagram is separate from the candid photograph; no fake compliance result.
    r=L.rect;t=L.text;b=L.block
    v=[r(0,0,1080,1350,'#F6FAFD'),b(h,60,110,960,88,maxheight=195),L.image('scene-16.png',40,295,1000,650,cover=False,radius=8)]
    labels=['Bath','Cream','PJs']
    for i,label in enumerate(labels):
        xx=60+i*225
        v.extend([r(xx,1000,202,112,'white',10,L.NAVY,2),t(label,xx+101,1068,34,weight=700,anchor='middle')])
        if i<2:v.append(t('→',xx+209,1069,30))
    v += [L.jar(794,1000,285),b(s,60,1170,680,34,weight=400),L.logo(60,1280,225)]
    return ''.join(v)

def routine(h,s):
    r=L.rect;t=L.text;b=L.block
    v=[r(0,0,1080,1350,'#EDF5FB'),b(h,60,108,960,88,maxheight=205)]
    # Three distinct areas of one new routine still; they are actions, not results.
    W,H=Image.open(ROOT/'assets'/'scene-20.png').size
    regions=[(0,0,W*.58,H*.72),(W*.20,H*.10,W*.60,H*.76),(W*.40,H*.16,W*.60,H*.76)]
    for i,((vx,vy,vw,vh),label) in enumerate(zip(regions,['Bath','Pat dry','Thin layer'])):
        xx=40+i*340
        v.append(r(xx,350,318,650,'white',12))
        v.append(f'<defs><clipPath id="routine-{i}"><rect x="{xx+12}" y="365" width="294" height="540" rx="5"/></clipPath></defs><g clip-path="url(#routine-{i})"><svg x="{xx+12}" y="365" width="294" height="540" viewBox="{vx} {vy} {vw} {vh}" preserveAspectRatio="xMidYMid slice" overflow="hidden"><image width="{W}" height="{H}" xlink:href="../assets/scene-20.png"/></svg></g>')
        v.append(t(label,xx+159,962,32,weight=700,anchor='middle'))
    v += [b(s,60,1117,680,34,weight=400),L.jar(792,1030,270),L.logo(60,1280,225)]
    return ''.join(v)

def main(nums=None):
    global CURRENT_HEAD,CURRENT_TEMPLATE,CURRENT_AD
    d=json.loads((ROOT/'copy-plan.json').read_text())
    rows=d['ads'] if isinstance(d,dict) else d
    for a in rows:
        n=int(a['ad_number']);f=f'scene-{n:02}.png'
        if nums and n not in nums:continue
        if not (ROOT/'assets'/f).exists():print('WAIT',n,f);continue
        h=a['headline'];s=a['support'];foot=a.get('footnote','')
        assert 3<=len(h.split())<=9,(n,h)
        assert len(s.split())<=12,(n,s)
        assert re.search(r'autistic kids?|sensory kids?|kids on the spectrum',h+' '+s,re.I),(n,'missing target')
        assert not re.search(r'your autistic child|your child[’\']s eczema',h+' '+s,re.I)
        CURRENT_HEAD=h;CURRENT_TEMPLATE=TEMPLATES[n];CURRENT_AD=n
        L.MAP[CURRENT_TEMPLATE]=f
        if n==1:body=L.image(f,0,0,1080,1250,align='xMidYMin')+L.rect(552,38,500,355,'white',12)+L.block(h,580,118,440,84,maxheight=270)+L.panel_footer(s,y=1060,product_y=1000)
        elif n==5:body=L.rect(0,0,1080,1350,'white')+L.block(h,60,108,960,88,maxheight=180)+L.image(f,0,270,1080,850)+L.panel_footer(s,product_x=60,product_y=1010,y=1080,support_x=385,support_y=1150,support_w=640,logo_x=735)
        elif n==8:body=L.image(f,0,0,1080,1190,align='xMidYMin')+L.rect(42,50,470,435,'white',14)+L.block(h,75,130,405,74,maxheight=350)+L.panel_footer(s,product_x=60,product_y=1010,y=1080,support_x=385,support_y=1150,support_w=640,logo_x=735)
        elif n==13:body=checklist(h,s)
        elif n==16:body=schedule(h,s)
        elif n==19:body=L.image(f,0,0,1080,1170)+L.rect(0,0,1080,340,L.NAVY)+L.block(h,60,115,960,89,'white',maxheight=205)+L.panel_footer(s,product_x=60,product_y=995,y=1060,support_x=385,support_y=1145,support_w=640,logo_x=735)
        elif n==20:body=routine(h,s)
        else:body=L.design(CURRENT_TEMPLATE,h,s,foot)
        # In this set footnote-bearing flat lay11 has a left product, so position
        # the note on its right; template19 already handles that arrangement.
        slug=re.sub('[^a-z0-9]+','-',h.lower()).strip('-');name=f'{n:02}-{slug}'
        for folder,ext in [('statics','png'),('editable','svg')]:
            for p in (ROOT/folder).glob(f'{n:02}-*.{ext}'):
                if p.stem!=name:p.unlink()
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350"><title>{escape(h)}</title>{L.DEFS}{body}</svg>'
        sp=ROOT/'editable'/(name+'.svg');sp.write_text(svg)
        pp=ROOT/'statics'/(name+'.png')
        env={**os.environ,'XDG_CACHE_HOME':'/tmp/afterwell-font-cache','XDG_CONFIG_HOME':'/tmp/afterwell-config'}
        p=subprocess.run(['inkscape',str(sp),'--export-area-page','--export-width=1080','--export-height=1350',f'--export-filename={pp}'],capture_output=True,text=True,env=env)
        if p.returncode:raise RuntimeError(p.stderr)
        assert Image.open(pp).size==(1080,1350)
        record={**a,'filename':pp.name,'editable':sp.name,'scene_asset':f,'product_asset':'product-master.png','logo_asset':'afterwell-logo-blue.png','dimensions':[1080,1350],'layout':CURRENT_TEMPLATE}
        (ROOT/'source'/f'ad-{n:02}.json').write_text(json.dumps(record,indent=2,ensure_ascii=False))
        print('RENDERED',n,pp.name)

if __name__=='__main__':main(set(map(int,sys.argv[1:])) if len(sys.argv)>1 else None)
