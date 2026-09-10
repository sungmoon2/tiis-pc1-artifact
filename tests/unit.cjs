// SPDX-FileCopyrightText: 2026 Sungmoon Park
// SPDX-License-Identifier: Apache-2.0
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const base = path.resolve(process.argv[2] || path.join(__dirname,'../..'));
const component = name => require(path.join(base,'tiis-pc1-'+name));
const api = require(path.join(base,'tiis-pc1-api/src/envelope'));
const canonicalizers = ['api','web','chaincode'].map(name =>
  require(path.join(base,'tiis-pc1-'+name+'/src/canonical')));
const vectors = [
  [{ '2':'two','10':'ten',a:1 },'{"10":"ten","2":"two","a":1}'],
  [{ z:[null,{ b:true,a:false }],a:[] },'{"a":[],"z":[null,{"a":false,"b":true}]}'],
  [{ text:'합성 😀',b:0 },'{"b":0,"text":"합성 😀"}'],
  [{ z:-0,a:1.25 },'{"a":1.25,"z":0}'],
];
for (let i=0;i<vectors.length;i++) test('KAT-'+(i+1),() => {
  const [input,expected]=vectors[i];
  for (const impl of canonicalizers) assert.equal(impl.canonical(input),expected);
  assert.equal(new Set(canonicalizers.map(impl=>impl.payloadHash(input))).size,1);
});
test('JSON domain rejection and undefined policy',() => {
  for (const impl of canonicalizers) {
    assert.equal(impl.canonical({b:undefined,a:[undefined]}),'{"a":[null]}');
    for (const value of [NaN,Infinity,1n,()=>{},new Date()]) assert.throws(()=>impl.canonical(value));
    const cyclic={};cyclic.self=cyclic;assert.throws(()=>impl.canonical(cyclic));
  }
});
for (const [source,operations] of Object.entries({'Source A':['Yard-1','Yard-2','Yard-3'],
                                               'Source B':['Dispatch-1','Dispatch-2']})) {
  for (const operation of operations) for (let round=1;round<=3;round++)
    test('adapter valid '+operation+' '+round,() => {
      const payload=source==='Source A'?{jobKey:'synthetic-'+round,operation,samples:[round]}:
        {plan:{key:'synthetic-'+round,operation},samples:[round]};
      const e=api.adapt(source,payload);
      assert.equal(api.validate(e),e);
      for (const name of ['chaincode']) {
        const other=require(path.join(base,'tiis-pc1-'+name+'/src/envelope'));
        assert.deepEqual(other.validate(e),e);
      }
    });
}
for (const field of ['A.key','A.operation','B.key','B.operation']) for (let round=1;round<=3;round++)
  test('adapter missing '+field+' '+round,() => {
    const a=field.startsWith('A');
    const p=a?{jobKey:'synthetic',operation:'Yard-1'}:{plan:{key:'synthetic',operation:'Dispatch-1'}};
    if(a) delete p[field.endsWith('key')?'jobKey':'operation'];
    else delete p.plan[field.endsWith('key')?'key':'operation'];
    assert.throws(()=>api.adapt(a?'Source A':'Source B',p));
  });
test('1.2 writer / 1.1 consumer common envelope preserved, extensions not invented',() => {
  const writer=api.contract;
  const consumer=require(path.join(base,'tiis-pc1-web/contracts/integration-contract.json'));
  assert.ok(writer.contractId.endsWith('/1.2.0'));
  assert.ok(consumer.contractId.endsWith('/1.1.0'));
  assert.deepEqual(writer.envelope,consumer.envelope);
  assert.equal(consumer.fabricPrincipal.writerAttribute,undefined);
  assert.equal(consumer.query,undefined);
  for(const [source,s] of Object.entries(writer.sources)) {
    const {writerEnrollmentId,...common}=s;
    assert.deepEqual(common,consumer.sources[source]);
  }
});
test('envelope altered fields fail closed',() => {
  const e=api.adapt('Source A',{jobKey:'synthetic',operation:'Yard-1'});
  for(const patch of [{targetOrg:'Source B'},{payloadHash:'sha256:BAD'},{recordId:'0'.repeat(24)},
    {payloadRef:'http://invalid.example'},{operation:'Dispatch-1'},{payloadSizeBytes:-1},
    {submittedAt:'2026-09-09'},{extra:true},{businessId:'x|y'}])
    assert.throws(()=>api.validate({...e,...patch}));
});
