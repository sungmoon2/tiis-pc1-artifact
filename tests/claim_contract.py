#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""Named contracts from declared synthetic mechanisms; not latency/height fitting."""
import json,sys
from pathlib import Path
from compare import compare,load
def expected():
    c1={}
    for op in ['Yard-1','Yard-2','Yard-3','Dispatch-1','Dispatch-2']:
        for n in range(1,4):c1[f'C1.valid.{op}.{n}']={'status':'COMMITTED'}
    for field in ['A.key','A.operation','B.key','B.operation']:
        for n in range(1,4):c1[f'C1.omission.{field}.{n}']={'dbWrites':0,'ledgerWrites':0}
    for name,source,reason in [('generic-a','Source A','writer attribute'),('wrong-a','Source A','writer enrollment'),
      ('admin-a','Source A','client OU'),('writer-b','Source A','source MSP'),('writer-a','Source B','source MSP')]:
        c1[f'C1.denied.{name}.{source}']={'ledgerRecordPresent':False,'expectedDenial':reason}
    for name in ['writer-a','writer-b']:c1['C1.direct-allowed.'+name]={'payloadRowExpected':False}
    c2={'C2.INT01.correctness-repeat':{'repeats':30,'scope':'VERIFIED','payloadProof':'VERIFIED','latencyMeasurement':False}}
    for kind in ['raw','coordinated-hash','missing-ref','coordinated-metadata']:
        for n in range(1,4):c2[f'C2.{kind}.{n}']={
          'scope':'MISMATCH' if kind in ['coordinated-hash','coordinated-metadata'] else 'VERIFIED',
          'payloadProof':'MISMATCH','rawWithheld':True}
    c2['C2.peer-unavailable']={'scope':'UNAVAILABLE','payloadProof':'UNAVAILABLE','raw':None,'peer':None}
    c3={f'C3.http.F{n:02}':{'status':status,'transport':'HTTP','protectedLeakage':0}
      for n,status in enumerate([401,401,403,403,403,200,200,200],1)}
    c3['C3.http.F09']={'status':200,'raw':False}
    c4names=['C4.full-sync','C4.multi-gap-pagination','C4.uncertain-classification','C4.validation-metadata']
    for kind,count in [('gap',10),('retry-replay',2),('instance-recreation',10),('finalize-failure',10)]:
        c4names += [f'C4.{kind}.{n}' for n in range(count)]
    c4={name:{'assertion_status':'PASS'} for name in c4names}
    regressions={
      'C3_REGRESSIONS':{
        'C3.http.audit-failure':{'raw':503,'integrity':503,'protectedLeakage':0,'injection':'APPLICATION_NOT_PHYSICAL_DB_OUTAGE'},
        'C3.http.revocation':{'revoked':401,'otherSession':200}},
      'C4_PROCESS_REGRESSION':{
        'C4.separate-process-SIGKILL':{'signal':'SIGKILL','projectionUnchanged':True,
         'checkpointUnchanged':True,'downtimeWrites':0,'includedInCounted36':False}},
      'C1_HTTP_TRANSPORT':{
        'C1.http.authentication-side-effects':{'status':401,'dbWrites':0},
        'C1.http.valid-submit':{'status':200,'ledger':'COMMITTED'}}}
    return {**{'C1':c1,'C2':c2,'C3':c3,'C4':c4},**regressions}
def index(raw):
    found={}
    for case in raw['cases']:
        if case['id'] in found:raise ValueError('duplicate raw case')
        if case['status']!='PASS':raise ValueError('raw case did not pass')
        found[case['id']]=case
    return found
