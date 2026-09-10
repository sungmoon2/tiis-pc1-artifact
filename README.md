<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# tiis-pc1-artifact

Synthetic clean research artifact for TIIS PC1. It contains newly authored generic
code and synthetic fixtures. Historical PC1 source and operating systems are excluded. C8 independent reproduction is
pending; a successful execution below is only an author self-test. C5/C6 are not
required by this runner; historical C6 used Dispatch-1 only. C7 remains incomplete.

## Inputs and environment

Use this umbrella's full immutable commit archive and the exact component bundle
named in `components.lock.json`. No Git remote, tag or GitHub token is required.
Four component archives are nested in that bundle. The runner verifies bytes,
SHA-256, inner manifest/checksums, full Git tree and commit archive metadata before
any application is executed. Never run from a production checkout.

Required: a disposable Ubuntu 24.04 x86_64 VM, 4 vCPU, at least 4608 MiB RAM, more than 20 GiB
free disk, Docker 29.1.5, Compose 5.0.2, Python 3.12, Git, OpenSSL and zstd 1.5.5.
The VM must report more than 4 GiB available before starting; a non-VM host requires
more than 9 GiB available and retains a 5 GiB reserve. Docker must expose cgroup v2
memory/swap/CPU controls. Internet access is required only to fetch pinned public
images and npm packages. No privileged application containers or host Docker
socket mounts are used. Runtime packages are not included in the source bundle.

For a newly created VM only, place the literal `tiis-disposable-vm-v1` in
`/etc/tiis-disposable-vm`, then run `sudo python3 environment/bootstrap-fresh-vm`.
That guarded helper refuses non-VM hosts and preexisting Docker installations.
It installs signed-distribution prerequisites inside that VM, verifies downloaded
Docker/Compose bytes using `environment/guest-tools.lock.json`, and starts a new
VM-local Docker daemon. Subsequent commands may run as root inside that disposable
VM. This is not permission to install or alter Docker on an existing machine.

## Complete local execution

From the extracted umbrella directory, use new private runtime and separate
publishable staging paths outside it. The runtime filesystem must permit direct
execution; use a unique `/var/tmp/tiis-pc1-<run-id>` or a caller-selected, verified
exec-capable ordinary filesystem path. A mode bit or `test -x` is insufficient.
`setup` records `findmnt -T` (target/source/filesystem/options) and directly executes
a temporary shell executable under the output root before Docker checks, image
pulls or network startup. A failure stops setup with a corrective message. Only
the exact probe file is removed; the private receipt is retained.

Example (generate a new run ID for every invocation):

```sh
unset GH_TOKEN GITHUB_TOKEN
run_id=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
private_output="/var/tmp/tiis-pc1-${run_id}"
publishable_output="/var/tmp/tiis-pc1-${run_id}-publishable"
python3 artifact doctor
python3 artifact verify-rc-input-bundle --bundle /input/component-bundle.tar.zst
python3 artifact reproduce --bundle /input/component-bundle.tar.zst --output "$private_output"
python3 artifact stage-evidence --input "${private_output}/evidence" --publishable-output "$publishable_output"
```

Replace the bundle path with your exact local path. The output paths must be new
and separate; never use a source directory as an output directory. Exit 0 from
`reproduce` requires setup, start, test, pre-teardown collection, scoped teardown,
and installation-container cleanup. It always attempts collection and teardown
after a failure. A failed run remains FAIL even if its package is well formed.
`READBACK.json` is outside `evidence/` to avoid a self-hash cycle; stage-evidence
requires it and performs another exact-set byte/hash check before copying.
Keep the runtime directory private. Only evidence that passes stage-evidence
and direct readback is eligible for distribution.

Equivalent diagnostic sequence, each once per new output directory:

```sh
run_id=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
private_output="/var/tmp/tiis-pc1-${run_id}"
python3 artifact setup --bundle /input/component-bundle.tar.zst --output "$private_output"
python3 artifact start --output "$private_output"
python3 artifact test --output "$private_output" --claims C1,C2,C3,C4
python3 artifact collect-evidence --output "$private_output" --phase pre-teardown
python3 artifact stop --output "$private_output"
python3 artifact finalize-evidence --output "$private_output"
```

After a failed phase, still run the remaining collection/stop/finalization steps.
Do not invoke host-wide prune, remove unrelated containers or reuse a run directory.
The runtime holds new synthetic private keys and random test tokens: keep it private.

## What is tested

C1: 15 valid submissions, 12 new four-class omissions, 5 policy denials, 2 allows.
C2: 14 cases (30 correctness repetitions in one case, 12 tamper trials and one
peer-unavailable case). C3: 9 actual HTTP authorization cases. C4: 36 declared
read-model/recovery cases. Audit-failure, revocation, HTTP submission and one Web
SIGKILL process restart are separately named regressions, not count inflation.
The expected files are strict case contracts, never substitutions for raw results.
The collector also checks actual SQL block/transaction/index foreign-key populations
against authoritative ledger results before and after HTTP/process regressions.

Run offline tooling checks with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest
discover -s tests -p 'test_*.py' -v`, `node --test tests/unit.cjs`,
`python3 canonicalization/verify.py ../`, and `python3 contracts/verify.py ../`.
The last two require the four sibling component directories (or extracted bundle).

See `docs/G3_HANDOFF.md` for the separate Windows review and two-VM G3 gate.
See `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`, `paper/PUBLIC_PAPER_SCOPE.json`, LICENSE,
NOTICE and THIRD_PARTY_NOTICES.md. See docs/WORKFLOWS.md for
UNEXECUTED_G4_SCAFFOLDING and one-run disposable self-hosted runner requirements.
The intended repository-code URLs in CITATION.cff do not assert repository or
published release availability. C8 independent reproduction remains pending.
