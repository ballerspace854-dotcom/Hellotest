from pathlib import Path
from html import escape
import json, re, os, subprocess, sys
from PIL import Image, ImageFont

ROOT = Path(__file__).parent
NAVY = '#1E2A5A'
BLUE = '#E9F2F9'
INK = '#18264D'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
MAP = {1:'scene-01.png',2:'scene-02.png',3:'new-03.png',4:'scene-05.png',5:'scene-12.png',6:'new-06.png',7:'new-07.png',8:'new-08.png',9:'new-09.png',10:'scene-17.png',11:'new-11.png',12:'scene-14.png',13:'scene-03.png',14:None,15:'scene-10.png',16:'scene-16.png',17:None,18:'new-18.png',19:'new-19.png',20:None,21:'new-21.png',22:'scene-18.png',23:'scene-04.png',24:'new-24.png',25:'new-25.png',26:'scene-07.png',27:'scene-13.png',28:'scene-11.png',29:'new-29.png',30:'new-30.png'}

def rect(x,y,w,h,fill='white',rx=0,stroke=None,sw=1):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+'/>'

def text(s,x,y,size=36,color=NAVY,weight=400,family='DejaVu Sans',anchor='start',spacing=None):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}"'+(f' letter-spacing="{spacing}"' if spacing else '')+'>'+escape(s)+'</text>'

def wrap(s,width,size,bold=False,serif=False):
    f=ImageFont.truetype(SERIF if serif else BOLD if bold else FONT,int(size))
    if '\n' in s:
        return [line for p in s.split('\n') for line in wrap(p,width,size,bold,serif)]
    out=[];line=''
    for word in s.split():
        nxt=(line+' '+word).strip()
        if line and f.getlength(nxt)>width:out.append(line);line=word
        else:line=nxt
    if line:out.append(line)
    return out

def block(s,x,y,width,size=80,color=NAVY,weight=700,serif=False,lineheight=1.08,maxheight=None):
    rows=wrap(s,width,size,weight>=600,serif)
    while maxheight and len(rows)*size*lineheight>maxheight and size>30:
        size-=2;rows=wrap(s,width,size,weight>=600,serif)
    family='DejaVu Serif' if serif else 'DejaVu Sans'
    return ''.join(text(v,x,y+i*size*lineheight,size,color,weight,family) for i,v in enumerate(rows))

def image(file,x,y,w,h,cover=True,align='xMidYMid',radius=0):
    href='../assets/'+file
    tag=f'<image x="{x}" y="{y}" width="{w}" height="{h}" xlink:href="{escape(href)}" preserveAspectRatio="{align} '+('slice' if cover else 'meet')+'"/>'
    if radius:
        cid='clip'+str(abs(hash((file,x,y,w,h))))
        tag=f'<defs><clipPath id="{cid}">{rect(x,y,w,h,"white",radius)}</clipPath></defs><g clip-path="url(#{cid})">{tag}</g>'
    return tag

def isolated(file,x,y,w,h):
    im=Image.open(ROOT/'assets'/file)
    bbox=im.getchannel('A').point(lambda a:255 if a>32 else 0).getbbox() if im.mode=='RGBA' else (0,0,*im.size)
    l,t,r,b=bbox;pad=3;l=max(0,l-pad);t=max(0,t-pad);r=min(im.width,r+pad);b=min(im.height,b+pad)
    return f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{l} {t} {r-l} {b-t}" preserveAspectRatio="xMidYMid meet"><image width="{im.width}" height="{im.height}" xlink:href="../assets/{file}"/></svg>'

def jar(x=765,y=1005,h=285):
    return isolated('product-master.png',x,y,h*.86,h)

def logo(x=58,y=1276,w=220):
    return isolated('afterwell-logo-blue.png',x,y,w,w*.20)

def panel_footer(s,product_x=775,product_y=1005,product_h=285,y=1015,fill='white',support_x=60,support_y=1110,support_w=650,logo_x=60):
    return rect(0,y,1080,1350-y,fill)+block(s,support_x,support_y,support_w,36,weight=400)+jar(product_x,product_y,product_h)+logo(logo_x)

