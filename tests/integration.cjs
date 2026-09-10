// SPDX-FileCopyrightText: 2026 Sungmoon Park
// SPDX-License-Identifier: Apache-2.0
'use strict';
// Development integration harness. This is not a fresh-VM G3/C8 attestation.
const fs=require('node:fs'), assert=require('node:assert/strict');
const {Pool}=require('/work/api/node_modules/pg');
const {createClient}=require('/work/web/node_modules/@redis/client');
const {connectIdentity}=require('/work/api/src/gateway');
const {SubmissionService}=require('/work/api/src/service');
const {adapt}=require('/work/api/src/envelope');
const {canonical,payloadHash}=require('/work/api/src/canonical');
const {IntegrityService}=require('/work/web/src/integrity');
const {SessionAccess}=require('/work/web/src/access');
const {ReadModel}=require('/work/web/src/read-model');
const configurations=JSON.parse(fs.readFileSync('/work/identities.json'));
const connections=Object.fromEntries(Object.entries(configurations).map(([name,c])=>[name,connectIdentity(c)]));
const pool=new Pool({host:'postgres',user:'artifact',database:'artifact',
  password:fs.readFileSync('/work/database-password','utf8'),max:4,connectionTimeoutMillis:5000});
const redis=createClient({url:'redis://redis:6379',socket:{connectTimeout:5000,reconnectStrategy:false}});
redis.on('error',error=>console.error('redis error:',error.message));
const evidence={scope:'G2_DEVELOPMENT_SERVICE_INTEGRATION_NOT_G3',
  provenance:'NEW_CLEAN_AUTHOR_EXECUTION',cases:[],limitations:[
  'Service methods exercised directly, not HTTP transport.',
  'Application-injected failures do not establish physical service-outage behavior.',
  'Historical PC1 records and absolute block heights are not reused.',
  'Fresh-VM, process-SIGKILL and C8 independent execution are not covered here.']};
