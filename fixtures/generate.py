#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""From-first-principles deterministic fixtures; no corpus input."""
import hashlib,json,sys
from pathlib import Path
def generate():
    rows=[]
    for source,operations in [('Source A',['Yard-1','Yard-2','Yard-3']),
                              ('Source B',['Dispatch-1','Dispatch-2'])]:
        for operation in operations:
            for round in range(1,4):
                key='synthetic-'+str(len(rows)+1).zfill(4)
                body={'jobKey':key,'operation':operation,'samples':[round,round+1]} if source=='Source A' else {
                    'plan':{'key':key,'operation':operation},'samples':[round,round+1]}
                rows.append(dict(source=source,operation=operation,round=round,payload=body))
    return dict(schema='tiis-synthetic-fixtures/v1',origin='NEW_FROM_FIRST_PRINCIPLES',
      seed='fixed-enumeration-v1',historical_payload_identity=False,rows=rows)
if __name__=='__main__':
    raw=(json.dumps(generate(),ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    target=Path(sys.argv[1])
    with target.open('xb') as stream:stream.write(raw)
    print(json.dumps(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())))
