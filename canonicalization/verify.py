#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""Literal known-answer oracle, not a second invocation of the JS canonicalizer."""
import hashlib,json,subprocess,sys
from pathlib import Path
base=Path(sys.argv[1]).resolve()
vectors=[
    ({'2':'two','10':'ten','a':1},'{"10":"ten","2":"two","a":1}'),
    ({'z':[None,{'b':True,'a':False}],'a':[]},'{"a":[],"z":[null,{"a":false,"b":true}]}'),
    ({'text':'합성 😀','b':0},'{"b":0,"text":"합성 😀"}'),
    ({'z':0,'a':1.25},'{"a":1.25,"z":0}')]
receipts=[]
for number,(value,literal) in enumerate(vectors,1):
    expected=literal.encode('utf-8');digest='sha256:'+hashlib.sha256(expected).hexdigest()
    for component in ['api','web','chaincode']:
        module=str(base/('tiis-pc1-'+component)/'src/canonical.js')
        code="const m=require(process.argv[1]);const v=JSON.parse(process.argv[2]);process.stdout.write(JSON.stringify({bytes:Buffer.from(m.canonical(v)).toString('hex'),hash:m.payloadHash(v)}));"
        result=subprocess.run(['node','-e',code,module,json.dumps(value,ensure_ascii=False)],
                              capture_output=True,text=True,timeout=10)
        assert result.returncode==0,result.stderr
        got=json.loads(result.stdout)
        assert bytes.fromhex(got['bytes'])==expected and got['hash']==digest
        receipts.append(dict(vector=number,component=component,bytes=len(expected),sha256=digest,status='PASS'))
print(json.dumps(dict(scope='NEW_LITERAL_KATS',status='PASS',receipts=receipts),indent=2))
