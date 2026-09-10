#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""Bounded offline validators. Never creates Git tags, attestations or C8 claims."""
import hashlib,json,re
from bundle import unique_json
H40={'type':'string','pattern':'^[a-f0-9]{40}$'}
H64={'type':'string','pattern':'^[a-f0-9]{64}$'}
TEXT={'type':'string','minLength':1}
URL={'type':'string','pattern':r'^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/releases/tag/[A-Za-z0-9_.-]+)?$'}
RELEASE_URL={'type':'string','pattern':r'^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/releases/tag/[A-Za-z0-9_.-]+$'}
def obj(properties,required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,
            'additionalProperties':False}
COMPONENT=obj({'id':{'enum':['api','web','network','chaincode']},'url':URL,'immutable_tag':TEXT,
               'commit':H40,'tree':H40,'archive_sha256':H64})
PUBLICATION=obj({
 'schema':{'const':'tiis-publication-binding/v1'},'candidate_binding_sha256':H64,
 'g4_release_manifest_sha256':H64,
 'g5_execution':obj({k:H64 for k in ['target_manifest_sha256','evidence_manifest_sha256','result_sha256','public_executor_attestation_sha256']}),
 'public_release':obj({'immutable_tag':TEXT,'components_lock_sha256':H64,'ga_release_manifest_sha256':H64,
   'umbrella':obj({'url':URL,'commit':H40,'tree':H40,'archive_sha256':H64}),
   'components':{'type':'array','minItems':4,'maxItems':4,'items':COMPONENT}}),
 'unauthenticated_readback_receipt_sha256':H64,
 'preservation':obj({'kind':{'const':'GITHUB_IMMUTABLE_RELEASE'},'locator':RELEASE_URL,'receipt_sha256':H64}),
 'c8_status':{'const':'PENDING_C8_EVIDENCE_RELEASE_READBACK'},
 'doi':{'type':'string','pattern':r'^10\.[0-9]{4,9}/[^\s]+$'},
 'external_preservation':obj({'locator':{'type':'string','pattern':r'^https://[^\s?#@]+$'},'receipt_sha256':H64})},
 required=['schema','candidate_binding_sha256','g4_release_manifest_sha256','g5_execution','public_release',
           'unauthenticated_readback_receipt_sha256','preservation','c8_status'])
COMPLETION=obj({
 'schema':{'const':'tiis-c8-completion/v1'},'status':{'const':'COMPLETED'},'publication_binding_sha256':H64,
 'c8_evidence':obj({'ref':{'type':'string','pattern':r'^refs/tags/tiis-pc1-c8-v[0-9]+\.[0-9]+\.[0-9]+(?:-r[2-9][0-9]*)?$'},
   'tag_object_sha256':H64,'release_url':RELEASE_URL,'evidence_manifest_sha256':H64,'readback_receipt_sha256':H64}),
 'ga_target':obj({'commit':H40,'tree':H40})})
