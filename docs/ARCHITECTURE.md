<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Architecture and trust boundary

Source A (Yard-1..3) and Source B (Dispatch-1/2) submit synthetic payloads through
source-token authentication, source-specific adapters and canonical JSON hashing.
The API stores RECEIVED before endorsement; COMMITTED follows a confirmed valid
Fabric commit. A provably unsubmitted injected fault is UNKNOWN. Application-level
timeouts/finalize failures do not imply that a valid ledger write did not occur.
The 1.2 chaincode checks MSP, OU=client, enrollment and the writer attribute, and
stores immutable envelopes. TLS authenticates synthetic peers and orderer.

Target T's Web consumer keeps its 1.1 envelope contract. PG is the durable read
model; Redis is only a disposable checkpoint. Valid block transactions/events drive
projection; invalid MVCC transactions never become committed evidence. Query ranges
are bounded at 500 items and 4 MiB. The target peer is the authority when checking
record metadata, references and canonical bytes; coordinated PG tampering is not
accepted as evidence. Raw bytes are withheld on MISMATCH or UNAVAILABLE.

HTTP interface: API `POST /submit`, `X-Source`, bearer token and JSON payload; Web
`GET /records/<24-hex-id>/{detail,integrity,raw}` with a synthetic session bearer.
Responses distinguish authentication/authorization denial and service unavailable.
`/health` and token-protected `/test-control` exist solely within the isolated test
container. API/Web loopback ports 8080/8081 are not host-published. Test sessions
are issued directly by the harness into its new database; no production login,
browser UI, cookie/CSRF integration or user lifecycle completeness is claimed.

Protected raw/integrity disclosure requires a durable ALLOW audit write; an audit
write failure yields 503. Detail authorization does not claim that same hard audit
dependency. Revocation is checked against the database, not a bearer cache.

Threat scope includes unauthorized writers, cross-source binding, malformed
envelopes, altered PG payload/hash/ref/index, unavailable peer/audit, replay/gaps,
uncertain submission state and targeted child-process restart. It does not establish
resistance to a compromised host, root, CA/MSP administrator, malicious dependency,
consensus collusion, real network partitions or production availability.

No operating wallet, data, Git history or source bytes are reused. The names are
logical aliases, not a public institution mapping. Reference-only dependency
licenses remain upstream; isolated execution is not binary redistribution approval.
