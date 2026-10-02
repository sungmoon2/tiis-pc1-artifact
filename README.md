<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# tiis-pc1-artifact

This repository provides a Hyperledger Fabric prototype for integrating
heterogeneous records, verifying payload integrity, controlling access, and
recovering an off-chain read model. It includes synthetic test data and a test
suite for admission, integrity, protected reads, and recovery.

## Download and get started

Use the [v0.1.1 release package](https://github.com/sungmoon2/tiis-pc1-artifact/releases/download/v0.1.1/TIIS_PC1_CORRECTED_RC_0.1.1_20260910T150052Z.zip)
for reproduction. It contains the runner and all four pinned component source
archives, together with their input bundle. GitHub's automatically generated
Source code ZIP contains the umbrella repository alone.

- File: `TIIS_PC1_CORRECTED_RC_0.1.1_20260910T150052Z.zip`
- Size: 549,494 bytes
- SHA-256: `4f3a1f9a3e15e9e8feb76d175a2ea7fc2b7152b0dde11771f046923ac1b0e999`

Extract the ZIP into a new directory and follow its top-level README to verify
`SHA256SUMS.txt` and extract `tiis-pc1-artifact.tar.gz`. Run the commands below
from that extracted artifact directory, using the enclosed
`tiis-pc1-rc-inputs-f8bea99b1ad0ee9363f8272b3aee833f03f710c5b682514c9fea9e4a520524de.tar.zst`
as the component bundle. The `/input/component-bundle.tar.zst` path in the examples
is a placeholder for this file's actual location. The release package fixes the
source versions used in the reported public-artifact runs.

## Relation to the manuscript

The manuscript *A Hyperledger Fabric Prototype for Heterogeneous Evidence
Integration, Scoped Verification, and Read-Model Recovery* describes the system
design and evaluation. This release is a separately implemented generic
derivative with synthetic inputs. The historical evaluation, supplementary
recovery and payload-absence checks, and instrumented latency pilot used the
archived implementation; their source and records are outside this release.

The authors ran v0.1.1 on two fresh virtual machines. Both runs passed all
98 checks: 34 admission, 14 integrity, nine protected-read, 36 functional/recovery,
and five transport/session/audit/restart checks. External-partner validation
(C7) and independent third-party reproduction (C8) remain future work.

The execution screenshots in Fig. 5 show summaries from a later run of this
release. The local display commands `pc1-execution` and `pc1-payload-check`
read saved results; `pc1-execution` also queries running services. Reproduce
the tests with the `python3 artifact` commands below.

## Inputs and environment

Use the source archive and component bundle from the release package.
`components.lock.json` identifies the exact bundle; no GitHub token is required.
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
VM. Run this helper only inside that new VM.

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
after a failure. Collection and cleanup do not change a failed test result.
`stage-evidence` checks the collected files against the run's `READBACK.json`
before copying them to the separate staging directory.
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

The runner executes C1-C4 and the named regression checks. C5/C6 are supporting
evaluations in the manuscript and are outside this release's runnable evaluation.

C1: 15 valid submissions, 12 new four-class omissions, 5 policy denials, 2 allows.
C2: 14 cases (30 correctness repetitions in one case, 12 tamper trials and one
peer-unavailable case). C3: 9 actual HTTP authorization cases. C4: 36 declared
read-model/recovery cases. Audit-failure, revocation, HTTP submission and one Web
SIGKILL process restart are recorded as separate regression checks.
Expected files define the case contracts; the runner compares them with collected results.
The collector also checks actual SQL block/transaction/index foreign-key populations
against authoritative ledger results before and after HTTP/process regressions.

Run offline tooling checks with `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest
discover -s tests -p 'test_*.py' -v`, `node --test tests/unit.cjs`,
`python3 canonicalization/verify.py ../`, and `python3 contracts/verify.py ../`.
The last two require the four sibling component directories (or extracted bundle).

## Further documentation

- [Architecture and interfaces](docs/ARCHITECTURE.md)
- [Evaluation scope and limitations](docs/LIMITATIONS.md)
- [Security and handling of runtime data](SECURITY.md)
- [License](LICENSE), [notice](NOTICE), and [third-party notices](THIRD_PARTY_NOTICES.md)
- [Software citation](CITATION.cff)

The [release notes](https://github.com/sungmoon2/tiis-pc1-artifact/releases/tag/v0.1.1)
record the two-VM verification and the earlier `artifact_version: 0.1.0` value
retained in the release's scope metadata. The release itself is v0.1.1.

`docs/G3_HANDOFF.md` records the release-preparation procedure that preceded the
two-VM results. The GitHub Actions workflows have not been run; their setup
requirements are described in [docs/WORKFLOWS.md](docs/WORKFLOWS.md). Local
reproduction follows the commands above.
