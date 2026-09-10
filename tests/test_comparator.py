# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
import copy,json,tempfile,unittest
from pathlib import Path
from compare import compare,load
class ComparatorTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(compare(self.expected(),self.actual())['status'],'PASS')
    def expected(self): return dict(claim='C1',cases={'a':{'writes':0}})
    def actual(self): return dict(claim='C1',provenance='NEW_CLEAN_AUTHOR_EXECUTION',
                                 cases=[dict(id='a',observed={'writes':0})])
    def test_negative_mutations(self):
        a=self.actual()
        mutations=[{**a,'claim':'C2'},{**a,'provenance':'HISTORICAL_PC1'},
          {**a,'cases':[]},{**a,'cases':a['cases']*2},{**a,'extra':True},
          {**a,'cases':[dict(id='unknown',observed={'writes':0})]},
          {**a,'cases':[dict(id='a',observed={'writes':1})]},
          {**a,'cases':[dict(id='a',observed={'writes':False})]},
          {**a,'cases':[dict(id='a',observed={'writes':0.0})]},
          {**a,'cases':[dict(id='a',observed={'writes':0},status='PASS')]}]
        for mutation in mutations:
            with self.assertRaises(ValueError): compare(self.expected(),mutation)
    def test_parser_rejects_ambiguous_input(self):
        for raw in ['{"a":1,"a":2}','{"a":NaN}','{','{"a":Infinity}']:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'x.json';p.write_text(raw)
                with self.assertRaises((ValueError,json.JSONDecodeError)):load(p)
if __name__=='__main__':unittest.main()