let serial=0,model;
const submitter=new SubmissionService(pool,{'Source A':connections['writer-a'],'Source B':connections['writer-b']});
const integrity=new IntegrityService(pool,connections.reader),access=new SessionAccess(pool);
const writeEvidence=()=>fs.writeFileSync('/work/DEVELOPMENT_CASES.json',JSON.stringify(evidence,null,2));
async function waitPeer(recordId) {
  for(let attempt=0;;attempt++) {
    try{return await integrity.peer(recordId);}
    catch(error) {
      if(attempt>=19)throw error;
      (evidence.retries ||= []).push({recordId,attempt:attempt+1,reason:error.message,
        timestamp:new Date().toISOString(),scope:'BOUNDED_TARGET_PEER_PROPAGATION'});
      await new Promise(r=>setTimeout(r,250));
    }
  }
}
async function check(id,fn) {
  const started=new Date().toISOString();
  try { const observed=await fn();evidence.cases.push({id,status:'PASS',observed,started,ended:new Date().toISOString()}); }
  catch(error) {
    evidence.cases.push({id,status:'FAIL',error:error.stack,started,ended:new Date().toISOString()});
    writeEvidence();throw error;
  }
  writeEvidence();console.log('PASS '+id);
}
function payload(source='Source A',operation='Yard-1') {
  const key='synthetic-'+String(++serial).padStart(6,'0');
  return source==='Source A'?{jobKey:key,operation,samples:[serial,serial+1]}:
    {plan:{key,operation},samples:[serial,serial+1]};
}
async function write(source='Source A',operation='Yard-1',fault=null) {
  const r=await submitter.submit(source,payload(source,operation),fault);
  if (!fault) assert.equal(r.status,'COMMITTED',JSON.stringify(r));
  return r;
}
async function main() {
  for(let attempt=0;;attempt++) {
    try {await pool.query('SELECT 1');break;}
    catch(error) {if(attempt>=19)throw error;await new Promise(r=>setTimeout(r,500));}
  }
  await redis.connect();await submitter.initialize();await access.initialize();
  model=new ReadModel(pool,redis,connections.reader);await model.initialize();
  const records=[];
  for(const [source,ops] of Object.entries({'Source A':['Yard-1','Yard-2','Yard-3'],
                                          'Source B':['Dispatch-1','Dispatch-2']}))
    for(const op of ops)for(let round=1;round<=3;round++)
      await check('C1.valid.'+op+'.'+round,async()=>{
        const r=await write(source,op);records.push(r.recordId);
        const peer=await waitPeer(r.recordId);assert.equal(peer.operation,op);
        return {status:r.status,recordId:r.recordId};
      });
  for(const field of ['A.key','A.operation','B.key','B.operation'])for(let round=1;round<=3;round++)
    await check('C1.omission.'+field+'.'+round,async()=>{
      const before=await pool.query('SELECT count(*) FROM artifact_payloads');
      const height=await model.height(),a=field.startsWith('A'),p=payload(a?'Source A':'Source B',a?'Yard-1':'Dispatch-1');
      if(a)delete p[field.endsWith('key')?'jobKey':'operation'];
      else delete p.plan[field.endsWith('key')?'key':'operation'];
      await assert.rejects(()=>submitter.submit(a?'Source A':'Source B',p));
      assert.deepEqual(await pool.query('SELECT count(*) FROM artifact_payloads').then(r=>r.rows),before.rows);
      assert.equal(await model.height(),height);
      return {dbWrites:0,ledgerWrites:0};
    });
  for(const [name,source] of [['generic-a','Source A'],['wrong-a','Source A'],['admin-a','Source A'],
                            ['writer-b','Source A'],['writer-a','Source B']])
    await check('C1.denied.'+name+'.'+source,async()=>{
      const e=adapt(source,payload(source,source==='Source A'?'Yard-1':'Dispatch-1'));
      const expected={'generic-a':'writer attribute','wrong-a':'writer enrollment',
        'admin-a':'client OU','writer-b':'source MSP','writer-a':'source MSP'}[name];
      let denial;
      await assert.rejects(()=>connections[name].contract.submitTransaction('RecordIntegrationResult',JSON.stringify(e)),
        error=>{denial=error.message+' '+JSON.stringify(error.details);return denial.includes(expected);});
      await assert.rejects(()=>integrity.peer(e.recordId));
      return {ledgerRecordPresent:false,expectedDenial:expected,observedDenial:denial};
    });
  const ledgerOnly=[];
  for(const [name,source,op] of [['writer-a','Source A','Yard-1'],['writer-b','Source B','Dispatch-1']])
    await check('C1.direct-allowed.'+name,async()=>{
      const e=adapt(source,payload(source,op));
      await connections[name].contract.submitTransaction('RecordIntegrationResult',JSON.stringify(e));
      ledgerOnly.push(e.recordId);assert.equal((await waitPeer(e.recordId)).recordId,e.recordId);
      return {recordId:e.recordId,payloadRowExpected:false};
    });
  await check('C4.full-sync',async()=>{const r=await model.synchronize();assert.ok(r.height>8);return r;});
  const id=records[0];
  await check('C2.INT01.correctness-repeat',async()=>{
    for(let i=0;i<30;i++){const r=await integrity.inspect(id);assert.equal(r.scope,'VERIFIED');assert.equal(r.payloadProof,'VERIFIED');}
    return {repeats:30,scope:'VERIFIED',payloadProof:'VERIFIED',latencyMeasurement:false};
  });
  const baseline=(await pool.query('SELECT * FROM artifact_payloads WHERE record_id=$1',[id])).rows[0];
  const indexed=(await pool.query('SELECT envelope FROM artifact_index WHERE record_id=$1',[id])).rows[0].envelope;
  async function restore() {
    await pool.query('UPDATE artifact_payloads SET raw=$2,canonical=$3,stored_hash=$4,envelope=$5 WHERE record_id=$1',
                    [id,baseline.raw,baseline.canonical,baseline.stored_hash,baseline.envelope]);
    await pool.query('UPDATE artifact_index SET envelope=$2 WHERE record_id=$1',[id,indexed]);
  }
  for(const kind of ['raw','coordinated-hash','missing-ref','coordinated-metadata'])for(let round=1;round<=3;round++)
    await check('C2.'+kind+'.'+round,async()=>{
      try {
        const altered={...baseline.raw,samples:[9999]};
        if(kind==='raw')await pool.query('UPDATE artifact_payloads SET raw=$2 WHERE record_id=$1',[id,altered]);
        if(kind==='coordinated-hash') {
          await pool.query('UPDATE artifact_payloads SET raw=$2,canonical=$3,stored_hash=$4 WHERE record_id=$1',
            [id,altered,canonical(altered),payloadHash(altered)]);
          await pool.query('UPDATE artifact_index SET envelope=$2 WHERE record_id=$1',
            [id,{...indexed,payloadHash:payloadHash(altered)}]);
        }
        if(kind==='missing-ref') {
          const copy={...indexed};delete copy.payloadRef;
          await pool.query('UPDATE artifact_index SET envelope=$2 WHERE record_id=$1',[id,copy]);
        }
        if(kind==='coordinated-metadata') {
          await pool.query('UPDATE artifact_payloads SET envelope=$2 WHERE record_id=$1',
            [id,{...baseline.envelope,sourceOrg:'Source B',operation:'Dispatch-1'}]);
          await pool.query('UPDATE artifact_index SET envelope=$2 WHERE record_id=$1',
            [id,{...indexed,sourceOrg:'Source B',operation:'Dispatch-1'}]);
        }
        const r=await integrity.inspect(id);
        assert.equal(r.payloadProof,'MISMATCH');assert.equal(r.raw,null);
        assert.equal(r.scope,['coordinated-hash','coordinated-metadata'].includes(kind)?'MISMATCH':'VERIFIED');
        return {scope:r.scope,payloadProof:r.payloadProof,rawWithheld:true};
      } finally {await restore();}
    });
  await check('C2.peer-unavailable',async()=>{
    integrity.peerUnavailable=true;
    try {const r=await integrity.inspect(id);assert.equal(r.scope,'UNAVAILABLE');assert.equal(r.raw,null);return r;}
    finally{integrity.peerUnavailable=false;}
  });
  const sourceAuditor=await access.issue({subject:'synthetic-auditor-a',org:'Source A',role:'auditor'});
  const targetAuditor=await access.issue({subject:'synthetic-auditor-t',org:'Target T',role:'auditor'});
  const sourceReader=await access.issue({subject:'synthetic-reader-a',org:'Source A',role:'reader'});
  const wrongOrg=await access.issue({subject:'synthetic-reader-b',org:'Source B',role:'auditor'});
  const wrongRole=await access.issue({subject:'synthetic-other',org:'Target T',role:'guest'});
  for(const [name,token,action,status] of [
    ['F01',null,'raw',401],['F02','invalid','raw',401],['F03',wrongOrg,'raw',403],
    ['F04',wrongRole,'detail',403],['F05',sourceReader,'raw',403],
    ['F06',sourceAuditor,'raw',200],['F07',targetAuditor,'integrity',200],
    ['F08',sourceReader,'detail',200]])
    await check('C3.service.'+name,async()=>{
      const r=await integrity.route(access,token,action,id);assert.equal(r.status,status);
      if(status!==200)assert.deepEqual(Object.keys(r.body),['error']);
      return {status,transport:'DIRECT_SERVICE_METHOD_NOT_HTTP'};
    });
  await check('C3.service.F09',async()=>{
    access.auditUnavailable=true;
    try {const r=await integrity.route(access,sourceReader,'detail',id);assert.equal(r.status,200);assert.equal(r.body.samples,undefined);return {status:200,protectedRaw:false};}
    finally{access.auditUnavailable=false;}
  });
  await check('C3.service.audit-write-failure',async()=>{
    access.auditUnavailable=true;
    try {
      for(const action of ['raw','integrity']) {
        const r=await integrity.route(access,targetAuditor,action,id);
        assert.equal(r.status,503);assert.deepEqual(r.body,{error:'audit unavailable'});
      }
      return {rawStatus:503,integrityStatus:503,leakage:0,injection:'APPLICATION'};
    }finally{access.auditUnavailable=false;}
  });
  await check('C3.service.revocation',async()=>{
    await access.revoke(sourceAuditor);
    assert.equal((await integrity.route(access,sourceAuditor,'raw',id)).status,401);
    assert.equal((await integrity.route(access,targetAuditor,'raw',id)).status,200);
    return {revoked:401,independentSession:200};
  });
  await check('C4.multi-gap-pagination',async()=>{
    await pool.query('DELETE FROM artifact_blocks WHERE number BETWEEN 0 AND 7');
    const r=await model.synchronize();assert.equal(r.pageQueries,4);return r;
  });
  for(let i=0;i<10;i++)await check('C4.gap.'+i,async()=>{
    await pool.query('DELETE FROM artifact_blocks WHERE number=$1',[i]);
    const r=await model.synchronize();
    assert.equal((await pool.query('SELECT count(*) FROM artifact_blocks WHERE number=$1',[i])).rows[0].count,'1');return r;
  });
  for(let i=0;i<2;i++)await check('C4.retry-replay.'+i,async()=>{
    await pool.query('DELETE FROM artifact_blocks WHERE number=$1',[i]);
    const block=await model.fetch(i);
    await assert.rejects(()=>model.apply(block,true));
    assert.equal((await pool.query('SELECT count(*) FROM artifact_blocks WHERE number=$1',[i])).rows[0].count,'0');
    await model.apply(block);await model.apply(block);return await model.synchronize();
  });
  for(let i=0;i<10;i++)await check('C4.instance-recreation.'+i,async()=>{
    model=null;const r=await write();
    model=new ReadModel(pool,redis,connections.reader);await model.initialize();await model.synchronize();
    assert.equal((await integrity.inspect(r.recordId)).payloadProof,'VERIFIED');
    return {newObjectInstance:true,newProcess:false};
  });
  for(let i=0;i<10;i++)await check('C4.finalize-failure.'+i,async()=>{
    const r=await write('Source A','Yard-1','finalize-failure');assert.equal(r.status,'RECEIVED');
    await model.synchronize();
    assert.equal((await pool.query('SELECT status FROM artifact_payloads WHERE record_id=$1',[r.recordId])).rows[0].status,'COMMITTED');
    return {before:'RECEIVED',after:'COMMITTED',injection:'APPLICATION'};
  });
  await check('C4.uncertain-classification',async()=>{
    const absent=[],present=[];
    for(let i=0;i<10;i++)absent.push((await write('Source A','Yard-1','not-submitted')).recordId);
    for(let i=0;i<2;i++)present.push((await write('Source A','Yard-1','commit-then-timeout')).recordId);
    await model.synchronize();
    for(const recordId of absent)assert.equal((await pool.query('SELECT status FROM artifact_payloads WHERE record_id=$1',[recordId])).rows[0].status,'UNKNOWN');
    for(const recordId of present)assert.equal((await pool.query('SELECT status FROM artifact_payloads WHERE record_id=$1',[recordId])).rows[0].status,'COMMITTED');
    return {knownNotSubmitted:absent,committedApplicationTimeout:present,falseFinalizations:0};
  });
  await check('C4.validation-metadata',async()=>{
    // Two endorsed writes of one absent key: second is genuinely MVCC-invalid.
    const e=adapt('Source A',payload());
    const p1=await connections['writer-a'].contract.newProposal('RecordIntegrationResult',{arguments:[JSON.stringify(e)]}).endorse();
    const p2=await connections['writer-a'].contract.newProposal('RecordIntegrationResult',{arguments:[JSON.stringify(e)]}).endorse();
    assert.equal((await (await p1.submit()).getStatus()).successful,true);
    assert.equal((await (await p2.submit()).getStatus()).successful,false);
    ledgerOnly.push(e.recordId);await model.synchronize();
    const rows=(await pool.query('SELECT valid FROM artifact_transactions WHERE tx_id=ANY($1)',[[p1.getTransactionId(),p2.getTransactionId()]])).rows;
    assert.equal(rows.filter(r=>r.valid).length,1);assert.equal(rows.filter(r=>!r.valid).length,1);
    return {valid:1,invalid:1,invalidEvidenceProjected:0};
  });
  const terminal=await model.synchronize();
  const missing=(await pool.query(`SELECT i.record_id FROM artifact_index i LEFT JOIN artifact_payloads p
    ON p.record_id=i.record_id WHERE p.record_id IS NULL ORDER BY i.record_id`)).rows.map(r=>r.record_id);
  assert.deepEqual(missing,[...ledgerOnly].sort());
  evidence.terminal={...terminal,redis:await redis.get('artifact:checkpoint'),
    ledgerOnlyRecords:missing,population:'NEW_EXPLICIT_SQL_NOT_HISTORICAL_FIVE_UNDEFINED_FIELDS'};
  const ledger=JSON.parse(Buffer.from(await connections.reader.contract.evaluateTransaction('ListEvidence')).toString());
  const indexedFinal=(await pool.query('SELECT record_id,tx_id,envelope FROM artifact_index ORDER BY record_id')).rows;
  assert.deepEqual(indexedFinal.map(r=>r.record_id),ledger.map(r=>r.recordId).sort());
  fs.writeFileSync('/work/PROJECTION_SNAPSHOT.json',JSON.stringify({
    provenance:'NEW_CLEAN_AUTHOR_EXECUTION',terminal:evidence.terminal,
    ledger,blocks:(await pool.query('SELECT number FROM artifact_blocks ORDER BY number')).rows,
    transactions:(await pool.query('SELECT * FROM artifact_transactions ORDER BY tx_id')).rows,
    index:indexedFinal,payloadStates:(await pool.query('SELECT record_id,tx_id,status FROM artifact_payloads ORDER BY record_id')).rows
  },null,2));
  evidence.status='PASS_WITH_DECLARED_SCOPE_LIMITS';
}
const deadline=setTimeout(()=>{console.error('integration deadline');writeEvidence();process.exit(124);},240000);
main().catch(error=>{evidence.status='FAIL';evidence.error=error.stack;console.error(error);process.exitCode=4;})
  .finally(async()=>{
    writeEvidence();clearTimeout(deadline);
    for(const c of Object.values(connections))c.close();
    if(redis.isOpen)await redis.quit();await pool.end();
  });
