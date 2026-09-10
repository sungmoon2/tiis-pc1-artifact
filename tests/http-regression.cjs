// SPDX-FileCopyrightText: 2026 Sungmoon Park
// SPDX-License-Identifier: Apache-2.0
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),{randomBytes}=require('node:crypto');
const {spawn}=require('node:child_process'),{Pool}=require('/work/api/node_modules/pg');
const {SessionAccess}=require('/work/web/src/access');
const {connectIdentity}=require('/work/api/src/gateway');
const {ReadModel}=require('/work/web/src/read-model');
const {createClient}=require('/work/web/node_modules/@redis/client');
const readerConnection=connectIdentity(JSON.parse(fs.readFileSync('/work/identities.json')).reader);
const checkpointClient=createClient({url:'redis://redis:6379',socket:{reconnectStrategy:false}});
checkpointClient.on('error',error=>console.error(error.message));
const config={control:randomBytes(32).toString('hex'),sources:{
  'Source A':randomBytes(32).toString('hex'),'Source B':randomBytes(32).toString('hex')}};
fs.writeFileSync('/work/test-control.json',JSON.stringify(config),{mode:0o600});
const pool=new Pool({host:'postgres',user:'artifact',database:'artifact',
  password:fs.readFileSync('/work/database-password','utf8'),max:2});
