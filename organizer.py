"""Metadata-only library backup and bulk organization. Called under server LOCK."""
import copy
import json
import os
import secrets
import time


def export(app):
    _, _, edits = app.category_data()
    ids = set(app.ASSETS)
    state = copy.deepcopy(app.STATE)
    state['favorites'] = [x for x in state['favorites'] if x in ids]
    state['collections'] = [{**c, 'ids': [x for x in c['ids'] if x in ids]} for c in state['collections']]
    state['recent'] = [x for x in state['recent'] if (x if isinstance(x, str) else x.get('id')) in ids]
    return {'format': 'surface-studio-organization', 'version': 1, 'created': time.time(),
            'root': app.INDEX['root'], 'materials': {k: a['folder'] for k, a in app.ASSETS.items()},
            'state': state, 'categories': copy.deepcopy(edits)}


def snapshot(app, label):
    folder = app.DATA/'organization-backups'
    folder.mkdir(exist_ok=True)
    path = folder/(time.strftime('%Y%m%d-%H%M%S')+'-'+label+'-'+secrets.token_hex(3)+'.json')
    app.save_json(path, export(app))
    return str(path)


def validate(data):
    def require(condition):
        if not condition: raise ValueError('备份格式无效或版本不支持')
    def strings(items):
        return isinstance(items, list) and all(isinstance(x, str) for x in items)
    def labels(obj):
        return isinstance(obj, dict) and all(isinstance(k,str) and isinstance(v,str) and 0<len(v.strip())<=40 and not any(ord(c)<32 for c in v) for k,v in obj.items())
    require(isinstance(data, dict) and data.get('format')=='surface-studio-organization' and data.get('version')==1)
    materials=data.get('materials');state=data.get('state');cats=data.get('categories')
    require(isinstance(materials,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in materials.items()))
    require(isinstance(state,dict) and strings(state.get('favorites')) and isinstance(state.get('collections'),list) and isinstance(state.get('recent'),list))
    require(all(isinstance(c,dict) and isinstance(c.get('id'),str) and isinstance(c.get('name'),str) and 0<len(c['name'].strip())<=40 and strings(c.get('ids')) for c in state['collections']))
    require(len({c['id'] for c in state['collections']})==len(state['collections']))
    require(all(isinstance(x,str) or isinstance(x,dict) and isinstance(x.get('id'),str) for x in state['recent']))
    require(isinstance(cats,dict) and labels(cats.get('custom')) and labels(cats.get('names',{})) and isinstance(cats.get('assignments'),dict))
    require(all(isinstance(k,str) and isinstance(v,str) for k,v in cats['assignments'].items()))
    return data


def restore_plan(app, raw):
    data=validate(raw)
    current={a['folder']: k for k,a in app.ASSETS.items()}
    mapping={k:current[folder] for k,folder in data['materials'].items() if folder in current}
    allcats,key,edits=app.category_data();edits=copy.deepcopy(edits);state=copy.deepcopy(app.STATE)
    source=data['categories'];catalog={**app.CATEGORIES,**edits['custom'],**edits.get('names',{})}
    catmap={k:k for k in app.CATEGORIES}
    for k,name in source['custom'].items():
        if k in app.CATEGORIES: raise ValueError('自定义分类标识无效')
        display=source.get('names',{}).get(k,name)
        same=next((cid for cid,label in catalog.items() if label.casefold()==display.casefold()),None)
        target=same or (k if k not in catalog else 'custom-'+secrets.token_hex(8))
        catmap[k]=target
        if target not in catalog: edits['custom'][target]=display;catalog[target]=display
    for k,name in source.get('names',{}).items():
        if k not in catmap: raise ValueError('备份引用了不存在的分类')
        target=catmap[k]
        if target in app.CATEGORIES and target not in edits.get('names',{}) and name.casefold() not in {v.casefold() for cid,v in catalog.items() if cid!=target}:
            edits.setdefault('names',{})[target]=name;catalog[target]=name
    conflicts=0
    for asset,cat in source['assignments'].items():
        if cat not in catmap: raise ValueError('备份引用了不存在的分类')
        if asset in mapping:
            target=mapping[asset]
            if target in edits['assignments']: conflicts+=edits['assignments'][target]!=catmap[cat]
            else: edits['assignments'][target]=catmap[cat]
    def mapped(items): return list(dict.fromkeys(mapping[x] for x in items if x in mapping))
    state['favorites']=list(dict.fromkeys(state['favorites']+mapped(data['state']['favorites'])))
    for c in data['state']['collections']:
        existing=next((x for x in state['collections'] if x['id']==c['id'] and x['name']==c['name']),None)
        if existing: existing['ids']=list(dict.fromkeys(existing['ids']+mapped(c['ids'])))
        else:
            cid=c['id'] if not any(x['id']==c['id'] for x in state['collections']) else secrets.token_hex(16)
            state['collections'].append({'id':cid,'name':c['name'],'ids':mapped(c['ids'])})
    recent=[x if isinstance(x,str) else x['id'] for x in state['recent']]
    for x in data['state']['recent']:
        old=x if isinstance(x,str) else x['id'];target=mapping.get(old)
        if target and target not in recent: state['recent'].append(target);recent.append(target)
    allcats[key]=edits
    summary={'matched':len(mapping),'missing':len(data['materials'])-len(mapping),'conflicts':conflicts,
             'favorites':len(data['state']['favorites']), 'collections':len(data['state']['collections'])}
    return state,allcats,summary


