#!/bin/bash
set -euo pipefail
# Cleanroom v1.3.0 validation:
# - Fresh clone of agent-pipeline-claude @ claude/adoring-banach-e9a9e1
# - Independent test run (no shared state with worktree)
# - Manual scaffold of a fixture project using the payload
# - Verify the scaffolded files match v1.3.0 expectations

TMP=$(mktemp -d)
echo "Cleanroom tmp: $TMP"

cd "$TMP"
echo ""
echo "=== STEP 1: fresh clone the v1.3.0 branch ==="
git clone --depth 1 --branch claude/adoring-banach-e9a9e1 https://github.com/scottconverse/agent-pipeline-claude.git plugin 2>&1 | tail -5

cd plugin
echo ""
echo "=== STEP 2: validate plugin metadata ==="
cat .claude-plugin/plugin.json | python3 -m json.tool | head -10
VERSION=$(python3 -c 'import json; print(json.load(open(".claude-plugin/plugin.json"))["version"])')
echo "version: $VERSION"
if [ "$VERSION" != "1.3.0" ]; then
    echo "FAIL: expected 1.3.0, got $VERSION"
    exit 1
fi
echo "OK"

echo ""
echo "=== STEP 3: ensure no autonomous_skip_chat anywhere ==="
if grep -r 'autonomous_skip_chat' pipelines/ skills/ 2>&1 | grep -v '^Binary' | head; then
    echo "FAIL: autonomous_skip_chat references still present"
    exit 1
fi
echo "OK: zero autonomous_skip_chat references"

echo ""
echo "=== STEP 4: ensure no gate_policy: autonomous default in template ==="
grep -E '^\s*gate_policy:' pipelines/manifest-template.yaml skills/pipeline-init/references/pipeline-payload/pipelines/manifest-template.yaml 2>&1 | head -5 || echo "(no active gate_policy fields)"
COUNT=$(grep -cE '^\s*gate_policy:' pipelines/manifest-template.yaml skills/pipeline-init/references/pipeline-payload/pipelines/manifest-template.yaml 2>&1 | grep -v ':0$' | wc -l)
if [ "$COUNT" -gt 0 ]; then
    echo "FAIL: gate_policy fields still present in templates"
    exit 1
fi
echo "OK"

echo ""
echo "=== STEP 5: install pytest + run full test suite from fresh clone ==="
pip install --quiet pytest pyyaml 2>&1 | tail -3 || true
python3 -m pytest tests/ -q --tb=line 2>&1 | tail -10

echo ""
echo "=== STEP 6: scaffold pipeline-init payload to a fresh fixture project ==="
FIXTURE=$(mktemp -d)
echo "Fixture project at: $FIXTURE"
# Simulate what pipeline-init does: copy payload into the fixture as .pipelines/ + scripts/policy/
mkdir -p "$FIXTURE/.pipelines"
mkdir -p "$FIXTURE/scripts/policy"
cp -r skills/pipeline-init/references/pipeline-payload/pipelines/* "$FIXTURE/.pipelines/"
cp skills/pipeline-init/references/pipeline-payload/scripts/*.py "$FIXTURE/scripts/policy/"
echo "Scaffolded files:"
find "$FIXTURE" -maxdepth 3 -type f | wc -l

echo ""
echo "=== STEP 7: scaffolded scripts run cleanly ==="
cd "$FIXTURE"
python3 scripts/policy/check_autonomous_mode.py 2>&1 | head -3
echo "exit: $?"
python3 scripts/policy/check_autonomous_compliance.py 2>&1 | head -3
echo "exit: $?"

echo ""
echo "=== STEP 8: a fake manifest with no gate_policy validates ==="
mkdir -p .agent-runs/test-run
cat > .agent-runs/test-run/manifest.yaml <<'YAML'
pipeline_run:
  id: "test-run"
  type: bugfix
  branch: "fix/cleanroom-test"
  goal: "Cleanroom test: validate v1.3.0 manifest with no gate_policy or autonomous_grant fields parses cleanly."
  allowed_paths:
    - "src/"
  forbidden_paths:
    - "docs/adr/"
  non_goals:
    - "No autonomous mode invocations."
  expected_outputs:
    - "src/foo.py"
  required_gates:
    - human_approval_manifest
    - human_approval_plan
    - policy_passed
    - tests_passed
    - human_approval_merge
  risk: low
  rollback_plan: "git revert the merge commit; no schema migration introduced."
  definition_of_done: "Cleanroom test asserts the v1.3.0 manifest with no gate_policy field passes check_manifest_schema.py."
  director_notes: []
  advances_target: "v1.3.0 cleanroom smoke"
  authorizing_source: ""
  override_active_target: ""
  target_repos: []
YAML

python3 scripts/policy/check_manifest_schema.py --run test-run 2>&1 | tail -3
echo "schema exit: $?"

echo ""
echo "=== CLEANROOM v1.3.0 RESULT: ALL CHECKS PASSED ==="
echo "tmp: $TMP"
echo "fixture: $FIXTURE"
