# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'release'))
from validators import *
class PublicationTests(unittest.TestCase):
    def fixture(self):
        h='a'*64;commit='b'*40;tree='c'*40;url='https://github.com/synthetic-owner/synthetic-artifact'
        binding={'schema':'tiis-publication-binding/v1','candidate_binding_sha256':h,
         'g4_release_manifest_sha256':h,'g5_execution':{k:h for k in PUBLICATION['properties']['g5_execution']['properties']},
         'public_release':{'immutable_tag':'unit-ga','components_lock_sha256':h,'ga_release_manifest_sha256':h,
          'umbrella':{'url':url,'commit':commit,'tree':tree,'archive_sha256':h},
          'components':[{'id':name,'url':url+'-'+name,'immutable_tag':'unit-ga','commit':commit,'tree':tree,'archive_sha256':h}
                         for name in ['api','web','network','chaincode']]},
         'unauthenticated_readback_receipt_sha256':h,
         'preservation':{'kind':'GITHUB_IMMUTABLE_RELEASE','locator':url+'/releases/tag/unit-ga','receipt_sha256':h},
         'c8_status':'PENDING_C8_EVIDENCE_RELEASE_READBACK'}
        raw=json.dumps(binding).encode()
        value={'schema':'tiis-c8-completion/v1','status':'COMPLETED','publication_binding_sha256':hashlib.sha256(raw).hexdigest(),
         'c8_evidence':{'ref':'refs/tags/tiis-pc1-c8-v1.0.0','tag_object_sha256':h,
          'release_url':url+'/releases/tag/tiis-pc1-c8-v1.0.0','evidence_manifest_sha256':h,'readback_receipt_sha256':h},
         'ga_target':{'commit':commit,'tree':tree}}
        tag={'type':'commit','target':commit,'peeled_target':commit}
        return binding,raw,value,tag
    def encode(self,value):return b'TIIS-C8-COMPLETION-V1\n'+json.dumps(value,separators=(',',':')).encode()+b'\n'
    def test_positive(self):
        binding,raw,value,tag=self.fixture()
        self.assertEqual(completion(self.encode(value),raw,value['c8_evidence'],tag)['validation'],'PASS')
        binding['doi']='10.1234/unit-test';publication(json.dumps(binding).encode())
    def test_publication_negatives(self):
        base,_,_,_=self.fixture()
        mutations=[]
        for key in ['preservation','candidate_binding_sha256','g5_execution']:
            d=copy.deepcopy(base);del d[key];mutations.append(d)
        for key,value in [('doi',None),('self_sha256','a'*64),('c8_status','COMPLETED')]:
            mutations.append({**base,key:value})
        d=copy.deepcopy(base);d['public_release']['components'][0]['id']='web';mutations.append(d)
        d=copy.deepcopy(base);d['preservation']['locator']='https://github.com/a/b/releases/tag/wrong';mutations.append(d)
        for d in mutations:
            with self.assertRaises(ValueError):publication(json.dumps(d).encode())
    def test_completion_negatives(self):
        binding,raw,value,tag=self.fixture();good=self.encode(value)
        malformed=[good.replace(b'\n',b'\r\n'),good+b'\n',good.replace(b'"schema":',b'"extra":0,"schema":',1),
          good.replace(b'"status":"COMPLETED",',b''),good.replace(b'"status":"COMPLETED"',b'"status":"COMPLETED","status":"COMPLETED"'),
          good.replace(b'"status":"COMPLETED"',b'"status": "COMPLETED"'),
          self.encode(dict(reversed(list(value.items()))))]
        for data in malformed:
            with self.assertRaises(ValueError):completion(data,raw,value['c8_evidence'],tag)
        for field in ['publication_binding_sha256']:
            d=copy.deepcopy(value);d[field]='x'*64
            with self.assertRaises(ValueError):completion(self.encode(d),raw,value['c8_evidence'],tag)
        d=copy.deepcopy(value);d['c8_evidence']['release_url']='http://example.invalid'
        with self.assertRaises(ValueError):completion(self.encode(d),raw,value['c8_evidence'],tag)
        for field,wrong in [('type','tag'),('target','d'*40),('peeled_target','e'*40)]:
            with self.assertRaises(ValueError):completion(good,raw,value['c8_evidence'],{**tag,field:wrong})
        with self.assertRaises(ValueError):completion(good,raw,{**value['c8_evidence'],'readback_receipt_sha256':'d'*64},tag)
if __name__=='__main__':unittest.main()
