#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""Strict named-result comparator; no missing/extra/duplicate/unknown success."""
import json, sys
def typed_equal(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return set(a)==set(b) and all(typed_equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(typed_equal(x,y) for x,y in zip(a,b))
    return a==b
def load(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    with open(path,encoding='utf-8') as stream:
        return json.load(stream,object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
def compare(expected,actual):
    if set(actual)!={'claim','provenance','cases'}: raise ValueError('top-level fields')
    if actual['claim']!=expected['claim']: raise ValueError('claim mismatch')
    if actual['provenance']!='NEW_CLEAN_AUTHOR_EXECUTION': raise ValueError('provenance mismatch')
    wanted=expected['cases']
    found=actual['cases']
    if not isinstance(found,list): raise ValueError('cases must be list')
    names=[case['id'] for case in found]
    if len(names)!=len(set(names)) or set(names)!=set(wanted): raise ValueError('case set mismatch')
    for case in found:
        if set(case)!={'id','observed'}: raise ValueError('case fields')
        if not typed_equal(case['observed'],wanted[case['id']]): raise ValueError('case mismatch: '+case['id'])
    return dict(claim=actual['claim'],status='PASS',cases=len(found),
                provenance='NEW_CLEAN_AUTHOR_EXECUTION')
if __name__=='__main__':
    try: print(json.dumps(compare(load(sys.argv[1]),load(sys.argv[2])),sort_keys=True))
    except Exception as error:
        print(json.dumps(dict(status='FAIL',error=str(error)),sort_keys=True));sys.exit(4)