const access=new SessionAccess(pool),children=[];
const result={scope:'NEW_HTTP_AND_PROCESS_REGRESSION_NOT_G3_OR_C8',cases:[],processes:[]};
async function request(port,path,{method='GET',token,body,control=false,source,fault}={}) {
  const headers={};
  if(token)headers.authorization='Bearer '+token;
  if(control)headers['x-test-control']=config.control;
  if(source)headers['x-source']=source;
  if(fault)headers['x-test-fault']=fault;
  if(body)headers['content-type']='application/json';
  const r=await fetch('http://127.0.0.1:'+port+path,{method,headers,
    body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(30000)});
  return {status:r.status,body:await r.json()};
}
async function launch(component) {
  const child=spawn(process.execPath,['/work/'+component+'/src/process.js'],{stdio:['ignore','pipe','pipe']});
  children.push(child);
  const log=fs.createWriteStream('/work/'+component+'-process-'+child.pid+'.log');
  child.stdout.pipe(log);child.stderr.pipe(log);
  for(let i=0;i<100;i++) {
    if(child.exitCode!==null)throw new Error(component+' exited '+child.exitCode);
    try {const r=await request(component==='api'?8080:8081,'/health');
      if(r.status===200){result.processes.push({component,pid:child.pid});return child;}}catch(_){}
    await new Promise(r=>setTimeout(r,100));
  }
  throw new Error(component+' readiness deadline');
}
const persist=()=>fs.writeFileSync('/work/HTTP_CASES.json',JSON.stringify(result,null,2));
async function check(id,fn) {
  try{result.cases.push({id,status:'PASS',observed:await fn()});console.log('PASS '+id);}
  catch(error){result.cases.push({id,status:'FAIL',error:error.stack});persist();throw error;}
  persist();
}
async function stop(child,signal='SIGTERM') {
  assert.ok(children.includes(child),'only recorded own child processes may be signalled');
  if(child.exitCode!==null || child.signalCode!==null)return;
  const exited=new Promise(resolve=>child.once('exit',(code,sig)=>resolve({code,signal:sig})));
  child.kill(signal);
  return await Promise.race([exited,new Promise((_,reject)=>setTimeout(()=>reject(new Error('child stop deadline')),10000))]);
}
async function main() {
  await checkpointClient.connect();
  await launch('api');let web=await launch('web');
  const id=(await pool.query("SELECT i.record_id FROM artifact_index i JOIN artifact_payloads p ON p.record_id=i.record_id WHERE i.envelope->>'sourceOrg'='Source A' AND p.status='COMMITTED' ORDER BY i.record_id LIMIT 1")).rows[0].record_id;
  const a=await access.issue({subject:'synthetic-http-a',org:'Source A',role:'auditor'});
  const t=await access.issue({subject:'synthetic-http-t',org:'Target T',role:'auditor'});
  const reader=await access.issue({subject:'synthetic-http-reader',org:'Source A',role:'reader'});
  const wrong=await access.issue({subject:'synthetic-http-b',org:'Source B',role:'auditor'});
  const guest=await access.issue({subject:'synthetic-http-guest',org:'Target T',role:'guest'});
  for(const [name,token,action,status] of [['F01',null,'raw',401],['F02','invalid','raw',401],
    ['F03',wrong,'raw',403],['F04',guest,'detail',403],['F05',reader,'raw',403],
    ['F06',a,'raw',200],['F07',t,'integrity',200],['F08',reader,'detail',200]])
    await check('C3.http.'+name,async()=>{
      const r=await request(8081,'/records/'+id+'/'+action,{token});assert.equal(r.status,status);
      if(status!==200)assert.deepEqual(Object.keys(r.body),['error']);
      return {status,transport:'HTTP',protectedLeakage:0};
    });
  const faults=async(value)=>assert.equal((await request(8081,'/test-control',
    {method:'POST',control:true,body:{action:'faults',...value}})).status,200);
  await check('C3.http.F09',async()=>{
    await faults({auditUnavailable:true});
    try{const r=await request(8081,'/records/'+id+'/detail',{token:reader});
      assert.equal(r.status,200);assert.equal(r.body.samples,undefined);return {status:200,raw:false};}
    finally{await faults({});}
  });
  await check('C3.http.audit-failure',async()=>{
    await faults({auditUnavailable:true});
    try{for(const action of ['raw','integrity']) {
      const r=await request(8081,'/records/'+id+'/'+action,{token:t});
      assert.equal(r.status,503);assert.deepEqual(r.body,{error:'audit unavailable'});}
      return {raw:503,integrity:503,protectedLeakage:0,injection:'APPLICATION_NOT_PHYSICAL_DB_OUTAGE'};
    }finally{await faults({});}
  });
  await check('C3.http.revocation',async()=>{
    await access.revoke(a);
    assert.equal((await request(8081,'/records/'+id+'/raw',{token:a})).status,401);
    assert.equal((await request(8081,'/records/'+id+'/raw',{token:t})).status,200);
    return {revoked:401,otherSession:200};
  });
  await check('C1.http.authentication-side-effects',async()=>{
    const before=(await pool.query('SELECT count(*) FROM artifact_payloads')).rows;
    const r=await request(8080,'/submit',{method:'POST',source:'Source A',token:'invalid',
      body:{jobKey:'synthetic-http-denied',operation:'Yard-1',samples:[1]}});
    assert.equal(r.status,401);
    assert.deepEqual((await pool.query('SELECT count(*) FROM artifact_payloads')).rows,before);
    return {status:401,dbWrites:0};
  });
  await check('C1.http.valid-submit',async()=>{
    const r=await request(8080,'/submit',{method:'POST',source:'Source A',token:config.sources['Source A'],
      body:{jobKey:'synthetic-http-valid',operation:'Yard-1',samples:[1]}});
    assert.equal(r.status,200);assert.equal(r.body.status,'COMMITTED');
    let verified=false;
    for(let attempt=0;attempt<20;attempt++) {
      const sync=await request(8081,'/test-control',{method:'POST',control:true,body:{action:'sync'}});
      assert.equal(sync.status,200);
      const proof=await request(8081,'/records/'+r.body.recordId+'/integrity',{token:t});
      if(proof.status===200&&proof.body.scope==='VERIFIED'&&proof.body.payloadProof==='VERIFIED'){verified=true;break;}
      await new Promise(resolve=>setTimeout(resolve,250));
    }
    assert.equal(verified,true);return {status:200,ledger:r.body.status};
  });
  await check('C4.separate-process-SIGKILL',async()=>{
    const snapshot=async()=>({
      blocks:(await pool.query('SELECT * FROM artifact_blocks ORDER BY number')).rows,
      transactions:(await pool.query('SELECT * FROM artifact_transactions ORDER BY tx_id')).rows,
      index:(await pool.query('SELECT * FROM artifact_index ORDER BY record_id')).rows});
    const before=await snapshot(),oldPid=web.pid;
    const checkpoint=(await request(8081,'/test-control',{method:'POST',control:true,body:{action:'checkpoint'}})).body;
    const termination=await stop(web,'SIGKILL');assert.equal(termination.signal,'SIGKILL');
    // No writes during downtime; this tests process continuity, not catch-up.
    web=await launch('web');assert.notEqual(web.pid,oldPid);
    assert.deepEqual(await snapshot(),before);
    assert.deepEqual((await request(8081,'/test-control',{method:'POST',control:true,body:{action:'checkpoint'}})).body,checkpoint);
    assert.equal((await request(8081,'/records/'+id+'/raw',{token:t})).status,200);
    return {oldPid,newPid:web.pid,signal:'SIGKILL',projectionUnchanged:true,checkpointUnchanged:true,downtimeWrites:0,
      includedInCounted36:false};
  });
  const finalModel=new ReadModel(pool,checkpointClient,readerConnection);
  const final=await finalModel.synchronize();
  const ledger=JSON.parse(Buffer.from(await readerConnection.contract.evaluateTransaction('ListEvidence')).toString());
  const indexed=(await pool.query('SELECT record_id,tx_id,envelope FROM artifact_index ORDER BY record_id')).rows;
  assert.deepEqual(indexed.map(r=>r.record_id),ledger.map(r=>r.recordId).sort());
  const missing=(await pool.query('SELECT i.record_id FROM artifact_index i LEFT JOIN artifact_payloads p ON p.record_id=i.record_id WHERE p.record_id IS NULL ORDER BY i.record_id')).rows.map(r=>r.record_id);
  fs.writeFileSync('/work/FINAL_PROJECTION_SNAPSHOT.json',JSON.stringify({
    provenance:'NEW_CLEAN_AUTHOR_EXECUTION',phase:'AFTER_HTTP_AND_PROCESS_REGRESSION',
    terminal:{...final,redis:await checkpointClient.get('artifact:checkpoint'),ledgerOnlyRecords:missing},
    ledger,blocks:(await pool.query('SELECT number FROM artifact_blocks ORDER BY number')).rows,
    transactions:(await pool.query('SELECT * FROM artifact_transactions ORDER BY tx_id')).rows,
    index:indexed,payloadStates:(await pool.query('SELECT record_id,tx_id,status FROM artifact_payloads ORDER BY record_id')).rows
  },null,2));
  result.status='PASS';
}
const deadline=setTimeout(()=>{persist();process.exit(124);},180000);
main().catch(error=>{result.status='FAIL';result.error=error.stack;console.error(error);process.exitCode=4;})
  .finally(async()=>{for(const child of children)await stop(child).catch(error=>{
    result.teardownError=error.message;process.exitCode=6;});
    readerConnection.close();if(checkpointClient.isOpen)await checkpointClient.quit();
    await pool.end();clearTimeout(deadline);persist();});
