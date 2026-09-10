<!-- SPDX-FileCopyrightText: 2026 Sungmoon Park -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Separate SoftwareX successor

This TIIS derivative preserves the 1.2 writer and 1.1 consumer contract boundary.
Contract consolidation, payload migration and new evaluation claims belong to a
separate SoftwareX successor. No integration change is made in this artifact.

A successor must identify the four component commits, trees and source archive
hashes plus the umbrella commit, document changed behavior and rerun compatibility
and affected claim tests. Historical PC1 evidence remains separately preserved.

Manuscript binding is one-way: freeze source commits and component pins first;
then insert those URLs and commits into the manuscript; finally freeze manuscript
files. Record final manuscript hashes in a separate future release asset or private
receipt. Source commits contain neither their own commit ID nor future manuscript
hashes. No completed manuscript-binding asset is provided here.