IDENTITY=obj({'logical_id':TEXT,'full_commit':H40,'tree':H40,'archive_sha256':H64,'archive_bytes':{'type':'integer'}})
RELEASE_PROPERTIES={
 'schema':{'const':'tiis-release-manifest/v1'},'stage':{'enum':['G2_CANDIDATE','G3_LOCAL_PASS','G4_PRIVATE_PASS','G5_INDEPENDENT_PASS','G6_PUBLIC_GA']},
 'created_utc':{'type':'string','pattern':r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'},
 'claims':{'const':['C1','C2','C3','C4']},'candidate_binding_sha256':H64,'components_lock_sha256':H64,
 'previous_stage_manifest_sha256':H64,'umbrella':IDENTITY,
 'components':{'type':'array','items':IDENTITY,'minItems':4,'maxItems':4},
 'rc_input_bundle':obj({'sha256':H64,'bytes':{'type':'integer'},'inner_manifest_sha256':H64}),
 'versions_lock_sha256':H64,'images_lock_sha256':H64,
 'expected_result_sha256':obj({c:H64 for c in ['C1','C2','C3','C4']}),
 'license_notice_manifest_sha256':H64,'sbom_sha256':H64,'security_scan_receipt_sha256':H64,
 'evidence_manifest_sha256':H64,'result_sha256':H64,'attempt_ids':{'type':'array','minItems':1,'items':TEXT},
 'paper_track':{'const':'TIIS'},'release_id':TEXT,'release_status':TEXT,
 'parent_release':obj({'manifest_sha256':H64}),'repository_role':{'const':'umbrella'},
 'repository_url_candidate':URL,'branch':TEXT,'full_commit_sha':H40,'dirty_status':{'const':'CLEAN'},
 **{name:H40 for name in ['API_commit','Web_commit','Network_commit','chaincode_commit']},
 'chaincode_name':TEXT,'chaincode_version':obj({'source_package_version':TEXT,'lifecycle_version':TEXT}),
 'chaincode_sequence':{'type':'integer'},'chaincode_package_identity':TEXT,
 'container_image_digest':{'type':'array','minItems':1,'items':{'type':'string','pattern':'^sha256:[a-f0-9]{64}$'}},
 'configuration_sha256':H64,'artifact_sha256':H64,'included_scope':{'type':'array','items':TEXT},
 'excluded_scope':{'type':'array','items':TEXT},'license_status':{'const':'PASS_SOURCE_SCOPE'},
 'sensitive_data_status':{'const':'PASS_SCOPED_SCANS'},'TIIS_claim_link':{'const':['C1','C2','C3','C4']},
 'SoftwareX_baseline_impact':TEXT,
 'external':obj({'repository_id':{'type':'integer'},'workflow_sha':H40,'workflow_ref':TEXT,
   'rc_tag_object':H40,'artifact_id':{'type':'integer'},'artifact_sha256':H64}),
 'public_executor_attestation_sha256':H64,'transfer_receipt_sha256':H64}
CONDITIONAL_FIELDS={'previous_stage_manifest_sha256','parent_release','repository_url_candidate',
 'evidence_manifest_sha256','result_sha256','attempt_ids','external','public_executor_attestation_sha256','transfer_receipt_sha256'}
RELEASE=obj(RELEASE_PROPERTIES,required=[k for k in RELEASE_PROPERTIES if k not in CONDITIONAL_FIELDS])
class Invalid(ValueError):pass
def validate(schema,value):
    known={'type','properties','required','additionalProperties','items','minItems','maxItems',
           'minLength','pattern','const','enum','description','title','$schema'}
    if set(schema)-known:raise Invalid('unsupported schema keyword')
    if 'const' in schema and value!=schema['const']:raise Invalid('constant mismatch')
    if 'enum' in schema and value not in schema['enum']:raise Invalid('enum mismatch')
    kind=schema.get('type')
    types={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'number':(int,float)}
    if kind and (kind not in types or type(value) not in (types[kind] if isinstance(types[kind],tuple) else (types[kind],))):
        raise Invalid('type mismatch')
    if kind=='object':
        if set(schema.get('required',[]))-set(value):raise Invalid('required field missing')
        if schema.get('additionalProperties') is False and set(value)-set(schema.get('properties',{})):
            raise Invalid('unknown field')
        for key,child in schema.get('properties',{}).items():
            if key in value:validate(child,value[key])
    if kind=='array':
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',10**9):raise Invalid('array length')
        for item in value:validate(schema['items'],item)
    if kind=='string':
        if len(value)<schema.get('minLength',0):raise Invalid('empty string')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'],value):raise Invalid('string pattern')
    return value
def publication(raw):
    value=validate(PUBLICATION,unique_json(raw))
    if {r['id'] for r in value['public_release']['components']}!={'api','web','network','chaincode'}:
        raise Invalid('component set mismatch')
    if value['preservation']['locator'] != value['public_release']['umbrella']['url']+'/releases/tag/'+value['public_release']['immutable_tag']:
        raise Invalid('preservation release mismatch')
    return value
def release(raw):
    value=validate(RELEASE,unique_json(raw))
    order=['G2_CANDIDATE','G3_LOCAL_PASS','G4_PRIVATE_PASS','G5_INDEPENDENT_PASS','G6_PUBLIC_GA']
    stage=order.index(value['stage'])
    needed=set()
    if stage>=1:needed|={'previous_stage_manifest_sha256','parent_release','evidence_manifest_sha256','result_sha256','attempt_ids'}
    if stage>=2:needed|={'repository_url_candidate','external'}
    if stage>=3:needed|={'public_executor_attestation_sha256','transfer_receipt_sha256'}
    if set(value)&CONDITIONAL_FIELDS!=needed:raise Invalid('stage field presence/absence')
    if stage>=1 and value['parent_release']['manifest_sha256']!=value['previous_stage_manifest_sha256']:
        raise Invalid('parent hash chain')
    components={r['logical_id']:r for r in value['components']}
    if set(components)!={'api','web','network','chaincode'}:raise Invalid('component identity set')
    for field,name in [('API_commit','api'),('Web_commit','web'),('Network_commit','network'),('chaincode_commit','chaincode')]:
        if value[field]!=components[name]['full_commit']:raise Invalid('component mirrored commit')
    if value['full_commit_sha']!=value['umbrella']['full_commit'] or value['artifact_sha256']!=value['umbrella']['archive_sha256']:
        raise Invalid('umbrella mirrored identity')
    if value['chaincode_sequence']<1 or value['rc_input_bundle']['bytes']<1:raise Invalid('positive size/sequence')
    if any(r['archive_bytes']<1 for r in value['components']+[value['umbrella']]):raise Invalid('archive size')
    return value
def completion(raw,binding_raw,readback,tag):
    if not isinstance(raw,bytes) or b'\r' in raw or raw.count(b'\n')!=2 or not raw.endswith(b'\n'):
        raise Invalid('UTF-8/LF framing')
    lines=raw.decode('utf-8').splitlines()
    if lines[0]!='TIIS-C8-COMPLETION-V1':raise Invalid('completion prefix')
    value=validate(COMPLETION,unique_json(lines[1]))
    for dictionary,keys in [(value,list(COMPLETION['properties'])),
       (value['c8_evidence'],list(COMPLETION['properties']['c8_evidence']['properties'])),
       (value['ga_target'],['commit','tree'])]:
        if list(dictionary)!=keys:raise Invalid('key order')
    if raw!=b'TIIS-C8-COMPLETION-V1\n'+json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()+b'\n':
        raise Invalid('noncanonical completion encoding')
    binding=publication(binding_raw)
    if value['publication_binding_sha256']!=hashlib.sha256(binding_raw).hexdigest():raise Invalid('binding hash')
    ga=binding['public_release']['umbrella']
    if value['ga_target']!={'commit':ga['commit'],'tree':ga['tree']}:raise Invalid('GA target')
    if value['c8_evidence']!=readback:raise Invalid('readback binding')
    if tag!={'type':'commit','target':ga['commit'],'peeled_target':ga['commit']}:raise Invalid('tag type/target')
    if value['c8_evidence']['release_url']!=ga['url']+'/releases/tag/'+value['c8_evidence']['ref'].split('/')[-1]:
        raise Invalid('evidence release locator')
    return {'validation':'PASS','actual_C8_completion_claim':'NOT_MADE_BY_OFFLINE_VALIDATOR'}
