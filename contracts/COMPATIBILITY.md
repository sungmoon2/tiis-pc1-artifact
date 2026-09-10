<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Dual-version contract boundary

Historical API/Network contract1.2 SHA256:
5218bff6ac0a10324d66e3bf84b69b8d5762b6542f81e986036212f72890b580
Historical Web contract1.1 SHA256:
36e3ff97ef373c0f4a92c8110aa88da63611b8f0179832dd19e2898fef900e9a

The three clean writer-side contract copies retain the1.2 version line. The
Web consumer retains1.1 and does not acquire writer enrollment/attribute or query
policy fields by silent schema unification. Common-envelope definitions agree.

New generic Source A(jobKey,operation) and Source B(plan.key,plan.operation)
fixture schemas are independently specified. Clean namespace, field vocabulary,
storage-reference table name and identifiers differ from private originals.
This is a behavioral derivative, not byte-identical historical code or payload.
Rights are addressed by excluding original materials and creating new generic
code/data, not by alias replacement alone.

Required G2 vectors: writer attribute absent/wrong; wrong enrollment; wrong MSP;
admin/generic client and read-only indexer; two dedicated writers;1.1 consumer
accepts common evidence from1.2 writers; hash/ref/metadata disagreement; missing
index ref despite verified peer scope; query limits and overflow; unsupported
versions rejected; raw/integrity ALLOW failure versus detail no-required-ALLOW.
Four named new omission fields are not claimed as reconstructed historical fields.

No new runtime compatibility is measured by this specification alone.
SoftwareX contract integration remains a separate future successor.
