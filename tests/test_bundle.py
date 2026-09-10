# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
import copy,io,os,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'release'))
from bundle import pack,verify,members,tree_identity,unique_json
class BundleTests(unittest.TestCase):
    def test_roundtrip_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);template=base/'empty-template';template.mkdir()
            env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
              'GIT_AUTHOR_NAME':'Sungmoon Park','GIT_AUTHOR_EMAIL':'qkrtjdans4145@gmail.com',
              'GIT_COMMITTER_NAME':'Sungmoon Park','GIT_COMMITTER_EMAIL':'qkrtjdans4145@gmail.com'}
            for name in ['api','web','chaincode','network']:
                repo=base/('tiis-pc1-'+name);repo.mkdir()
                (repo/'src').mkdir();(repo/'src/example.txt').write_text('owned synthetic test data\n')
                (repo/'README.md').write_text('synthetic '+name+'\n')
                for args in [['init','--initial-branch=main','--template='+str(template)],
                             ['add','.'],['-c','commit.gpgsign=false','commit','-m','Owned test fixture']]:
                    subprocess.run(['git','-C',str(repo),*args],env=env,check=True,capture_output=True)
            lock=pack(base,base/'bundle');bundle=base/'bundle'/lock['bundle']['filename']
            self.assertEqual(verify(bundle,lock,base/'extracted')['components'],4)
            altered=copy.deepcopy(lock);altered['bundle']['sha256']='0'*64
            with self.assertRaises(ValueError):verify(bundle,altered)
            altered=copy.deepcopy(lock);altered['components'][0]['tree']='0'*40
            with self.assertRaises(ValueError):verify(bundle,altered)
            altered=copy.deepcopy(lock);altered['components'].pop()
            with self.assertRaises(ValueError):verify(bundle,altered)
    def test_unsafe_archive(self):
        for name,kind in [('../escape',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w') as tar:
                entry=tarfile.TarInfo(name);entry.type=kind;entry.linkname='/outside';tar.addfile(entry)
            with self.assertRaises(ValueError):members(stream.getvalue())
    def test_duplicate_json(self):
        with self.assertRaises(ValueError):unique_json('{"x":1,"x":2}')
if __name__=='__main__':unittest.main()
