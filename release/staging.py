# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
import csv,hashlib,json,re,shutil
from pathlib import Path,PurePosixPath
from bundle import unique_json
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check_private_inventory(value):
    if isinstance(value,list):
        for v in value:check_private_inventory(v)
    if isinstance(value,dict):
        if value.get('argv')==['docker','volume','ls','-q']:
            if value.get('stdout')!='<PRIVATE_RESOURCE_INVENTORY_REDACTED>' or not re.fullmatch('[a-f0-9]{64}',value.get('stdout_sha256','')):
                raise ValueError('unredacted global host resource inventory')
        for v in value.values():check_private_inventory(v)
def verify_export(directory):
    directory=Path(directory)
    files={p.relative_to(directory).as_posix():p for p in directory.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in directory.rglob('*')):raise ValueError('export symlink')
    required={'RUN_RESULT.json','FINALIZATION.json','MANIFEST.tsv','SHA256SUMS.txt','EXPORT_PROVENANCE.json'}
    if not required<=set(files):raise ValueError('required evidence absent')
    listed={}
    for line in files['SHA256SUMS.txt'].read_text().splitlines():
        digest,name=line.split('  ',1);path=PurePosixPath(name)
        if not re.fullmatch('[a-f0-9]{64}',digest) or path.is_absolute() or '..' in path.parts or name in listed:
            raise ValueError('invalid checksum entry')
        listed[name]=digest
    if set(listed)!=set(files)-{'SHA256SUMS.txt'}:raise ValueError('checksum set mismatch')
    for name,digest in listed.items():
        if sha(files[name].read_bytes())!=digest:raise ValueError('evidence checksum mismatch')
    with files['MANIFEST.tsv'].open() as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
    names=[r['path'] for r in rows]
    if len(names)!=len(set(names)) or set(names)!=set(files)-{'SHA256SUMS.txt','MANIFEST.tsv'}:
        raise ValueError('manifest set mismatch')
    for row in rows:
        raw=files[row['path']].read_bytes()
        if len(raw)!=int(row['bytes']) or sha(raw)!=row['sha256']:raise ValueError('manifest bytes/hash')
    receipt=unique_json((directory.parent/'READBACK.json').read_bytes())
    if receipt['status']!='PASS' or len(receipt['files'])!=len(files):raise ValueError('readback absent/incomplete')
    if {r['path'] for r in receipt['files']}!=set(files):raise ValueError('readback set mismatch')
    for row in receipt['files']:
        if row['path'] not in files:raise ValueError('readback unknown path')
        raw=files[row['path']].read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('readback mismatch')
    for name,path in files.items():
        text=path.read_bytes().decode('utf-8')
        if name.endswith('.json'):check_private_inventory(unique_json(text))
        if re.search(r'-----BEGIN (?:EC |RSA )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|/(?:home|Users)/[^/\s]+/',text):
            raise ValueError('unredacted secret/private path')
        if re.search(r'(?:PASSWORD|password)["\x27]?\s*[:=]\s*["\x27]?[A-Za-z0-9]{24,}',text):
            raise ValueError('unredacted password')
    result=unique_json(files['RUN_RESULT.json'].read_bytes())
    if result['overall'] not in ['PASS','FAIL'] or result['C8']!='C8_PENDING_INDEPENDENT_REPRODUCTION':
        raise ValueError('invalid evidence claim')
    if result['overall']=='PASS':
        if any(result['phases'].get(k)!='PASS' for k in ['setup','start','test','collect','stop','install_cleanup']):
            raise ValueError('false phase PASS')
        for claim,count in [('C1',34),('C2',14),('C3',9),('C4',36)]:
            matches=[p for name,p in files.items() if name.endswith('-'+claim+'.compare.json')]
            if len(matches)!=1:raise ValueError('claim comparison absent/ambiguous')
            comparison=unique_json(matches[0].read_bytes())
            if comparison!={'claim':claim,'status':'PASS','cases':count,'provenance':'NEW_CLEAN_AUTHOR_EXECUTION'}:
                raise ValueError('claim comparison mismatch')
    return {'status':'PASS','files':len(files),'overall':result['overall']}
def stage(source,destination):
    receipt=verify_export(source)
    destination=Path(destination)
    if destination.exists():raise ValueError('staging destination must be new')
    shutil.copytree(source,destination)
    for p in Path(source).rglob('*'):
        if p.is_file() and p.read_bytes()!=(destination/p.relative_to(source)).read_bytes():
            raise ValueError('staging readback mismatch')
    return receipt
