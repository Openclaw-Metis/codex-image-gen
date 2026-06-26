# Readiness report

This file is release evidence for the current skill version.
It records mechanical gate results and must be updated whenever `SKILL.md`, scripts, references, or eval assets change.

## Final gate
- Current version reviewed: 2026.6.26
- Overall status: PASS (draft stage gate)
- Blocking issues:
  - None at draft stage.
- Evidence / commands run:
  - format_check.py: PASS
  - audit_structure.py --json: PASS
  - audit_workflow_contract.py --json: PASS
  - audit_semantics.py --json: PASS
  - audit_eval_coverage.py --json: PASS (tags should-trigger/should-not-trigger/near-miss/happy-path/edge-case/failure-mode/overlap-neighbor; languages zh/en/mixed)
  - audit_eval_quality.py --json: PASS
  - audit_skill_references.py --json: PASS
  - audit_unreferenced_files.py --json: PASS
  - gate_language: PASS
  - scripts/codex_image.py verify/locate exercised against a real Codex-generated 9:16 image
  - stage_gate.py --stage create --json: PASS
  - release_gate.py --stage draft --json: PASS
- Audit date: 2026-06-26
- Git commit: local-only
- Audit runner: local (skill-creator-advanced toolchain)

## Format checks
- [ ] Folder name is kebab-case
- [ ] `SKILL.md` exists (case-sensitive)
- [ ] YAML frontmatter starts/ends with `---`
- [ ] Frontmatter has `name` + `description`
- [ ] No `<` or `>` in frontmatter
- [ ] `references/readiness_report.md` is present and updated for this review
- [ ] `scripts/`, `references/`, and `assets/` have no unexplained unreferenced files
- [ ] No `README.md` inside the skill folder

## Structure checks
- [ ] `<role>` exists as a real semantic block
- [ ] `<decision_boundary>` exists as a real semantic block
- [ ] `<workflow>` exists as a real semantic block
- [ ] Every workflow step has Action / Input / Output / Validation
- [ ] `<output_contract>` exists as a real semantic block
- [ ] `<default_follow_through_policy>` exists as a real semantic block
- [ ] At least one worked example exists and is not just a placeholder

## Eval and lifecycle checks
- [ ] `assets/evals/evals.json` exists
- [ ] `assets/evals/regression_gates.json` exists
- [ ] Trigger eval coverage includes should-trigger / should-not-trigger / near-miss
- [ ] Trigger eval coverage includes zh / en / mixed language cases
- [ ] Functional eval coverage includes happy path / edge case / failure mode
- [ ] Benchmark metadata requirements include skill version, git commit, host, model, timestamp, and grader version
- [ ] Version and audit date are not stale

## Manual review notes
- [ ] Triggers on obvious queries
- [ ] Triggers on paraphrases
- [ ] Does NOT trigger on unrelated queries
- [ ] Does NOT steal queries from neighboring skills
- [ ] Works on expected language variants
- [ ] If cross-tool, supported / unsupported hosts are explicitly documented
- [ ] Description clearly says when to use and when NOT to use the skill
- [ ] Skill has one clear primary job
- [ ] Instructions use imperative steps with input/output/validation
- [ ] Opening summary / Purpose / Scope paragraphs stay descriptive; only actionable instructions use imperative voice
- [ ] Core workflow works end-to-end
- [ ] Errors handled with actionable guidance
- [ ] Output matches required structure
- [ ] Output contract is explicit
- [ ] Default follow-through policy is explicit
- [ ] Examples exist when style/format quality matters
- [ ] Tool rules are explicit if the skill uses tools
- [ ] If cross-tool, the core skill pack is kept separate from host wrappers / manifests
- [ ] If cross-tool, auth / approval / persistence expectations are explicit
- [ ] Mutable state / cache / auth artifacts are NOT stored inside the skill folder

## Common error checks
- [ ] No missing local paths referenced from `SKILL.md` or `references/*.md`
- [ ] No unexplained orphan files remain in `scripts/`, `references/`, or `assets/`
- [ ] No contradictory rules between `SKILL.md`, `references/`, and `scripts/`
- [ ] No release-blocking `[TODO]` placeholders remain in user-facing instructions
- [ ] No hidden side effects bypass the stated follow-through policy
- [ ] Neighbor-skill overlap / negative triggers were reviewed after the latest changes
- [ ] Host wrappers do NOT fork or silently rewrite the core workflow

## Maintenance
- [ ] Version bumped in top-level version
- [ ] Changes documented (outside the skill folder, e.g., repo release notes)
- [ ] Evals saved to assets/evals/evals.json (if benchmarking this skill)
- [ ] Regression gates defined (if benchmarking this skill)
- [ ] ROI review completed
- [ ] Long workflows are split into stages or multi-turn steps when appropriate
- [ ] Model-specific notes added if GPT-style and reasoning models need different guidance
