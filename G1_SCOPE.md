<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Source and reproduction scope

Apache-2.0 applies only to newly authored clean source owned by Sungmoon Park.
Original third-party copyright, license and NOTICE obligations remain applicable.
Private operational source, institution-specific mappings, payloads, credentials,
rights-unclear originals and historical Git history were excluded from redistribution.
This repository contains newly authored generic synthetic code.

Source A fixtures use jobKey and operation; Source B uses plan.key and
plan.operation. Synthetic counters and arrays exercise four declared omission
classes. Operations are Yard-1 through Yard-3 and Dispatch-1/Dispatch-2, with
Target T as the logical target. These schemas are not renamed operating payloads.

API and chaincode/network preserve the 1.2 writer contract; Web preserves the
1.1 consumer contract. Canonicalization, hash/reference checks, access decisions,
audit failure and ordered projection recovery are covered by the test core.
Historical PC1 results and new clean author self-tests have separate provenance.
C1–C4 are the reproduction core; C5/C6 are optional; C7/C8 remain incomplete.
Historical C6 covered Dispatch-1 only. A successful author run is not independent C8.

Image layers, npm packages, node_modules, VM images and tool binaries are external
runtime dependencies and are not included in source archives or the input bundle.
Preserved upstream license texts and their file-level register are included.
Generated synthetic credentials remain in a fresh private runtime directory.
The runner requires unused names, scoped resource ownership, no published ports
and bounded memory/CPU/PID resources. No institution endorsement or production
suitability is claimed. Contract integration belongs to the SoftwareX successor.
