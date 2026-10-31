"""Resolve only the configured SS installation's loopback service."""
import json
from pathlib import Path
from urllib.request import urlopen

def resolve_service(executable):
    path=Path(executable).parent/'data'/'service.json'
    if path.exists():
        record=json.loads(path.read_text(encoding='utf-8'))
        port=record.get('port');instance=record.get('instance')
        if record.get('format')!='surface-studio-service-v1' or type(port) is not int or not 1<=port<=65535 or not isinstance(instance,str) or len(instance)<16:
            raise ValueError('SS 服务记录无效，请重启 SS')
        base='http://127.0.0.1:'+str(port)
        with urlopen(base+'/api/health',timeout=3) as response:health=json.load(response)
        if health.get('app')!='Surface Studio' or health.get('instance')!=instance:
            raise ValueError('SS 服务记录已过期，请重启 SS')
        return base
    # Compatibility with released SS versions that predate discovery records.
    base='http://127.0.0.1:47831'
    with urlopen(base+'/api/health',timeout=3) as response:health=json.load(response)
    if health.get('app')!='Surface Studio':raise ValueError('本地端口不是 SS 服务')
    return base