def commit(app,state,categories):
    # A durable journal recovers both metadata files together after an interruption.
    journal=app.DATA/'organization-pending.json'
    app.save_json(journal, {'state':state,'categories':categories})
    app.save_json(app.DATA/'categories.json',categories)
    app.save_json(app.DATA/'state.json',state)
    app.STATE.clear();app.STATE.update(state)
    journal.unlink()


def recover(app):
    journal=app.DATA/'organization-pending.json'
    if journal.exists():
        pending=app.read_json(journal,None)
        if not isinstance(pending,dict) or not isinstance(pending.get('state'),dict) or not isinstance(pending.get('categories'),dict):
            raise ValueError('整理记录恢复日志损坏，请保留 data 并联系支持')
        commit(app,pending['state'],pending['categories'])


def handle(app, body):
    if not isinstance(body,dict): raise ValueError('无效操作')
    recover(app)
    if app.SCANNING: raise ValueError('正在扫描，请完成后再整理或备份')
    action=body.get('action')
    if action=='export': return {'ok':True,'path':snapshot(app,'backup')}
    if action=='open-backups':
        folder=app.DATA/'organization-backups';folder.mkdir(exist_ok=True);os.startfile(str(folder));return {'ok':True}
    if action in ('preview','restore'):
        state,cats,summary=restore_plan(app,body.get('backup'))
        if action=='preview': return summary
        backup=snapshot(app,'before-restore');commit(app,state,cats)
        return {'ok':True,**summary,'path':backup}
    ids=body.get('ids')
    if not isinstance(ids,list) or not ids or not all(isinstance(x,str) and x in app.ASSETS for x in ids): raise ValueError('请选择仍在素材库中的材质')
    ids=list(dict.fromkeys(ids));state=copy.deepcopy(app.STATE);cats,key,edits=app.category_data()
    if action=='category':
        target=body.get('category')
        if target is not None and (not isinstance(target,str) or target not in {**app.CATEGORIES,**edits['custom']}):raise ValueError('分类不存在')
        for ident in ids:
            if target is None:edits['assignments'].pop(ident,None)
            else:edits['assignments'][ident]=target
        cats[key]=edits
    elif action=='favorite':state['favorites']=list(dict.fromkeys(state['favorites']+ids))
    elif action=='unfavorite':state['favorites']=[x for x in state['favorites'] if x not in ids]
    elif action=='collection':
        target=next((c for c in state['collections'] if c['id']==body.get('collection')),None)
        if not target:raise ValueError('集合不存在，请先新建集合')
        target['ids']=list(dict.fromkeys(target['ids']+ids))
    else:raise ValueError('无效批量操作')
    backup=snapshot(app,'before-bulk');commit(app,state,cats)
    return {'ok':True,'count':len(ids),'path':backup}