DEFS='''<defs><linearGradient id="lighttop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="white" stop-opacity=".98"/><stop offset=".7" stop-color="white" stop-opacity=".84"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient><linearGradient id="darktop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0C1735" stop-opacity=".94"/><stop offset="1" stop-color="#0C1735" stop-opacity="0"/></linearGradient><linearGradient id="darkleft"><stop offset="0" stop-color="#0C1735" stop-opacity=".98"/><stop offset="1" stop-color="#0C1735" stop-opacity=".04"/></linearGradient><filter id="shadow" x="-.3" y="-.3" width="1.6" height="1.6"><feDropShadow dx="0" dy="8" stdDeviation="12" flood-opacity=".10"/></filter></defs>'''

def design(n,h,s,foot=''):
    f=MAP[n];v=[]
    if n==1:
        v=[image(f,0,0,1080,1200),rect(0,0,1080,530,'url(#lighttop)'),block(h,58,112,940,98),panel_footer(s,y=1060,product_y=1000)]
    elif n==2:
        v=[rect(0,0,1080,1350,NAVY),image(f,245,0,835,1140),rect(0,0,1080,1080,'url(#darkleft)'),block(h,60,126,770,94,'white',maxheight=510),panel_footer(s,y=1090,product_y=1015,support_y=1165)]
    elif n==3:
        v=[rect(0,0,1080,1350,'#F4F6F7'),block(h,60,112,960,92),rect(38,325,1004,690,'white',12),image(f,53,340,974,660,align='xMidYMin',radius=6),block(s,390,1110,610,34,weight=400),jar(64,1010,278),logo(700,1280,250)]
    elif n==4:
        v=[image(f,0,0,1080,1160),'<g transform="rotate(-2 520 220)">',rect(42,53,996,345,'white',5),block(h,84,155,905,83),'</g>',panel_footer(s,y=1060,product_x=65,product_y=998,support_x=388,support_w=630,logo_x=710)]
    elif n==5:
        v=[image(f,265,0,815,1115),rect(0,0,510,680,NAVY),block(h,52,115,410,86,'white',maxheight=550),panel_footer(s,y=1080,product_y=1015,support_y=1152)]
    elif n==6:
        v=[image(f,0,0,1080,1015),rect(0,940,1080,410,NAVY),rect(40,1015,280,290,'white',10),jar(55,1007,280),block(h,370,1035,650,78,'white',maxheight=190),block(s,370,1238,650,31,'white',weight=400),rect(54,1295,250,48,'white',3),logo(66,1300,205)]
    elif n==7:
        v=[rect(0,0,1080,1350,BLUE),image(f,36,180,1008,910,radius=14),rect(60,44,960,280,'white',8),rect(60,44,10,280,NAVY),block(h,98,142,860,92),panel_footer(s,y=1095,fill=BLUE,product_y=1010,support_y=1165)]
    elif n==8:
        v=[image(f,0,0,1080,1200),rect(0,0,1080,550,'url(#darktop)'),block(h,62,135,930,92,'white',serif=True),panel_footer(s,y=1090,product_x=72,product_y=1015,support_x=390,support_y=1170,support_w=620,logo_x=727)]
    elif n==9:
        v=[rect(0,0,1080,1350,'#F7FAFC'),image(f,38,38,1004,895,radius=8),block(h,56,1028,710,76,maxheight=180),block(s,56,1215,700,31,weight=400),jar(804,996,286),logo(62,1283,230)]
    elif n==10:
        v=[image(f,0,0,1080,1140),rect(46,50,988,318,'white',20),block(h,86,151,905,90),panel_footer(s,y=1080,product_y=1000,support_y=1150)]
    elif n==11:
        v=[image(f,0,0,1080,1200),'<g transform="rotate(2 530 210)">',rect(45,50,990,350,'#FCFCF7',2),block(h,90,145,890,83,serif=True),'</g>',panel_footer(s,y=1080,product_x=60,product_y=1010,support_x=375,support_w=655,support_y=1160,logo_x=736)]
    elif n==12:
        v=[rect(0,0,1080,1350,BLUE),block(h,62,113,955,84),'<g transform="rotate(-2 540 645)">',rect(48,303,984,680,'white'),image(f,64,319,952,648),'</g>',block(s,62,1095,660,36,weight=400),jar(786,1000,300),logo(62,1280)]
    elif n==13:
        v=[rect(0,0,1080,1350,'white'),block(h,60,115,960,84,maxheight=175),rect(38,286,489,715,'#F0F0ED',10),rect(553,286,489,715,BLUE,10),text('THICK OINTMENT',70,339,29,weight=700),image(f,56,370,453,600,radius=4),text('AFTERWELL',590,339,29,weight=700),block('Sea moss. Aloe. Oats.',590,417,390,43),jar(673,611,330),block(s,60,1090,650,35,weight=400),logo(62,1276,245)]
    elif n==14:
        v=[rect(0,0,1080,1350,NAVY),block(h,60,117,960,83,'white'),rect(38,320,489,710,'#F0F2F3',8),rect(553,320,489,710,BLUE,8),text('“UNSCENTED”',75,382,35,weight=700),text('NO ADDED FRAGRANCE',580,382,29,weight=700),'<g transform="rotate(-7 265 640)">'+rect(160,450,200,330,'white',18,NAVY,2)+rect(184,774,150,55,NAVY,3)+text('UNSCENTED',260,596,23,weight=700,anchor='middle')+'</g>',block('May use scent to hide smells.',92,905,380,34,weight=400),jar(671,604,340),block(s,60,1117,690,35,'white',weight=400),rect(44,1260,285,72,'white',5),logo(62,1278,245)]
    elif n==15:
        v=[rect(0,0,1080,1350,BLUE),block(h,60,115,960,87),rect(35,313,495,708,'white',8),image(f,50,390,465,480,radius=4),rect(550,313,495,708,'white',8),text('PRESCRIBED CREAM',66,370,29,weight=700),text('DAILY CREAM',586,370,29,weight=700),text('Use as prescribed.',71,950,33),jar(681,539,340),text('No steroids.',629,950,33),block(s,60,1112,670,35,weight=400),logo(62,1278,245)]
    elif n==16:
        v=[rect(0,0,1080,1350,'white'),image(f,0,285,650,850),rect(630,285,450,850,BLUE),block(h,56,102,970,79,maxheight=190),text('THE OLD TUB',45,350,27,weight=700),text('AFTERWELL',684,350,27,weight=700),jar(717,674,320),block(s,60,1205,690,33,weight=400),logo(740,1280,265)]
    elif n==17:
        v=[rect(0,0,1080,1350,'#F8FAFC'),rect(0,0,1080,330,NAVY),block(h,60,110,955,84,'white',maxheight=260),rect(40,350,470,655,'#E8EDF1',10),rect(144,447,260,410,'white',8,NAVY,1),text('INGREDIENTS',170,492,22,weight=700),rect(550,350,490,655,BLUE,10),text('INCLUDES',590,403,24,weight=700),block('Sea moss. Aloe. Oats.',590,483,390,50),jar(705,675,270),block(s,60,1105,670,34,weight=400),logo(62,1280,245)]
        for k in range(13):v.append(rect(171,524+k*21,195-(k%3)*22,5,'#B2BAC4',2))
    elif n==18:
        v=[image(f,0,0,1080,1230),rect(0,0,1080,440,'url(#lighttop)'),block(h,60,116,965,88),rect(310,760,460,460,'#FFFFFF',230),jar(420,810,370),rect(0,1210,1080,140,'white'),block(s,60,1258,670,28,weight=400),logo(773,1273,240)]
    elif n==19:
        v=[image(f,0,0,1080,1100),rect(50,62,912,340,NAVY,8),block(h,90,163,822,80,'white'),panel_footer(s,y=1065,product_x=60,product_y=990,support_x=380,support_y=1150,support_w=650,logo_x=730)]
    elif n==20:
        v=[rect(0,0,1080,1350,'#F9FCFF'),block(h,60,116,950,94),rect(105,400,870,660,'white',24),jar(352,416,520),rect(60,830,252,190,BLUE,4),block('Contains oats. Patch test first.',80,884,212,29,weight=400),block(s,60,1128,920,35,weight=400),logo(62,1277,260)]
    elif n==21:
        v=[image(f,0,0,1080,1160),rect(0,0,1080,390,'url(#lighttop)'),block(h,58,115,960,89),panel_footer(s,y=1058,product_y=990,support_y=1148)]
    elif n==22:
        v=[rect(0,0,1080,1350,NAVY),image(f,375,0,705,1160),rect(0,0,1080,1160,'url(#darkleft)'),block(h,62,135,780,95,'white',maxheight=540),panel_footer(s,y=1110,product_y=1030,support_y=1195)]
    elif n==23:
        v=[rect(0,0,1080,1350,BLUE),image(f,30,30,1020,940,radius=6),rect(45,650,990,330,'white',6),block(h,85,755,900,88),jar(63,1010,280),block(s,386,1103,630,34,weight=400),logo(738,1280,260)]
    elif n==24:
        v=[rect(0,0,1080,1350,'white'),block(h,60,113,950,90),image(f,38,330,1004,700,radius=16),panel_footer(s,y=1085,product_y=1004,support_y=1160)]
    elif n==25:
        v=[image(f,0,225,1080,980),rect(0,0,1080,330,NAVY),block(h,60,110,960,91,'white'),panel_footer(s,y=1060,product_x=60,product_y=996,support_x=383,support_w=645,support_y=1145,logo_x=735)]
    elif n==26:
        v=[image(f,0,0,1080,1170),rect(0,0,1080,540,'url(#lighttop)'),block(h,60,118,925,90,serif=True),panel_footer(s,y=1070,product_y=1005,support_y=1146)]
    elif n==27:
        v=[rect(0,0,1080,1350,'white'),rect(0,0,1080,260,BLUE),block(h,60,105,960,88),image(f,40,302,1000,742,radius=14),panel_footer(s,y=1095,product_y=1000,support_y=1170)]
    elif n==28:
        v=[image(f,0,0,1080,1160),rect(48,52,984,355,'#FCFCF7',5),block(h,89,150,900,86),panel_footer(s,y=1070,product_y=1000,support_y=1150)]
    elif n==29:
        v=[image(f,0,0,1080,1210),rect(0,0,1080,530,'url(#lighttop)'),block(h,60,125,950,91),rect(62,855,360,378,'white',12),jar(90,885,340),rect(0,1230,1080,120,'white'),block(s,455,1130,570,34,weight=400),logo(773,1277,245)]
    elif n==30:
        v=[rect(0,0,1080,1350,NAVY),image(f,310,0,770,1080),rect(0,0,1080,1080,'url(#darkleft)'),block(h,60,126,700,92,'white',maxheight=490),panel_footer(s,y=1095,product_y=1015,support_y=1165)]
    if foot and n!=20:
        # Brief-required patch note remains readable and separate from the hook.
        fx=375 if n in [4,8,11,19,23,25] else 60
        v.append(rect(fx-14,1211,695 if fx==60 else 655,47,'white',3))
        v.append(text(foot,fx,1245,27))
    return ''.join(v)