def verify_projection(snapshot):
    terminal=snapshot['terminal'];height=terminal['height']
    assert height>0 and terminal['latest']==height-1 and terminal['redis']==str(height-1)
    assert [int(row['number']) for row in snapshot['blocks']]==list(range(height))
    txs={row['tx_id']:row for row in snapshot['transactions']}
    assert len(txs)==len(snapshot['transactions'])
    assert all(0<=int(row['block_number'])<height for row in txs.values())
    ledger={row['recordId']:row for row in snapshot['ledger']}
    projected={row['record_id']:row for row in snapshot['index']}
    assert len(ledger)==len(snapshot['ledger']) and len(projected)==len(snapshot['index'])
    assert set(ledger)==set(projected)
    for record_id,row in projected.items():
        assert row['envelope']==ledger[record_id] and txs[row['tx_id']]['valid'] is True
        assert row['envelope']['transactionId']==row['tx_id']
    states={row['record_id']:row for row in snapshot['payloadStates']}
    missing=set(projected)-set(states)
    assert missing==set(terminal['ledgerOnlyRecords'])
    unknown=[r for r in states.values() if r['status']=='UNKNOWN']
    assert len(unknown)==10 and all(r['record_id'] not in ledger for r in unknown)
    assert all(r['status'] in ['UNKNOWN','COMMITTED'] for r in states.values())
    assert all(r['record_id'] in ledger for r in states.values() if r['status']=='COMMITTED')
    assert sum(not r['valid'] for r in txs.values())==1
    return {'status':'PASS','height':height,'contiguousBlocks':height,'ledgerRecords':len(ledger),
      'knownUnsubmitted':len(unknown),'declaredLedgerOnly':len(missing),'invalidTransactions':1,
      'scope':'NEW_EXPLICIT_POPULATIONS_NOT_HISTORICAL_UNDEFINED_TERMINAL_FIELDS'}
def collect(runtime,output):
    runtime=Path(runtime);output=Path(output);output.mkdir(exist_ok=False)
    service=load(runtime/'DEVELOPMENT_CASES.json');http=load(runtime/'HTTP_CASES.json')
    assert service['status']=='PASS_WITH_DECLARED_SCOPE_LIMITS' and http['status']=='PASS'
    assert 'teardownError' not in http
    service_cases=index(service);http_cases=index(http);spec=expected()
    frozen=Path(__file__).resolve().parent/'expected'
    assert {p.stem for p in frozen.glob('*.json')}==set(spec)
    for claim,cases in spec.items():assert load(frozen/(claim+'.json'))=={'claim':claim,'cases':cases}
    expected_service=set(spec['C1'])|set(spec['C2'])|set(spec['C4'])|{
      f'C3.service.F{n:02}' for n in range(1,10)}|{
      'C3.service.audit-write-failure','C3.service.revocation'}
    assert set(service_cases)==expected_service
    expected_http=set(spec['C3'])|set(spec['C3_REGRESSIONS'])|set(spec['C4_PROCESS_REGRESSION'])|set(spec['C1_HTTP_TRANSPORT'])
    assert set(http_cases)==expected_http
    assert len(service_cases)==95 and len(http_cases)==14
    projection=verify_projection(load(runtime/'PROJECTION_SNAPSHOT.json'))
    (output/'projection.json').write_text(json.dumps(projection,indent=2))
    final_projection=verify_projection(load(runtime/'FINAL_PROJECTION_SNAPSHOT.json'))
    (output/'final-projection.json').write_text(json.dumps(final_projection,indent=2))
    results={}
    for claim,wanted in spec.items():
        actual=[]
        for name,fields in wanted.items():
            case=(service_cases if claim in ['C1','C2','C4'] else http_cases)[name]
            if claim=='C4':
                observed={'assertion_status':case['status']}
            else:
                observed={field:case['observed'][field] for field in fields}
            actual.append({'id':name,'observed':observed})
        document={'claim':claim,'provenance':'NEW_CLEAN_AUTHOR_EXECUTION','cases':actual}
        comparison=compare({'claim':claim,'cases':wanted},document)
        (output/(claim+'.actual.json')).write_text(json.dumps(document,indent=2))
        (output/(claim+'.compare.json')).write_text(json.dumps(comparison,indent=2))
        results[claim]=comparison
    (output/'RESULT.json').write_text(json.dumps(results,indent=2))
    return results
if __name__=='__main__':
    if sys.argv[1]=='expected':
        out=Path(sys.argv[2]);out.mkdir(exist_ok=False)
        for claim,cases in expected().items():
            (out/(claim+'.json')).write_text(json.dumps({'claim':claim,'cases':cases},indent=2))
    else: print(json.dumps(collect(sys.argv[1],sys.argv[2]),indent=2))
