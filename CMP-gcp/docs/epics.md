---
status: draft
stepsCompleted: [requirements-inventory, epic-list, stories]
inputDocuments: [prd.md, architecture.md, ../../docs/plans/gcp/tasks.md]
---

# CMP-gcp — Epic Breakdown (local dev & debug)

BMAD v6.12.4 `bmad-create-epics-and-stories` shape. One story = one `GCP-L*` task; acceptance mirrors [tasks.md](../../docs/plans/gcp/tasks.md#local), and the stories add Given/When/Then, files and tests. Cloud (`GCP-C*`) belongs to [`../deploy/`](../deploy/README.md).

## Global Constraints (every story)
- No hardcoded scalars, no env defaults, fail fast ([NFR-1, NFR-2](prd.md#5-cross-cutting-nfrs); [AGENTS.md](../AGENTS.md#policy)).
- Secrets only in `config/.env.secrets` / Bitwarden `bw`. The local profile needs none.
- Reuse before create; 127.0.0.1 only; never `down -v` or prune ([AD-7](architecture.md#ad-7--reuse-before-create-localhost-only)).
- Ponytail: the smallest complete change; reuse the `CMP-dbx-fe` patterns; each story's **Never** list names what to skip.
- TDD: write the failing test first; expected values come from `reference.py` / FX.
- Done = verification command run and output quoted in the Dev Agent Record (superpowers `verification-before-completion`).
- No git push or PR without user confirmation; work on a `feat/` branch.

## FR Coverage Map
| FR | Story | GCP task |
|---|---|---|
| FR-1 | [1.1](stories/1.1.story.md) | [L01](../../docs/plans/gcp/tasks.md#gcp-l01) |
| FR-2 | [1.2](stories/1.2.story.md) | [L02](../../docs/plans/gcp/tasks.md#gcp-l02) |
| FR-3 | [1.3](stories/1.3.story.md) | [L03](../../docs/plans/gcp/tasks.md#gcp-l03) |
| FR-4 | [2.1](stories/2.1.story.md) | [L04](../../docs/plans/gcp/tasks.md#gcp-l04) |
| FR-5 | [2.2](stories/2.2.story.md) | [L05](../../docs/plans/gcp/tasks.md#gcp-l05) |
| FR-6 | [2.3](stories/2.3.story.md) | [L06](../../docs/plans/gcp/tasks.md#gcp-l06) |
| FR-7 | [3.1](stories/3.1.story.md) | [L07](../../docs/plans/gcp/tasks.md#gcp-l07) |
| FR-8 | [3.2](stories/3.2.story.md) | [L08](../../docs/plans/gcp/tasks.md#gcp-l08) |
| FR-9 | [3.3](stories/3.3.story.md) | [L12](../../docs/plans/gcp/tasks.md#gcp-l12) |
| FR-10 | [4.1](stories/4.1.story.md) | [L09](../../docs/plans/gcp/tasks.md#gcp-l09) |
| FR-11 | [4.2](stories/4.2.story.md) | [L10](../../docs/plans/gcp/tasks.md#gcp-l10) |
| FR-12 | [4.3](stories/4.3.story.md) | [L11](../../docs/plans/gcp/tasks.md#gcp-l11) |
| FR-13 | [4.4](stories/4.4.story.md) | [L13](../../docs/plans/gcp/tasks.md#gcp-l13) |

## Epic List
1. **Foundation** — discovery, strict settings, core port + producer. Output: offline `just test` green.
2. **Emulators & SQL path** — Pub/Sub + BigQuery emulators, SQL templates, shim. Output: FX on `trades_1m`.
3. **Beam path** — pipeline, TestStream suite, debug tooling. Output: FX on `trades_1m_beam`; cases 1–6 green.
4. **Verification & hardening** — E2E, faults, live smoke, CI. Output: `just it` + `just fault-all` PASS.

Build order: 1.1 → 1.2 → 1.3 → (2.1 → 2.2 → 2.3) ∥ (3.1 ⇄ 3.2) → 4.1 → 4.2, 4.3, 3.3 → 4.4. Stories 3.1 and 3.2 go TDD together: write the 3.2 case 1 test first.

Backlog (no story files): [L14 DuckDB](../../docs/plans/gcp/tasks.md#gcp-l14), [L15 Prism](../../docs/plans/gcp/tasks.md#gcp-l15).
