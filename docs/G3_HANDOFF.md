<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# RC 0.1.1 runtime-path handoff

The runtime-path correction and an author run do not establish G3 or C8.
Windows must first review the candidate diff, privacy and immutable identities.
Then use the exact same approved RC ZIP bytes in fresh VM A and a completely
new VM B. Do not reuse runtime output, VM disks or snapshots between runs.

Verify the supplied RC decimal bytes/SHA-256, ZIP CRC, safe unique paths,
manifest/checksums, source archive commit/tree identities and component bundle.
Use the disposable VM prerequisites and guarded bootstrap in ../README.md.
No physical-host Docker or Docker socket mount is authorized.

In each guest, extract the approved umbrella and bundle into new source/input
directories. From the umbrella directory run the README sequence with a unique
private output `/var/tmp/tiis-pc1-<run-id>` on an exec-capable ordinary filesystem.
Use a separate new `/var/tmp/tiis-pc1-<run-id>-publishable` for staging. A caller
may choose different new paths with the same semantics.

`setup` must retain `private/OUTPUT_PREFLIGHT.json`: the `findmnt -T` result,
target/source/filesystem/options, direct shell-executable result and exact probe
cleanup. A mode bit or `test -x` alone is insufficient. On denial, preserve the
failure and select a new exec-capable output root; do not alter mount options or
add a Docker socket. The preflight runs before Docker checks, pull or startup.

Retain actual/expected and raw cases separately for C1 34, C2 14, C3 actual HTTP 9
and C4 36. Report transport, audit, revocation and process regressions separately.
Verify chaincode install, SQL/ledger populations, writer 1.2 to consumer 1.1,
staging/readback and owned-resource teardown in each run. Preserve private raw
logs and actual path mappings separately from the public candidate and staged
synthetic evidence. A failed run remains failed even after successful cleanup.

Only the separately reviewed full results from both VMs can resolve the prior
G3 failure. GitHub writes, publication and C8 require their own subsequent gates.
