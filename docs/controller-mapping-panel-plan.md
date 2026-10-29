# Live controller mapping panel implementation plan

Date: 2026-10-27

Current trial update (2026-10-28): the user's corrected default is **LT held
Shift**, not RB. A/Menu are excluded from Shift choices. RT checks highlighted
Media, Y clears checks, and A applies checked media (or just the highlight if
none checked). This is a staged, transient per-container checkbox trial, not
live playhead selection and not the earlier RB/Shift+A chord. Trigger press
>=30/255 and release <20/255 were approved for this trial. Button/trigger
Normal/Shifted layers, configurable Shift, conflict confirmation, Common
precedence, and version-3 presets are now implemented; validation/acceptance is
tracked in the checklist. Historical RB and Normal-only updates below describe
earlier stages, not current defaults. Continuous/grouped controls, capture,
grading, final wiring and full live-follow remain open.

Status: execution has begun with the user-approved compatibility-first button
preview described below. Unresolved product decisions listed as gates remain
unapproved.

Authority: [mapping panel specification](controller-mapping-panel-spec.md).
Requirement IDs A1-A17 and decision gates G1-G7 below refer to that document.
The [brainstorm](controller-plugin-brainstorm.md) records product intent.
The [earlier working plan](controller-plugin-plan.md) and
[existing checklist](controller-todo.md) remain the record of controller work
outside this panel feature.

Approved initial sequencing change (2026-10-27): build a narrow live preview
for ordinary A/B/X/Y/View assignments before replacing legacy chords. Keep
Menu/RB/D-pad behavior intact temporarily. The preview implements a subset of
steps 1-4 and 9 with a real dockable panel and callback bridge; it does not close
their full Shift/grouped-control requirements or G1-G6. The full feature scope
remains unchanged. G7's registration/bridge proof passed in a disposable xstudio
runtime; detailed evidence is in the checklist.

Preset update (2026-10-27): G6 policies are approved and the ordinary-button
portion of step 8 is implemented, including real-application save/import/export
and two-launch restore validation. Persistence currently uses versioned
`ordinary-buttons` scope; it must be extended deliberately when Shift/grouped/
analog configuration is implemented. No full-feature gate is closed merely by
the existing button schema.

Menu usability update (2026-10-27): the user requested toggle-open/toggle-closed
Menu behavior instead of holding Menu while navigating. This is implemented
independently of the pending held Shift-layer design. Use the current toggle
behavior, not historical Menu-held wording below, when reconciling G1 defaults.

Binding-contract update (2026-10-27): the user approved reserved Menu navigation,
configurable held Shift defaulting to RB, Shift-based Media multi-selection,
grouped Viewer navigation preserving the existing four D-pad directions, and
confirmed/undoable Shift reassignment with fresh action-button presses after
layer transitions. See specification section 5 for the authoritative rules.
These are partial G1/G2/G5 decisions, not implemented preview features or closure
of step 0A/0C. Remaining defaults/migration, analog, and capture decisions stay open.

Common mapping extension (2026-10-28): specification section 5 now separates
function categories from modes and defines Common defaults, local overrides,
explicit Disable, non-destructive inherited-function suppression, and Shift
precedence. The Normal ordinary-button slice is implemented with categorized
choices, effective provenance, guide/dispatch integration, and version-2 presets.
Legacy version-1 presets retain their exact mappings with empty Common scope.
Acceptance A18/A19 extend the original A1-A17. Apply these rules to subsequent
Shift/grouped/analog model, resolution, capture, and wiring work; the current
slice does not claim those stages are complete. Validation is in the checklist.

## 1. Delivery strategy

Build a thin end-to-end live-remapping slice before completing the visual editor.
First prove that a dockable panel can update the existing Python action owner's
configuration safely. Then complete transactions, capture, presets, analog
semantics, grading, and the final wiring interactions.

Keep the current Windows/XInput backend and one shared Python action owner.
Do not introduce a second poller, a native controller shim, a new input library,
or a generic node/device framework.

Steps are bounded implementation units, not promises of one commit each.
For each step:

1. Read the relevant existing code and approved decisions.
2. Add the smallest failing test covering the intended behavior.
3. Implement only that behavior using existing project patterns.
4. Run targeted tests; run the controller regression suite when shared runtime
   behavior changes.
5. Record exact commands/results and any remaining hardware evidence.

Do not mark a step complete merely because UI controls appear or an API request
returns success. Assert the resulting configuration and actual dispatched action.

## 2. Decisions and discovery before dependent work

### Step 0A: establish baseline and resolve the binding contract

**Prerequisites:** none.

