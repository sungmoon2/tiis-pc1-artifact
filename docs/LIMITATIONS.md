<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Claim and trust boundaries

This is a newly authored generic derivative. It does not contain or represent
the actual operating institutions, original payload schemas, credentials,
deployment endpoints, evaluation corpus or private Git history.

Historical PC1 observations are not test outputs of this implementation.
C6's historical evaluation scope was Dispatch-1 only. C5/C6 remain optional;
C7 and C8 remain incomplete. Author-assisted execution is not independent C8.

The source preserves a declared 1.2 writer / 1.1 consumer compatibility line.
Public contract bytes and generic payload fields are intentionally new.
SoftwareX unification or migration belongs in a separate successor; no silent
contract unification is permitted here.

Development service-method tests are not automatically HTTP route tests,
fresh-VM reproduction, physical outage tests or process-kill tests. Each raw
receipt names what actually ran. In-process recreation is not process restart.
Application-injected audit/finalization/timeout faults are not physical outages.
Historical absolute ledger height is not a target for synthetic tests.
Historical terminal counters lacking their population/join/predicate definitions
remain report-only; new explicit SQL assertions must be labeled separately.

The generic canonicalizer accepts JSON-domain values, sorts object keys by
UTF-16 code units, omits undefined object properties, treats undefined array
values as null, and rejects cycles/nonfinite/non-JSON objects. Date/custom
object rejection is a declared input-domain hardening, not demonstrated
parity with every possible non-JSON JavaScript object in the private source.
The new generic adapter also rejects a vertical-bar character in business
identifiers to keep the declared concatenation domain unambiguous. Historical
behavior outside these explicitly selected synthetic domains is not claimed.

No repository is production-ready or endorsed by any institution. Source
Apache-2.0 coverage does not relicense upstream dependency code or image layers.
Runtime dependency references do not authorize bundling those binaries.
The get-params 0.1.2 upstream package contains an explicit MIT/copyright
declaration but not a publisher-specific full permission text; its original
declaration is retained and package-code redistribution is not cleared.

GitHub workflows are UNEXECUTED_G4_SCAFFOLDING. No GitHub-hosted run or public
attestation is claimed. Reproduction requires a one-run disposable Ubuntu 24.04
VM with at least 4 vCPU, MemAvailable >4 GiB and free disk >20 GiB. The standard
ubuntu-24.04 GitHub-hosted runner is not a supported full reproduction environment.
Runner registration and disposal are managed outside these source repositories.
