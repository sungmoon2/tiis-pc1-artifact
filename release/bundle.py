#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""Local deterministic component transport. No Git remote or external write."""
import gzip,hashlib,io,json,re,subprocess,tarfile
from pathlib import Path,PurePosixPath
IDS=['api','web','chaincode','network']
def unique_json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=unique)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git_hash(kind,raw):return hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).digest()
def tree_identity(files):
    root={}
    for name,(data,mode) in files.items():
        parts=name.split('/');node=root
        for part in parts[:-1]:node=node.setdefault(part,{})
        if parts[-1] in node:raise ValueError('duplicate/tree collision')
        node[parts[-1]]=(data,mode)
    def tree(node):
        body=b''
        for name,value in sorted(node.items(),key=lambda kv:(kv[0]+('/' if isinstance(kv[1],dict) else '')).encode()):
            if isinstance(value,dict):mode='40000';digest=tree(value)
            else:
                data,permissions=value;mode='100755' if permissions&0o111 else '100644';digest=git_hash('blob',data)
            body+=mode.encode()+b' '+name.encode()+b'\0'+digest
        return git_hash('tree',body)
    return tree(root).hex()
def members(raw,compression=''):
    entries={};total=0
    if compression=='gzip':raw=gzip.decompress(raw)
    if len(raw)>64*1024**2:raise ValueError('archive expanded size limit')
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tar:
        for entry in tar.getmembers():
            name=entry.name
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or str(p)!=name.rstrip('/'):
                raise ValueError('unsafe archive path')
            if entry.isdir():continue
            if not entry.isfile() or name in entries:raise ValueError('nonregular/duplicate archive entry')
            total+=entry.size
            if total>64*1024**2:raise ValueError('archive size limit')
            entries[name]=(tar.extractfile(entry).read(),entry.mode)
    return entries
def tar_bytes(files):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for name,raw in sorted(files.items()):
            info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644
            info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
            tar.addfile(info,io.BytesIO(raw))
    return stream.getvalue()
def archive_repository(repo):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    if git('status','--porcelain=v1').strip():raise ValueError('dirty component')
    commit=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
    raw=gzip.compress(git('archive','--format=tar',commit),mtime=0)
    files=members(raw,'gzip')
    if tree_identity(files)!=tree:raise ValueError('archive Git tree mismatch')
    return raw,dict(commit=commit,tree=tree,archive_sha256=sha(raw),archive_bytes=len(raw),
      files={name:dict(bytes=len(data),sha256=sha(data),executable=bool(mode&0o111))
             for name,(data,mode) in sorted(files.items())})
def pack(base,output):
    base=Path(base);output=Path(output);output.mkdir(exist_ok=False)
    archives={};components=[]
    for name in IDS:
        raw,record=archive_repository(base/('tiis-pc1-'+name))
        filename='tiis-pc1-'+name+'.tar.gz'
        archives[filename]=raw;components.append(dict(id=name,archive=filename,**record))
    manifest=json.dumps(dict(schema='tiis-rc-inputs/v1',components=components),sort_keys=True,indent=2).encode()+b'\n'
    archives['MANIFEST.json']=manifest
    archives['SHA256SUMS.txt']=''.join(sha(raw)+'  '+name+'\n' for name,raw in sorted(archives.items())).encode()
    uncompressed=tar_bytes(archives)
    def compress():
        return subprocess.check_output(['zstd','-q','-19','-T1','--stdout'],input=uncompressed)
    first,second=compress(),compress()
    if first!=second:raise ValueError('bundle nondeterministic')
    digest=sha(first);filename='tiis-pc1-rc-inputs-'+digest+'.tar.zst'
    (output/filename).write_bytes(first)
    lock=dict(schema='tiis-components-lock/v1',components=components,
              bundle=dict(filename=filename,sha256=digest,bytes=len(first)))
    (output/'components.lock.json').write_text(json.dumps(lock,sort_keys=True,indent=2)+'\n')
    return lock
def verify(bundle,lock,output=None):
    raw=Path(bundle).read_bytes()
    if sha(raw)!=lock['bundle']['sha256'] or len(raw)!=lock['bundle']['bytes']:
        raise ValueError('outer bundle identity mismatch')
    uncompressed=subprocess.check_output(['zstd','-q','--decompress','--stdout'],input=raw)
    entries=members(uncompressed)
    expected={r['archive'] for r in lock['components']}|{'MANIFEST.json','SHA256SUMS.txt'}
    if set(entries)!=expected or sorted(r['id'] for r in lock['components'])!=sorted(IDS):
        raise ValueError('bundle entry/component set mismatch')
    manifest=unique_json(entries['MANIFEST.json'][0])
    if manifest!={'schema':'tiis-rc-inputs/v1','components':lock['components']}:
        raise ValueError('nested manifest differs from lock')
    checksums=''.join(sha(data)+'  '+name+'\n' for name,(data,_) in sorted(entries.items())
                      if name!='SHA256SUMS.txt').encode()
    if entries['SHA256SUMS.txt'][0]!=checksums:raise ValueError('nested checksum mismatch')
    extracted={}
    for component in lock['components']:
        if not re.fullmatch('[a-f0-9]{40}',component['commit']) or not re.fullmatch('[a-f0-9]{40}',component['tree']):
            raise ValueError('full Git identity required')
        if component['archive']!='tiis-pc1-'+component['id']+'.tar.gz':
            raise ValueError('component archive name mismatch')
        data=entries[component['archive']][0]
        if sha(data)!=component['archive_sha256'] or len(data)!=component['archive_bytes']:
            raise ValueError('component archive mismatch')
        files=members(data,'gzip')
        with tarfile.open(fileobj=io.BytesIO(gzip.decompress(data)),mode='r:') as tar:
            if tar.pax_headers.get('comment')!=component['commit']:raise ValueError('archive commit comment mismatch')
        if tree_identity(files)!=component['tree']:raise ValueError('component tree mismatch')
        inventory={name:dict(bytes=len(raw),sha256=sha(raw),executable=bool(mode&0o111))
                   for name,(raw,mode) in sorted(files.items())}
        if inventory!=component['files']:raise ValueError('component file inventory mismatch')
        extracted[component['id']]=files
    if output is not None:
        output=Path(output);output.mkdir(exist_ok=False)
        for component,files in extracted.items():
            directory=output/('tiis-pc1-'+component);directory.mkdir()
            for name,(data,mode) in files.items():
                target=directory/name;target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:stream.write(data)
                target.chmod(0o755 if mode&0o111 else 0o644)
    return dict(status='PASS',components=len(extracted),bundle_sha256=sha(raw),
      file_count=sum(len(files) for files in extracted.values()))
