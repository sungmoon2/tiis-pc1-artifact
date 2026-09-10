# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
import errno,importlib.machinery,importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('runner',str(ROOT/'artifact'))
spec=importlib.util.spec_from_loader(loader.name,loader);runner=importlib.util.module_from_spec(spec);loader.exec_module(runner)
class RunnerTests(unittest.TestCase):
    def test_exec_capable_output_and_exact_probe_cleanup(self):
        with tempfile.TemporaryDirectory(prefix='tiis-pc1-test-',dir='/var/tmp') as d:
            output=Path(d);(output/'private').mkdir()
            sentinel=output/'.tiis-exec-probe-unrelated';sentinel.write_text('keep')
            receipt=runner.preflight_output(output)
            self.assertEqual(receipt['status'],'PASS')
            self.assertEqual(receipt['mount']['exit_code'],0)
            self.assertEqual(receipt['direct_exec']['argv'],[receipt['probe']])
            self.assertEqual(receipt['direct_exec']['exit_code'],0)
            self.assertEqual(receipt['probe_cleanup'],'PASS')
            self.assertFalse(Path(receipt['probe']).exists())
            self.assertEqual(sentinel.read_text(),'keep')
    def test_exec_denied_stops_reproduce_before_setup_work(self):
        # Deterministic EACCES injection; this is not a real noexec mount test.
        real_run=subprocess.run
        seen=[]
        def deny_probe(argv,**kwargs):
            seen.append(argv)
            if Path(argv[0]).name.startswith('.tiis-exec-probe-'):
                self.assertTrue(Path(argv[0]).stat().st_mode & 0o100)
                raise PermissionError(errno.EACCES,'injected execution denial',argv[0])
            self.assertEqual(argv[0],'findmnt')
            return real_run(argv,**kwargs)
        with tempfile.TemporaryDirectory(prefix='tiis-pc1-test-',dir='/var/tmp') as d:
            output=Path(d)/'private-run'
            with patch.object(runner.subprocess,'run',side_effect=deny_probe),patch.object(runner,'doctor') as doctor,patch.object(runner,'verify') as verify,patch.object(sys,'argv',['artifact','reproduce','--output',str(output)]):
                self.assertEqual(runner.main(),4)
                doctor.assert_not_called();verify.assert_not_called()
            receipt=json.loads((output/'private/OUTPUT_PREFLIGHT.json').read_text())
            self.assertEqual(receipt['status'],'FAIL')
            self.assertEqual(receipt['errno'],errno.EACCES)
            self.assertEqual(receipt['probe_cleanup'],'PASS')
            self.assertFalse(Path(receipt['probe']).exists())
            self.assertEqual(len(seen),2)
            self.assertFalse((output/'runtime').exists())
            self.assertEqual(json.loads((output/'evidence/RUN_RESULT.json').read_text())['overall'],'FAIL')
    def test_nonzero_exec_is_rejected(self):
        real_command=runner.command
        def nonzero(argv,**kwargs):
            if Path(argv[0]).name.startswith('.tiis-exec-probe-'):
                return dict(argv=list(map(str,argv)),exit_code=7,stdout='',stderr='injected exit 7')
            return real_command(argv,**kwargs)
        with tempfile.TemporaryDirectory(prefix='tiis-pc1-test-',dir='/var/tmp') as d:
            output=Path(d);(output/'private').mkdir()
            with patch.object(runner,'command',side_effect=nonzero):
                with self.assertRaisesRegex(RuntimeError,'NEW private path'):runner.preflight_output(output)
            receipt=json.loads((output/'private/OUTPUT_PREFLIGHT.json').read_text())
            self.assertEqual(receipt['direct_exec']['exit_code'],7)
            self.assertEqual(receipt['status'],'FAIL')
            self.assertFalse(Path(receipt['probe']).exists())
    def failure(self,root):
        output=root/'run'
        with patch.object(runner,'doctor',side_effect=RuntimeError('injected doctor failure')),patch.object(sys,'argv',['artifact','reproduce','--output',str(output)]):
            self.assertEqual(runner.main(),4)
        self.assertEqual(json.loads((output/'STATE.private.json').read_text())['phases'],
          {'setup':'FAIL','collect':'PASS','stop':'PASS','install_cleanup':'PASS'})
        self.assertEqual(runner.stage(output/'evidence',root/'upload')['overall'],'FAIL')
        return output
    def test_failure_finalization_and_staging(self):
        with tempfile.TemporaryDirectory() as d:self.failure(Path(d))
    def test_missing_extra_mutated_readback_and_secret_reject(self):
        from staging import verify_export
        mutations=['missing','extra','mutated','readback','empty']
        for mutation in mutations:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                output=self.failure(Path(d));evidence=output/'evidence'
                if mutation=='missing':(evidence/'FINALIZATION.json').rename(output/'saved.json')
                if mutation=='extra':(evidence/'EXTRA').write_text('extra')
                if mutation=='mutated':(evidence/'RUN_RESULT.json').write_text('{}')
                if mutation=='readback':
                    p=output/'READBACK.json';value=json.loads(p.read_text());value['files'][-1]=value['files'][0];p.write_text(json.dumps(value))
                if mutation=='empty':evidence=Path(d)/'empty';evidence.mkdir()
                with self.assertRaises(ValueError):verify_export(evidence)
    def test_redaction(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);runtime=root/'runtime';runtime.mkdir()
            (runtime/'database-password').write_text('unit-secret-value')
            value=runner.redact(str(root)+' unit-secret-value 172.19.0.4',runtime,root)
            self.assertNotIn('unit-secret-value',value);self.assertNotIn(str(root),value)
            with self.assertRaises(ValueError):runner.redact('-----BEGIN PRIVATE KEY-----',runtime,root)
    def test_global_inventory_is_hashed_not_exported(self):
        from staging import check_private_inventory
        source=[{'argv':['docker','volume','ls','-q'],'stdout':'private-volume-unit\n','exit_code':0}]
        with self.assertRaises(ValueError):check_private_inventory(source)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);clean=runner.redact(json.dumps(source),root,root)
            self.assertNotIn('private-volume-unit',clean)
            value=json.loads(clean);check_private_inventory(value)
            self.assertEqual(value[0]['stdout_line_count'],1)
if __name__=='__main__':unittest.main()
