"""Loopback binding and installation-local service discovery lifecycle."""
import errno,json,secrets
from pathlib import Path

def bind_server(handler,preferred=47831):
    from http.server import ThreadingHTTPServer
    candidates=list(range(preferred,min(65536,preferred+10))) if preferred else [0]
    if preferred:candidates.append(0)
    for port in candidates:
        try:return ThreadingHTTPServer(('127.0.0.1',port),handler)
        except OSError as exc:
            if exc.errno not in (errno.EADDRINUSE,errno.EACCES,10048,10013):raise
    raise OSError('无法分配本地服务端口')

def publish(data,port,instance):
    path=Path(data)/'service.json';temporary=path.with_name('service-'+secrets.token_hex(6)+'.tmp')
    temporary.write_text(json.dumps({'format':'surface-studio-service-v1','port':port,'instance':instance}),encoding='utf-8')
    temporary.replace(path)

def clear(data,instance):
    path=Path(data)/'service.json'
    try:
        if json.loads(path.read_text(encoding='utf-8')).get('instance')==instance:path.unlink()
    except (OSError,ValueError):pass