- Run the existing controller tests and record failures before editing.
- Inventory available inputs, functions, mode-switch operations, modifiers,
  guide state, and browse gates in the current Python plugin.
- Produce a concrete default-mapping table that reconciles existing Menu/RB
  chords with the dedicated Shift model, grouped D-pad, and function uniqueness.
- Explain any mappings that cannot be preserved exactly and obtain approval
  for the replacement behavior; do not silently drop multi-selection or browsing.
- Resolve global-binding precedence/scope or explicitly agree how global
  bindings are staged without losing required current operations.
- Define stable function semantics, including directional mode changes and
  grouped navigation/exposure operations.
- Resolve G1 and the catalog/grouped-control portion of G2 with the user.

**Exit:** approved input/function catalog and default/migration table, with
unsupported combinations identified. Baseline test results are recorded.

### Step 0B: prove dockable-panel integration

**Prerequisites:** none; can be investigated independently of 0A.

- Find repository prior art for registering a dockable QML panel and exchanging
  state/commands with a Python plugin.
- Trace registration, installation, plugin discovery, and shared-owner lifetime.
- Build the smallest in-process proof: show connection/configuration state,
  submit an edit to a fake or harmless configuration field, and receive the
  authoritative revision or explicit error.
- Open two instances to prove shared ownership; close them and verify that
  the controller owner remains alive.
- Keep any proof code confined to the actual integration path and evolve it
  into the panel shell, rather than leaving a second demo subsystem.
- Resolve G7 from source evidence and a runtime probe. If the supported bridge
  cannot satisfy the spec, stop for an architectural decision rather than
  adding a speculative native component.

**Exit:** verified panel/bridge mechanism, installation requirements, and
single-owner behavior. Runtime proof is required, not just a source trace.

### Step 0C: settle remaining interaction and analog decisions

**Prerequisites:** 0A for input/function semantics; independent of 0B.

Resolve these in focused user decisions and record them in the spec:

- G2: compatible pairs; grouped direction meaning; analog threshold, hysteresis,
  repeat, neutral, release, and re-arm semantics. Use existing response
  constants where they exist; do not invent tunable settings.
- G3: actual grading API, affected components, rate/axis semantics, and supported
  targets for Slope/Offset/Power. Obtain an explicit staging decision if that
  support cannot ship with the rest of the feature.
- G4: manual mode/layer editing versus live following during drag/capture.
- G5: connection removal, Shift reassignment conflicts, and capture rules for
  Shift, grouped controls, and analog controls.
- G6: names/collisions, built-in preset behavior, import activation, export of
  unsaved changes, history boundaries, and startup recovery.

Technical investigation should present concrete choices, not ask the user to
choose an implementation API. Implementations below wait only for their relevant
decisions; unrelated pure model work need not wait for every gate.

**Exit:** affected behavior is testable without guessing. No default is promoted
from proposal to requirement without approval.

## 3. Core model and live-remapping slice

### Step 1: configuration and catalog validation

**Prerequisites:** 0A.

- Define typed configuration/catalog structures using existing Python patterns.
- Include schema version, preset identity/name, device kind, dedicated Shift,
  modes, layers, input IDs, function IDs, and validated semantic parameters.
- Represent grouped controls as one input; derive fallback rather than storing
  duplicate connections.
- Validate identifiers, modes, parameters, dedicated Shift exclusion, and
  per-mode/per-layer cardinality. Add compatibility validation as G2 is resolved.
- Encode the approved default preset and migration behavior without changing
  runtime dispatch yet.

**Tests:** valid defaults, round-trip representation, duplicate inputs/functions,
cross-layer uniqueness, reuse across modes, unknown/unavailable IDs, and malformed
parameters. Validation must not mutate the source configuration.

**Exit:** a deterministic model that rejects invalid configurations explicitly.

### Step 2: configuration-driven resolution

**Prerequisites:** 1; approved G1 and relevant G2 semantics.

- Replace hard-coded mapping choices with the validated configuration while
  retaining existing action implementations.
- Implement held Shift, mode-local layers, Normal fallback, and fresh-activation
  handling for buttons.
- Introduce approved grouped adapters for existing directional operations.
- Preserve connection generations, stale-event rejection, and mode independence
  from UI focus.
- Keep current behavior operational through the approved default preset.

**Tests:** default mapping parity or explicitly approved changes, both Shift
release orders, unassigned inputs, fallback, cross-mode assignments, and no
synthetic presses on mode/layer changes.

**Exit:** the existing action owner executes approved mappings without a panel.

### Step 3: atomic edits, history, and authoritative revisions

**Prerequisites:** 1 and 2; G5 for removal and Shift changes.

