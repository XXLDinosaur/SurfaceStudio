"""Sign a release installer. Private keys are never copied into builds/releases."""
import argparse,base64,hashlib,json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from updater import SETUP,verify_manifest,version
from update_key import PUBLIC_KEY

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',required=True);parser.add_argument('--installer',default='dist/SurfaceStudio-Setup.exe');parser.add_argument('--key',default='.release-signing-private/update-ed25519.pem');parser.add_argument('--output',default='dist')
    args=parser.parse_args();version(args.version)
    installer=Path(args.installer);key=serialization.load_pem_private_key(Path(args.key).read_bytes(),password=None)
    public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    if public!=base64.b64decode(PUBLIC_KEY):raise ValueError('签名私钥与客户端公钥不匹配')
    raw=json.dumps({'format':'surface-studio-update-v1','version':args.version.lstrip('v'),'asset':SETUP,'size':installer.stat().st_size,'sha256':hashlib.sha256(installer.read_bytes()).hexdigest()},sort_keys=True,separators=(',',':')).encode()
    signature=key.sign(raw);verify_manifest(raw,signature,{'tag_name':args.version})
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    (output/'surface-update.json').write_bytes(raw);(output/'surface-update.sig').write_bytes(signature)
    print('Signed update manifest written; publish installer plus manifest and signature together')
if __name__=='__main__':main()
