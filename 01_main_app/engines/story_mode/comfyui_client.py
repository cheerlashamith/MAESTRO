import copy,json,random,time,urllib.parse
from pathlib import Path
import requests

def load_workflow(path):
    return json.load(open(path,'r',encoding='utf-8'))
def find_nodes(wf,typ): return [k for k,v in wf.items() if isinstance(v,dict) and v.get('class_type')==typ]
def title(n): return str((n.get('_meta') or {}).get('title','')).lower()
def inject(wf,prompt,neg,width,height,steps,cfg):
    w=copy.deepcopy(wf); clips=find_nodes(w,'CLIPTextEncode'); pos=negid=None
    for nid in clips:
        t=title(w[nid])
        if 'positive' in t or 'pos' in t: pos=nid
        if 'negative' in t or 'neg' in t: negid=nid
    if pos is None and clips: pos=clips[0]
    if negid is None and len(clips)>1: negid=clips[1]
    if not pos: raise RuntimeError('No CLIPTextEncode node')
    w[pos].setdefault('inputs',{})['text']=prompt
    if negid: w[negid].setdefault('inputs',{})['text']=neg
    for nid in find_nodes(w,'KSampler'):
        i=w[nid].setdefault('inputs',{}); i['seed']=random.randint(1,2**63-1)
        if 'steps' in i: i['steps']=int(steps)
        if 'cfg' in i: i['cfg']=float(cfg)
    for cls in ['EmptyLatentImage','EmptySD3LatentImage','EmptyLatentVideo']:
        for nid in find_nodes(w,cls):
            i=w[nid].setdefault('inputs',{})
            if 'width' in i: i['width']=int(width)
            if 'height' in i: i['height']=int(height)
    for nid in find_nodes(w,'SaveImage'):
        w[nid].setdefault('inputs',{})['filename_prefix']='story_mode_scene'
    return w
class ComfyUIClient:
    def __init__(self,base_url='http://127.0.0.1:8188',timeout=300):
        self.base_url=base_url.rstrip('/'); self.timeout=timeout
        self.ensure_running()
    
    def ensure_running(self):
        try:
            self.health()
            return
        except Exception:
            pass
        import os, subprocess, time, sys
        p = str(Path(__file__).resolve().parent.parent.parent)
        if p not in sys.path:
            sys.path.insert(0, p)
        try:
            from backend.core.config import get_config
            cfg = get_config()
            root = cfg.get("paths", {}).get("comfyui_root")
        except Exception:
            root = None
        if not root: raise RuntimeError("ComfyUI is not running and comfyui_root is not configured.")
        root = Path(root)
        bat = root / "run_nvidia_gpu.bat"
        if not bat.exists(): raise RuntimeError(f"run_nvidia_gpu.bat not found at {bat}")
        log_file = open(root / "comfyui_auto.log", "w", encoding="utf-8")
        subprocess.Popen([str(bat)], cwd=str(root), stdout=log_file, stderr=log_file, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        for _ in range(120):
            time.sleep(1)
            try: self.health(); return
            except Exception: pass
        raise RuntimeError("ComfyUI did not start within 120 seconds.")

    def health(self): r=requests.get(f'{self.base_url}/system_stats',timeout=5); r.raise_for_status(); return r.json()
    def queue_prompt(self,wf): r=requests.post(f'{self.base_url}/prompt',json={'prompt':wf},timeout=30); r.raise_for_status(); return r.json()['prompt_id']
    def wait(self,pid):
        st=time.time()
        while time.time()-st<self.timeout:
            r=requests.get(f'{self.base_url}/history/{pid}',timeout=10); r.raise_for_status(); h=r.json()
            if pid in h: return h[pid]
            time.sleep(1.5)
        raise TimeoutError(pid)
    def download(self,h,out):
        for o in h.get('outputs',{}).values():
            imgs=o.get('images') or []
            if imgs:
                im=imgs[0]; q=urllib.parse.urlencode({'filename':im['filename'],'subfolder':im.get('subfolder',''),'type':im.get('type','output')})
                r=requests.get(f'{self.base_url}/view?{q}',timeout=60); r.raise_for_status(); Path(out).parent.mkdir(parents=True,exist_ok=True); open(out,'wb').write(r.content); return out
        raise RuntimeError('No image output')
    def generate_image(self,wf,prompt,negative_prompt,out,width=1080,height=1920,steps=20,cfg=4.0):
        pid=self.queue_prompt(inject(wf,prompt,negative_prompt,width,height,steps,cfg)); return self.download(self.wait(pid),out)