def main(nums=None):
    data=json.loads((ROOT/'copy-plan.json').read_text())
    rows=data['ads'] if isinstance(data,dict) else data
    out=[]
    for r in rows:
        n=int(r['ad_number'])
        if nums and n not in nums:continue
        if MAP[n] and not (ROOT/'assets'/MAP[n]).exists():
            print(f'WAIT {n:02}: {MAP[n]}');continue
        h=r['headline'];s=r['support'];foot=r.get('footnote','')
        assert 3<=len(h.split())<=8,(n,h,len(h.split()))
        assert len(s.split())<=12,(n,s,len(s.split()))
        slug=re.sub('[^a-z0-9]+','-',h.lower()).strip('-')
        name=f'{n:02}-{slug}'
        for folder,ext in [('statics','png'),('editable','svg')]:
            for old in (ROOT/folder).glob(f'{n:02}-*.{ext}'):
                if old.stem!=name:old.unlink()
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350"><title>{escape(h)}</title>{DEFS}{design(n,h,s,foot)}</svg>'
        p=ROOT/'editable'/(name+'.svg');p.write_text(svg)
        png=ROOT/'statics'/(name+'.png')
        env={**os.environ,'XDG_CACHE_HOME':'/tmp/afterwell-font-cache','XDG_CONFIG_HOME':'/tmp/afterwell-config'}
        proc=subprocess.run(['inkscape',str(p),'--export-area-page','--export-width=1080','--export-height=1350',f'--export-filename={png}'],capture_output=True,text=True,env=env)
        if proc.returncode:raise RuntimeError(proc.stderr)
        with Image.open(png) as im:assert im.size==(1080,1350)
        record={**r,'filename':png.name,'editable':p.name,'scene_asset':MAP[n],'product_asset':'product-master.png','logo_asset':'afterwell-logo-blue.png','dimensions':[1080,1350]}
        (ROOT/'source'/f'ad-{n:02}.json').write_text(json.dumps(record,indent=2,ensure_ascii=False))
        out.append(n);print('RENDERED',n,png.name)
    print('Rendered:',out)

if __name__=='__main__':main(set(map(int,sys.argv[1:])) if len(sys.argv)>1 else None)
