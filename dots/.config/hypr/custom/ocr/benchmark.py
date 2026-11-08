#!/usr/bin/env python3
"""Controlled English fixtures, fresh OCR processes, clipboard/notifications mocked."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import statistics
import subprocess
import tempfile
import sys
import time
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
SANS='/usr/share/fonts/noto/NotoSans-Regular.ttf'
SERIF='/usr/share/fonts/noto/NotoSerif-Regular.ttf'
MONO='/usr/share/fonts/noto/NotoSansMono-Regular.ttf'
TEXT='The quick brown fox jumps over the lazy dog.\nPlease keep the original words and punctuation.\nLocal screenshots stay on this computer.'
PARA='Good software should make ordinary work easier.\nKeep each line in the order shown on the screen.\n\nA new paragraph starts after this blank line.\nNumbers: 1360, 95%, 16 GB, and 2026.'
CODE='def greet(name):\n    if name:\n        print("Hello, " + name)\n    else:\n        return None\n\nresult = greet("Alex")'
CASES=[
 ('light-sans-18',SANS,18,'#ffffff','#18202a',TEXT,9),
 ('dark-sans-16',SANS,16,'#181a20','#e7e9ee',TEXT,9),
 ('small-light-10',SANS,10,'#ffffff','#15171a',TEXT,6),
 ('small-dark-11',SANS,11,'#202124','#e8eaed',TEXT,6),
 ('serif-paragraph-17',SERIF,17,'#fffaf1','#252422',PARA,9),
 ('sans-paragraph-14',SANS,14,'#ffffff','#333333',PARA,8),
 ('mono-code-15',MONO,15,'#ffffff','#202020',CODE,8),
 ('dark-code-14',MONO,14,'#1e1e1e','#d4d4d4',CODE,8),
 ('small-code-11',MONO,11,'#202124','#e8eaed',CODE,7),
 ('low-contrast-14',SANS,14,'#ffffff','#777777',TEXT,8),
 ('single-line-13',SANS,13,'#ffffff','#222222','Settings > Notifications: show sender and message',6),
 ('mono-paragraph-13',MONO,13,'#f5f5f5','#282828',PARA,8),
]

def distance(a,b):
    previous=list(range(len(b)+1))
    for i,ac in enumerate(a,1):
        current=[i]
        for j,bc in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(ac!=bc)))
        previous=current
    return previous[-1]


def fixtures():
    target=HERE/'samples';target.mkdir(exist_ok=True)
    manifest=[]
    for name,fontpath,size,bg,fg,text,gap in CASES:
        font=ImageFont.truetype(fontpath,size);lines=text.splitlines();lineheight=size+gap
        width=max(200,int(max(font.getlength(line) for line in lines))+48);height=40+lineheight*len(lines)
        image=Image.new('RGB',(width,height),bg);draw=ImageDraw.Draw(image)
        for i,line in enumerate(lines):draw.text((24,18+i*lineheight),line,font=font,fill=fg)
        image.save(target/(name+'.png'));(target/(name+'.txt')).write_text(text+'\n')
        manifest.append({'name':name,'width':width,'height':height,'font':Path(fontpath).name,'size':size})
    for name,font in [('native-light-14','Google Sans Flex'),('native-dark-code-14','JetBrains Mono NF')]:
        path=target/(name+'.png')
        if path.exists():
            with Image.open(path) as image:manifest.append({'name':name,'width':image.width,'height':image.height,'font':font,'size':14})
    return manifest


def run(repeats=3):
    manifest=fixtures();results=[]
    with tempfile.TemporaryDirectory(prefix='ocr-benchmark-') as directory:
        root=Path(directory);binary=root/'bin';binary.mkdir();output=root/'output.txt'
        for name,body in [('wl-copy','cat > "$OCR_BENCH_OUTPUT"'),('notify-send','exit 0')]:
            p=binary/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
        env=os.environ.copy();env['PATH']=str(binary)+':'+env['PATH'];env['OCR_BENCH_OUTPUT']=str(output)
        for case in manifest:
            samples={}
            for backend in ['tesseract','rapidocr']:
                times=[];rss=[];text=''
                for attempt in range(repeats):
                    source=root/"capture with ' quotes.png";shutil.copyfile(HERE/'samples'/(case['name']+'.png'),source)
                    output.unlink(missing_ok=True);mem=root/'rss.txt'
                    if backend=='rapidocr':command=[str(HERE/'screen-ocr'),'--image',str(source),'--crop','0','0',str(case['width']),str(case['height']),'--delete-input']
                    else:
                        q=shlex.quote(str(source));command=['bash','-c',f'magick {q} -crop {case["width"]}x{case["height"]}+0+0 +repage {q} && tesseract {q} stdout -l eng+osd | wl-copy && rm {q}']
                    measurement="import os,subprocess,sys,time,json;from pathlib import Path;t=time.perf_counter();p=subprocess.Popen(json.loads(sys.argv[2]),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);_,status,r=os.wait4(p.pid,0);Path(sys.argv[1]).write_text(json.dumps({'elapsed':time.perf_counter()-t,'rss':r.ru_maxrss}));sys.exit(os.waitstatus_to_exitcode(status))"
                    subprocess.run([sys.executable,'-c',measurement,str(mem),json.dumps(command)],env=env,capture_output=True,check=True,timeout=30)
                    metrics=json.loads(mem.read_text())
                    times.append(metrics['elapsed']);rss.append(metrics['rss']);text=output.read_text();assert not source.exists()
                reference=(HERE/'samples'/(case['name']+'.txt')).read_text()
                norm=lambda value:re.sub(r'\s+','',value)
                samples[backend]={'median_seconds':statistics.median(times),'runs_seconds':times,'max_rss_kib':max(rss),'character_errors':distance(norm(reference),norm(text)),'characters':len(norm(reference)),'cer':distance(norm(reference),norm(text))/len(norm(reference)),'line_count':len(text.rstrip('\n').splitlines()),'blank_lines':sum(not line.strip() for line in text.rstrip('\n').splitlines()),'indentation':[len(line)-len(line.lstrip(' ')) for line in text.splitlines() if line.strip()],'text':text}
            results.append({'sample':case,**samples})
            print(case['name'], 'Tess',round(samples['tesseract']['median_seconds'],3),'Rapid',round(samples['rapidocr']['median_seconds'],3),'CER',round(samples['tesseract']['cer'],3),round(samples['rapidocr']['cer'],3),flush=True)
    (HERE/'benchmark-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Results:',HERE/'benchmark-results.json')

if __name__=='__main__':run()
