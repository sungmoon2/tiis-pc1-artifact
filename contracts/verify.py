#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sungmoon Park
# SPDX-License-Identifier: Apache-2.0
"""Independent structural writer/consumer contract verifier."""
import hashlib,json,sys
from pathlib import Path
base=Path(sys.argv[1]).resolve()
raw={name:(base/('tiis-pc1-'+name)/'contracts/integration-contract.json').read_bytes()
     for name in ['api','web','chaincode','network']}
assert raw['api']==raw['chaincode']==raw['network']
writer=json.loads(raw['api']);consumer=json.loads(raw['web'])
assert writer['contractId']=='tiis-clean-integration/1.2.0'
assert consumer['contractId']=='tiis-clean-integration/1.1.0'
assert writer['envelope']==consumer['envelope']
assert writer['ledgerSchemaVersion']==consumer['ledgerSchemaVersion']
assert writer['chaincodeFunction']==consumer['chaincodeFunction']
assert writer['historicalCompatibility']==consumer['historicalCompatibility']
assert 'query' not in consumer
for name,source in writer['sources'].items():
    common=dict(source);del common['writerEnrollmentId']
    assert common==consumer['sources'][name]
common=dict(writer['fabricPrincipal'])
del common['writerAttribute'];del common['writerEnrollmentIdAttribute']
assert common==consumer['fabricPrincipal']
print(json.dumps(dict(status='PASS',scope='NEW_GENERIC_DUAL_CONTRACT_STRUCTURE_NOT_PRIVATE_BYTE_IDENTITY',
      hashes={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()}),indent=2))
