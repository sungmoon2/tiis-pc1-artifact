<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Workflow status and evidence boundaries

Status: UNEXECUTED_G4_SCAFFOLDING. These workflows have not been executed, and
no runner has been registered by this artifact. They do not establish C8.

reproduce-c1-c4 uses workflow_dispatch only, a protected environment, and labels
self-hosted/linux/x64/tiis-ephemeral. Provision a one-run disposable Ubuntu 24.04
VM with at least 4 vCPU, MemAvailable >4 GiB and free disk >20 GiB. Keep the
runner exclusive to the selected commit and destroy both runner registration and
VM after the run, including cancellation or setup failure. The standard public
ubuntu-24.04 GitHub-hosted runner is not claimed to support this full workflow.

Provision the component bundle before the run and set TIIS_RC_INPUT_BUNDLE in
the isolated runner environment. Protected variables bind source commit/tree,
controller commit/ref/file SHA-256, repository identity and component bundle hash.
The manual workflow must execute from that exact immutable source revision.
No trigger accepts pull requests, pull_request_target events or automatic pushes.

Raw command output stays in the disposable runner's private directory. Only a
successful stage-evidence output or a constant DIAGNOSTIC.json can be uploaded.
Native Actions logs and deployment metadata are not collected as artifacts.
A separate local/private auditor may retain every attempt under restricted access;
its code, raw archive and credentials must remain outside public repositories.

isolated-attester is a manual, protected, fail-closed placeholder with no write
permissions or attestation step. A future implementation needs a separate review:
public attestations persist in a public transparency log. Only a sanitized final
release manifest or public bundle may be a subject. Private audit ZIPs, native logs
and unpublished manuscript bytes are forbidden subjects. No attestation or C8
completion is produced by this placeholder.