- Implement assign, disconnect, and Shift-change transactions.
- Assignment removes occupied input/function bindings exactly as specified,
  including a target function's assignment in the other layer of the same mode.
- Serialize configuration publication and input resolution through the existing
  owner. Use revisions to reject stale edits explicitly.
- Add Undo/Redo and content-based dirty comparison against the saved baseline.
- Ensure rejected/no-op requests cannot corrupt history or partially publish.

**Tests:** A4/A5/A13, full displacement restoration, invalid edit atomicity,
stale requests from two clients, redo invalidation after a new edit, and held
inputs across remapping. Assert dispatch never sees a partial configuration.

**Exit:** one complete edit publishes one revision and is reversed in one Undo.

### Step 4: first usable dockable live-edit slice

**Prerequisites:** 0B and 3; G4 for editing context.

- Evolve the bridge proof into a panel with connection status, mode/layer
  selectors, readable input/function lists, explicit errors, and dirty state.
- Wire a simple assignment affordance to the same transaction API that the
  later drag/capture workflows will use.
- Display authoritative revisions; never make local UI state a second source
  of configuration truth.
- Verify Play/Pause can be reassigned and tested without restarting xstudio.

**Tests/trial:** A1/A2 using the temporary assignment affordance, A14/A17,
rejected/stale bridge requests, panel close/reopen, and one dispatch per press.
The final drag-specific A2 acceptance waits for step 10.

**Exit:** a real end-to-end button-remapping slice. It is not full panel acceptance.

## 4. Input semantics and capture

### Step 5: analog acquisition and safe continuous resolution

**Prerequisites:** 2 and 3; approved analog/grouped semantics from G2.

- Extend acquired state with both sticks and triggers while retaining button
  edges, generations, and ordered samples.
- Normalize values using the approved fixed response policy, including signed
  range endpoints and grouped D-pad diagonal behavior.
- Ensure continuous behavior receives the updates/timing it needs even when
  the physical state remains unchanged; do not assume button-edge sampling
  is sufficient.
- Implement supported continuous adapters and analog-to-command activation,
  including threshold/hysteresis and explicit neutral/re-arm behavior.
- On remap, mode/layer change, disconnect, or disable, end the old continuous
  operation without dispatching a new discrete action or resetting the user's
  accumulated grading/exposure value.

**Tests:** range endpoints, noise around thresholds, held values, fake-clock
rate behavior, both release orders, reconnect while deflected, stale samples,
and no stuck action or final-value reset. Cover A9/A15.

**Exit:** continuous and button-like analog mappings have deterministic,
approved semantics, not just values appearing in the panel.

### Step 6: assignment capture

**Prerequisites:** 3 and 5; approved G4/G5 capture policy.

- Add owner-managed capture with target mode/layer/function, cancel, and clear
  UI feedback.
- Consume captured input before normal resolution, including events needed to
  re-arm safely after capture.
- Support buttons, grouped sticks/D-pad, and triggers under the approved rules.
- Handle cancellation, disconnect, target changes, and multiple panel instances
  without leaving capture stuck or dispatching the gesture.

**Tests:** A3/A15, old/new action suppression, already-held inputs, Shift capture,
analog noise, cancel/release, and stale capture requests.

**Exit:** capture and direct assignment produce identical validated transactions.

### Step 7: grading adapters and mode

**Prerequisites:** 5; approved G3 and relevant G1/G2 catalog decisions.

- Implement verified Slope/Offset/Power action adapters and expose Grading mode.
- Preserve approved viewer/colour-pipeline targeting and component semantics.
- Make Grading+Shift left stick/Slope, D-pad/Offset, right stick/Power configurable
  through the same catalog and transaction path.
- Report missing/incompatible grading targets explicitly.

**Tests/trial:** A8/A15, actual value changes, limits, target changes, neutral
handling, and preservation of unrelated colour settings.

**Exit:** the requested grading example works in xstudio. A placeholder row is
not completion. Any deferral requires explicit scope approval.

## 5. Presets and complete presentation

### Step 8: preset storage and failure-safe operations

**Prerequisites:** 1 and 3; approved G6. Can proceed independently of steps 5-7.

- Reuse the repository's user-configuration location and persistence conventions.
- Add named presets, Save / Save As, versioned import/export, and saved startup
  selection.
- Validate before activation and write safely before changing the saved baseline
  or selected startup preset.
- Implement Save/Discard/Cancel as an ordered operation; save failure blocks
  replacement.
- Apply approved collision, import activation, history, and recovery policies.

