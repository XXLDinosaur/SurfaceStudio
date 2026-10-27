"""Signed GitHub release updates. All checks/downloads run off the UI thread."""
import base64,hashlib,json,re,threading,time,uuid
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlparse,quote
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from update_key import PUBLIC_KEY

VERSION='1.5.0'
REPO='XXLDinosaur/SurfaceStudio'
LATEST='https://api.github.com/repos/'+REPO+'/releases/latest'
SETUP='SurfaceStudio-Setup.exe'
MAX_SIZE=512*1024*1024

def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'v?\d+\.\d+\.\d+',value):raise ValueError('仅支持正式版本号，例如 v1.5.0')
    return tuple(int(x) for x in value.lstrip('v').split('.'))

def allowed(url):
    p=urlparse(url)
    return p.scheme=='https' and not p.username and not p.password and p.port in (None,443) and p.hostname in {'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not allowed(newurl):raise ValueError('更新下载地址无效')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def open_remote(url):
    if not allowed(url):raise ValueError('更新地址无效')
    return build_opener(SafeRedirect()).open(Request(url,headers={'User-Agent':'SurfaceStudio/'+VERSION,'Accept':'application/vnd.github+json'}),timeout=20)

def fetch(url,limit):
    with open_remote(url) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('更新信息过大')
    return data

def verify_manifest(raw,signature,release,public_key=PUBLIC_KEY):
    Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key)).verify(signature,raw)
    data=json.loads(raw)
    if not isinstance(data,dict) or data.get('format')!='surface-studio-update-v1':raise ValueError('更新信息格式无效')
    if version(data.get('version'))!=version(release.get('tag_name')):raise ValueError('更新版本不匹配')
    if data.get('asset')!=SETUP or not isinstance(data.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',data['sha256']):raise ValueError('安装包校验信息无效')
    if type(data.get('size')) is not int or not 0<data['size']<=MAX_SIZE:raise ValueError('安装包大小无效')
    if release.get('draft') or release.get('prerelease'):raise ValueError('忽略非正式版本')
    return data

def download_verified(url,destination,manifest,progress=lambda n:None,opener=open_remote):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(uuid.uuid4().hex+'.partial');count=0;digest=hashlib.sha256()
    try:
        with opener(url) as response,temporary.open('wb') as stream:
            while True:
                block=response.read(256*1024)
                if not block:break
                count+=len(block)
                if count>manifest['size']:raise ValueError('安装包大小不符')
                digest.update(block);stream.write(block);progress(count)
        if count!=manifest['size'] or digest.hexdigest()!=manifest['sha256']:raise ValueError('安装包校验失败，已取消更新')
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    return destination

class Updater:
    def __init__(self,root):
        self.root=Path(root);self.folder=self.root/'data'/'updates';self.folder.mkdir(parents=True,exist_ok=True)
        self.settings=self.folder/'settings.json'
        try:self.auto=json.loads(self.settings.read_text(encoding='utf-8')).get('autoCheck',True) is True
        except (OSError,ValueError,AttributeError):self.auto=True
        self.lock=threading.Lock();self.manifest=None;self.package=None;self.release=None
        self.state={'current':VERSION,'phase':'idle','message':'尚未检查更新','autoCheck':self.auto,'progress':0}
    def status(self):return dict(self.state)
    def set_auto(self,value):
        if type(value) is not bool:raise ValueError('更新设置无效')
        self.auto=value;self.state['autoCheck']=value
        temp=self.settings.with_suffix('.tmp');temp.write_text(json.dumps({'autoCheck':value}),encoding='utf-8');temp.replace(self.settings)
        return self.status()
    def start(self,operation):
        if not self.lock.acquire(False):return self.status()
        def worker():
            try:operation()
            except Exception as exc:self.state.update(phase='error',message='更新未完成：'+(str(exc) or type(exc).__name__))
            finally:self.lock.release()
        threading.Thread(target=worker,daemon=True).start();return self.status()
    def check(self):
        if self.lock.locked():return self.status()
        self.state.update(phase='checking',message='正在检查 GitHub 正式版本…',progress=0)
        return self.start(self._check)
    def _check(self):
        self.manifest=None;self.package=None
        release=json.loads(fetch(LATEST,1024*1024));self.release=release
        if release.get('draft') or release.get('prerelease'):raise ValueError('最新条目不是正式版本')
        latest=release['tag_name'];self.state.update(latest=latest,notes=str(release.get('body') or '此版本未提供更新说明')[:20000],checkedAt=time.time())
        if version(latest)<=version(VERSION):
            self.state.update(phase='current',message='当前已是最新版本（或本地开发版更新）');return
        assets={a['name']:a for a in release.get('assets',[]) if a.get('state')=='uploaded'}
        base='https://github.com/'+REPO+'/releases/download/'+quote(latest,safe='')+'/'
        for name in ['surface-update.json','surface-update.sig',SETUP]:
            if name not in assets:raise ValueError('新版尚未上传完整签名更新包，请稍后重试')
            if assets[name].get('browser_download_url')!=base+name:raise ValueError('更新资产来源不匹配')
        raw=fetch(base+'surface-update.json',65536);sig=fetch(base+'surface-update.sig',128)
        self.manifest=verify_manifest(raw,sig,release)
        self.url=base+SETUP
        self.state.update(phase='available',message='发现新版本 '+latest)
    def download(self):
        if not self.manifest:return {'error':'请先检查更新'}
        if self.lock.locked():return self.status()
        self.state.update(phase='downloading',message='正在下载并校验安装包…',progress=0)
        return self.start(self._download)
    def _download(self):
        m=self.manifest
        dest=self.folder/('.'.join(map(str,version(m['version']))))/SETUP
        self.package=download_verified(self.url,dest,m,lambda n:self.state.update(progress=round(n/m['size']*100)))
        self.state.update(phase='ready',message='下载及签名校验完成，可以安装',progress=100)
    def verified_package(self):
        if not self.package or not self.manifest:raise ValueError('请先下载更新')
        path=self.package
        if path.is_symlink() or path.stat().st_size!=self.manifest['size'] or hashlib.sha256(path.read_bytes()).hexdigest()!=self.manifest['sha256']:raise ValueError('安装包已变化，请重新下载')
        return path
