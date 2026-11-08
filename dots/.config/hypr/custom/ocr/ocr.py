#!/usr/bin/env python3
"""On-demand English screenshot OCR. Local models, CPU only, no persistent process."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time

# Bound native thread pools before importing NumPy/OpenCV/ONNX Runtime.
for name,value in {'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}.items():os.environ[name]=value
HERE=Path(__file__).resolve().parent
DATA=Path.home()/'.local/share/rdp-screen-ocr'


def notify(title,message):
    try:subprocess.run(['notify-send','-a','Screen OCR',title,message],timeout=3,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except (OSError,subprocess.SubprocessError):pass


def engine():
    import cv2
    import onnxruntime
    from rapidocr import RapidOCR, EngineType, LangDet, LangRec, ModelType, OCRVersion
    from rapidocr.utils.download_file import DownloadFile
    cv2.setNumThreads(1)
    onnxruntime.disable_telemetry_events()
    manifest=json.loads((HERE/'models.json').read_text())
    for entry in manifest.values():
        path=DATA/'models'/entry['file']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('OCR model missing or damaged. Run the documented OCR setup again.')
    def offline(*args,**kwargs):raise RuntimeError('A dependency attempted a download. Re-run OCR setup; captures run offline.')
    DownloadFile.run=staticmethod(offline)
    return RapidOCR(params={
        'Global.use_cls':False,
        'Global.use_preprocess_img':False,
        'Global.use_vertical_padding':True,
        'Global.return_word_box':False,
        'Global.return_single_char_box':False,
        'Global.log_level':'critical',
        'Global.model_root_dir':str(DATA/'models'),
        'EngineConfig.onnxruntime.intra_op_num_threads':4,
        'EngineConfig.onnxruntime.inter_op_num_threads':1,
        'EngineConfig.onnxruntime.use_cuda':False,
        'EngineConfig.onnxruntime.use_dml':False,
        'EngineConfig.onnxruntime.use_cann':False,
        'EngineConfig.onnxruntime.use_coreml':False,
        'Det.engine_type':EngineType.ONNXRUNTIME,'Det.ocr_version':OCRVersion.PPOCRV5,'Det.model_type':ModelType.MOBILE,'Det.lang_type':LangDet.MULTI,
        'Det.model_path':str(DATA/'models'/manifest['detector']['file']),
        'Det.limit_type':'max','Det.limit_side_len':1600,
        'Det.mean':[0.485,0.456,0.406],'Det.std':[0.229,0.224,0.225],
        'Rec.engine_type':EngineType.ONNXRUNTIME,'Rec.ocr_version':OCRVersion.PPOCRV5,'Rec.model_type':ModelType.MOBILE,'Rec.lang_type':LangRec.EN,
        'Rec.model_path':str(DATA/'models'/manifest['recognizer']['file']),
        'Rec.rec_batch_num':6,
    })


def prepare(image):
    import numpy as np
    import cv2
    array=np.asarray(image.convert('RGB'))
    gray=cv2.cvtColor(array,cv2.COLOR_RGB2GRAY)
    # Complement genuinely dark screenshots; preserve antialiasing and colours.
    dark=float(np.median(gray))<90 and 0.002<float(np.mean(gray>160))<0.45
    if dark:array=255-array
    return np.ascontiguousarray(array[:,:,::-1]),{'inverted_dark':dark}


def ink_edges(array,boxes):
    """Refine box padding for layout only; recognition pixels are never thresholded."""
    import numpy as np
    import cv2
    gray=cv2.cvtColor(array,cv2.COLOR_BGR2GRAY)
    edges=[]
    for box in boxes:
        x0=max(0,int(min(p[0] for p in box)));x1=min(gray.shape[1],int(max(p[0] for p in box))+1)
        y0=max(0,int(min(p[1] for p in box)));y1=min(gray.shape[0],int(max(p[1] for p in box))+1)
        crop=gray[y0:y1,x0:x1]
        if crop.size:
            light,dark=np.percentile(crop,[90,10])
            threshold=light-max(20.0,(light-dark)*0.35)
            columns=np.flatnonzero(np.sum(crop<threshold,axis=0)>=max(1,crop.shape[0]*0.08))
            if len(columns):edges.append((x0+float(columns[0]),x0+float(columns[-1])+1));continue
        edges.append((float(x0),float(x1)))
    return edges


def extract(path,crop=None):
    from PIL import Image
    from layout import reconstruct
    started=time.perf_counter()
    with Image.open(path) as image:
        if image.width*image.height>25_000_000:raise ValueError('Screenshot exceeds the 25-megapixel safety limit. Select a smaller capture.')
        if crop:
            x,y,w,h=crop
            if min(x,y)<0 or min(w,h)<=0 or x+w>image.width or y+h>image.height:raise ValueError('Selected region is outside the screenshot')
            image=image.crop((x,y,x+w,y+h))
        array,preprocessing=prepare(image)
    ocr=engine()
    ready=time.perf_counter()
    result=ocr(array,use_cls=False)
    finished=time.perf_counter()
    boxes=result.boxes.tolist() if result.boxes is not None else []
    texts=list(result.txts or [])
    text=reconstruct(boxes,texts,ink_edges(array,boxes))
    return {'text':text,'boxes':boxes,'texts':texts,'scores':list(result.scores) if result.scores is not None else [],'preprocessing':preprocessing,'setup_seconds':ready-started,'inference_seconds':finished-ready,'total_seconds':time.perf_counter()-started}


def identity(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid():raise ValueError('Capture must be a regular file owned by your user')
    return (info.st_dev,info.st_ino,info.st_mtime_ns,info.st_size)


def clean_input(path,expected):
    try:
        if expected is not None and identity(path)==expected:path.unlink()
    except (OSError,ValueError):pass


def selected_capture():
    region=subprocess.run(['slurp',*shlex.split(os.environ.get('SLURP_ARGS',''))],capture_output=True,text=True)
    if region.returncode or not region.stdout.strip():return None
    directory=tempfile.TemporaryDirectory(prefix='screen-ocr-',dir=os.environ.get('XDG_RUNTIME_DIR'))
    try:
        image=Path(directory.name)/'capture.png'
        subprocess.run(['grim','-g',region.stdout.strip(),str(image)],check=True,capture_output=True,timeout=10)
        return directory,image
    except BaseException:
        directory.cleanup();raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--image',type=Path);source.add_argument('--select',action='store_true')
    parser.add_argument('--crop',nargs=4,type=int,metavar=('X','Y','WIDTH','HEIGHT'))
    parser.add_argument('--delete-input',action='store_true')
    output=parser.add_mutually_exclusive_group();output.add_argument('--stdout',action='store_true');output.add_argument('--json',action='store_true')
    args=parser.parse_args();image=args.image;expected=None;temporary=None
    try:
        if image is not None:expected=identity(image)
        lockdir=Path(os.environ.get('XDG_RUNTIME_DIR',tempfile.gettempdir()))
        with (lockdir/f'rdp-screen-ocr-{os.getuid()}.lock').open('a') as guard:
            try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('Another OCR capture is still running. Try again in a moment.')
            if args.select:
                capture=selected_capture()
                if capture is None:return 0
                temporary,image=capture
            result=extract(image,args.crop)
            if args.json:print(json.dumps(result,ensure_ascii=False));return 0
            if not result['text'].strip():raise RuntimeError('No readable English text found. Clipboard was left unchanged.')
            if args.stdout:sys.stdout.write(result['text']);return 0
            subprocess.run(['wl-copy','--type','text/plain;charset=utf-8'],input=result['text'].encode('utf-8'),check=True,timeout=5)
            notify('Text copied','English text is on the clipboard.')
        return 0
    except Exception as exc:
        if args.stdout or args.json:print(str(exc),file=sys.stderr)
        else:notify('OCR failed',str(exc))
        return 1
    finally:
        if args.delete_input and args.image is not None:clean_input(args.image,expected)
        if temporary is not None:temporary.cleanup()

if __name__=='__main__':
    def interrupted(*_):raise RuntimeError('OCR was interrupted. Clipboard was left unchanged.')
    signal.signal(signal.SIGTERM,interrupted)
    raise SystemExit(main())