**Tests:** temporary-directory round trips, A10-A13/A17, malformed/unknown schema,
unsupported controls/functions, duplicate mappings, permission/write failures,
failed replacement, and startup recovery. Verify invalid operations alter
neither live configuration nor the previous valid saved data.

**Exit:** persisted mappings, dirty state, and startup selection remain consistent
under success and failure.

### Step 9: configuration-derived guide and live activity

**Prerequisites:** 4 and 5; approved modifier/browse behavior from G1.

- Generate guide descriptions and modifier/browse indicators from effective
  mappings instead of hard-coded Menu/RB text.
- Publish active input, effective function, layer, and inheritance from the
  shared owner; distinguish input activity from actual command dispatch.
- Apply approved live-follow behavior without moving an active edit's context.
- Avoid UI traffic at raw polling frequency when coalescing is safe; never lose
  discrete command feedback or introduce action execution in presentation code.

**Tests/trial:** A6/A7/A14/A16, remapped guide labels, fallback rendering, paused/
empty viewers, multiple overlays, and bounded state publication under analog input.

**Exit:** guides and editor describe the same effective configuration.

### Step 10: finish the two-column wiring editor

**Prerequisites:** 4, 6, 8, and 9; include 7 before full feature acceptance.

- Render controller inputs left and functions right, with accurate connecting
  lines, grouped controls, and visible unassigned entries.
- Add drag-to-connect and the approved connection-removal interaction using the
  existing transaction API.
- Distinguish fallback connections and cross-layer assignment context.
- Complete capture, Shift selection, preset, import/export, and Undo/Redo controls.
- Keep endpoints correct during resize, docking, scrolling, filtering if present,
  and live updates. Do not introduce a canvas navigation/node system.
- Use existing QML styling, focus, keyboard, and error presentation patterns.

**Tests/trial:** drag success/rejection/cancel, A1-A7/A10-A14/A17, connection
geometry after resize/scroll, inherited versus explicit bindings, keyboard
operation of controls, and focus changes while the controller remains active.

**Exit:** both assignment workflows are complete and agree on the live result.

## 6. Final regression and delivery

### Step 11: Windows runtime, lifecycle, and package acceptance

**Prerequisites:** steps 7 and 10; all relevant gates resolved.

- Run all A1-A17 scenarios with the Windows/Xbox controller in the same xstudio
  process for live-edit scenarios.
- Test repeated panel open/close, multiple instances, shutdown/plugin disable,
  disconnect/reconnect, held controls, rapid edits, and session replacement.
- Verify saved-preset restart and import/export using clean configuration state.
- Verify panel/QML resources are installed and discoverable in both existing
  installed and portable Windows distribution workflows.
- Re-run existing transport, source activation, browsing, selection, loop, mask,
  and exposure regressions. Confirm one owner across interactive viewers.
- Complete the existing screening-room/projector trial where applicable; keep
  unavailable hardware evidence explicitly pending rather than claiming success.
- Update user-facing controller documentation and the existing implementation
  checklist with actual behavior, commands/results, and outstanding limitations.

**Exit:** acceptance evidence covers every requirement or records an explicitly
approved scope change. No unresolved gate is hidden behind a disabled UI item.

## 7. Dependency summary

```text
0A -> 1 -> 2 -> 3 -> 4
0B ----------------> 4
0C -> affected behavior in 2, 3, 4, 5, 6, 7, 8, 9, 10
2 + 3 -> 5 -> 7
3 + 5 -> 6
1 + 3 -> 8
4 + 5 -> 9
4 + 6 + 8 + 9 -> 10
7 + 10 -> 11
```

Independent work is an option, not a requirement to use parallel agents.
Do not concurrently edit shared resolver/owner files without explicit ownership.

## 8. Validation commands and evidence policy

Baseline and button/runtime regression command from the repository root:

```powershell
python -m unittest discover -s python\test\controller_input -p test_controller.py
```

If focused tests are split into additional `test_*.py` modules, run their smallest
applicable selectors while iterating and use this controller-suite command at
integration boundaries:

```powershell
python -m unittest discover -s python\test\controller_input -p "test_*.py"
```

Use existing QML checks, CMake targets, and packaging commands after discovering
the exact applicable targets in step 0B. Do not prescribe an unverified target
or install tooling just for this plan.

For each implementation step record:

- Exact command and result, with baseline failures separated from regressions.
- Assertions on effective bindings and dispatched actions.
- Manual runtime/hardware scenarios, observed results, and environment.
- Any blocked gate or acceptance criterion.

The original planning task changed documentation only. Subsequent implementation
tests and runtime evidence are recorded in the checklist; physical hardware
trials remain outstanding.
