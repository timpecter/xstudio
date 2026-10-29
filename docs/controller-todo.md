# Controller plugin implementation checklist

Source: [controller-plugin-plan.md](controller-plugin-plan.md), reconciled with the brainstorm and the architecture/API investigations. The controller implementation is partial: Windows input, bindings, transport, exposure, mask, loop, and the mode/guide overlay exist; Playlists/Media browsing with A activation and RB+A media multi-select exist (not yet user-accepted). Stage and acceptance boxes stay unchecked until their full exit evidence is met. Current subtask progress, blockers, and verification evidence are recorded below.

Mapping-panel update (2026-10-27): the
[mapping panel specification](controller-mapping-panel-spec.md) and
[implementation plan](controller-mapping-panel-plan.md) define the live editor
extension. Its execution checklist is below. Earlier completed work and
validation evidence remain historical facts, not evidence that the new panel
is implemented. Subsequent preview progress and evidence are recorded below;
full-feature acceptance remains unchecked.

## Implementation stages

- [ ] **Stage 0 — Resolve targeting.** Enumerate intended viewers and output paths; define the policy for divergent playback states and choose the initial projection/capture path. Produce a concrete fixture and target matrix, including named completion signals for source activation and timeline pinning.
- [ ] **Stage 1 — Build the thin risk slice.** Implement the Windows/Xbox adapter, minimal bindings, four controller modes, shared browse-and-confirm overlay, source activation, transport, and relative exposure. Pass the controller/projector-only trial for playlists, media, and pinned sequences across follower and independent viewers; verify state preservation, disconnect safety, and overlay presence in an agreed capture.
- [ ] **Stage 2 — Build the configurable workflow.** Add searchable supported actions, input learning, global and mode-specific bindings, modifiers, suitable repeat, profile save/default/import/export, and capture exclusion. Add resolver/profile tests and explicit unsupported-device/error feedback; validate binding precedence and profile schema before profile sharing.
- [ ] **Stage 3 — Validate package acceptance.** Add the immediate-navigation option, complete output coverage, guide/feedback, lifecycle handling, and packaged-runtime validation. Pass the agreed hardware/projector/capture matrix on both installed and portable Windows distributions without workstation interaction after setup.

The mapping-panel checklist refines the live configuration part of Stage 2.
It expands the older analog deferral and fixes the editor location as a dockable
xstudio panel. Global bindings, optional repeat, and legacy modifiers still
require explicit reconciliation; broader command discovery and response tuning
are deferred. Capture exclusion and immediate navigation remain separate
existing-stage requirements, not additions to the mapping-panel scope.

## Live mapping panel execution checklist - 2026-10-27

Step numbers, prerequisites, and exit criteria follow the
[mapping panel plan](controller-mapping-panel-plan.md). Gate IDs G1-G7 and
acceptance IDs A1-A17 refer to the
[mapping panel specification](controller-mapping-panel-spec.md).
Check a step's parent box only after its implementation, tests, and exit evidence
are complete. A recorded proposal does not close a decision gate.

### Decisions and integration discovery

#### LT Shift and staged Media checkbox trial - 2026-10-28

The user corrected the earlier Shift proposal: default LT (still configurable;
A/Menu excluded), RT toggles the highlighted checkbox independently of Shift.
The user agreed to try staged checks: Y clears, A opens the checked group or
the highlight if none checked. Earlier RB/Shift+A selection proposals below
are superseded, not additional modifiers.

- [x] Add trigger acquisition and hysteresis (press >=30/255, release <20/255),
  no held repeat and reconnect/edit/load re-arm safety.
- [x] Add Normal/Shifted bindings, configured Shift, Common/local precedence,
  cross-layer displacement, explicit disable and inherited fallback.
- [x] Confirm Shift reassignment conflicts across layers/modes; atomic Undo/Redo.
  Exclude A/Menu, free RB, and protect held buttons through layer changes.
- [x] Expose Shift/layer controls, effective guide and live layer state.
- [x] Add version-3 preset fields and non-writing version-1/2 migration.
- [x] Stage per-container Media checks separately from the playhead selection;
  RT checks, Y clears (including last check), A applies in list order or uses
  highlight when empty. Display checkboxes and instructions in the overlay.
- [x] Complete automated and focused real-runtime validation and safe deployment.
- [ ] Obtain physical-controller acceptance of LT/RT thresholds and checkbox trial.
- [ ] Resolve remaining grouped/continuous/capture/grading behavior; final wiring
  and full live-follow remain pending. Current editor view selection is manual.

Validation:

- `python -m unittest discover -s python\test\controller_input -p "test_*.py"`
  - **passed**, 93 tests (baseline 80). Includes trigger acquisition/thresholds/
  jitter/reconnect, both Shift release orders, simultaneous digital Shift/action,
  configuration edits/load/Undo re-arm, layer/Common precedence, cross-layer
  displacement, confirmed Shift conflicts, reserved RT/Y priority, staged checks,
  deleted media, per-container isolation, and version-1/2 migration/version-3
  round trips.
- `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  - **passed**, 2/2.
- `python python\test\controller_input\check_mapping.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  and `python python\test\controller_input\check_overlay.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  - **passed**, 3 QtTest checks each. Panel checks cover layer requests,
  disabled Shift input, and cancel/confirm reassignment; overlay checks cover
  checkbox markers and live Shifted status.
- `cmake -E copy_directory src\plugin\python_plugins\controller_input build_win11\bin\plugin-python\controller_input`
  - **passed**, no dependency reconfiguration.
- Two final isolated real-xstudio launches with synthetic raw trigger samples
  through the shared owner - **passed**, eight initial and seven restore checks.
  Real exposure confirmed Normal/Shifted dispatch and no action on held-button
  layer release; RT checked once without changing actual playhead selection;
  A applied the checked group in list order and preserved paused state; Y and
  removal of the final check left the viewer unchanged; RT/Y worked when chosen
  as Shift; reconnect-held triggers required release; saved layers/Shift restored
  on the second launch while checked media did not persist.
  An intermediate probe stopped at the expected Y reassignment confirmation;
  the corrected probe explicitly confirmed the conflict and passed.
  Disposable processes were stopped without touching user preferences.
- These focused trials do not claim resolution of the earlier broad Viewer
  media-stepping timeout, physical-controller response acceptance, or full
  grouped/continuous/wiring acceptance.

Approved binding-contract decisions (2026-10-27; specification section 5):

- [x] Reserve preset-independent Menu and its D-pad/A navigation while open.
- [x] Default dedicated held Shift to RB; allow per-preset changes and no
  standalone Shift mapping. Media multi-select follows Shift, not fixed RB.
- [x] Approve grouped Viewer navigation: Left/Right exposure, Up/Down media.
  Separate Exposure adjustment uses Left/Right only.
- [x] Confirm all displaced mappings before Shift reassignment; perform the
  change as one Undo-able edit, leaving the former Shift unassigned.
- [x] Require a fresh action-button press after a Shift transition; held buttons
  do not fire another action just because the layer changes.

This is decision evidence only. Full default/migration, remaining grouped and
analog semantics, and capture decisions remain open; dependent implementation
and full gate acceptance are not checked off.

- [ ] **0A - Establish baseline and binding contract.** No prerequisites.
  - [x] Run existing controller tests; record exact commands/results and
    separate pre-existing failures from later regressions.
  - [ ] Inventory inputs, functions, modes, modifiers, guide state, and browse gates.
  - [ ] Approve the default/migration table reconciling Menu/RB chords, one
    dedicated Shift button, grouped D-pad, and function uniqueness (G1).
  - [ ] Preserve required browsing and multi-selection or obtain approval for
    explicit behavior changes; settle global-binding scope/precedence or staging.
  - [ ] Define stable directional/grouped function semantics and unsupported
    pairs; close the catalog portion of G2 with an approved input/function table.
- [x] **0B - Prove dockable-panel integration.** No prerequisites; independent of 0A.
  - [x] Find supported QML/Python panel and bridge prior art; trace registration,
    installation, discovery, and shared-owner lifetime.
  - [x] Run an in-process state/edit/revision/error bridge proof.
  - [x] Verify two panels share one owner and closing both leaves it operating.
  - [x] Resolve G7 with runtime evidence and evolve proof code into the panel
    shell; stop for a decision if the supported integration path is insufficient.
- [ ] **0C - Settle remaining interaction/analog decisions.** Requires 0A for semantics.
  - [ ] Approve compatible pairs, grouped direction behavior, analog thresholds,
    hysteresis, repeat, neutral/release, and re-arm rules (G2).
  - [ ] Verify grading APIs and approve component/axis/rate/target semantics for
    Slope, Offset, and Power, or explicitly approve staging (G3).
  - [ ] Approve manual editing versus live mode/layer following (G4).
  - [ ] Approve connection removal, Shift conflicts, and button/grouped/analog
    capture behavior (G5).
  - [x] Approve preset names/collisions, built-ins, import activation, export of
    unsaved changes, history boundaries, and startup recovery (G6).
  - [ ] Record decisions in the spec before implementing dependent behavior.

### Core model and first live-edit slice

#### Common mappings extension - 2026-10-28

Follow-up usability clarification:

- [x] Label explicit per-mode Disable as **Unassigned**, distinct from
  **Inherit Common**; Common has Unassigned only, as it cannot inherit itself.
- [x] Disable Save when Factory is selected or the selected personal preset has
  no unsaved changes. Factory edits can be persisted through Save As.
- [x] Explain Save/Save As/Export Live with tooltips and usage documentation.
  Save As creates/selects a saved local preset; Export Live writes a portable
  file without changing local saved/dirty state.
- Validation: `python python\test\controller_input\check_mapping.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  - **passed**, 3 QtTest checks, including explicit Unassigned/Inherit labels,
  clean/dirty Factory Save disabled, clean personal Save disabled, dirty personal
  Save enabled, and successful Save returning to disabled. `git diff --check`
  - **passed**. Safe copy deployment and deployed QML hash verification passed.

Approved: function categories independent of mode; Common defaults with local
inherit/override/disable; reserved menu priority; mode Shifted > mode Normal >
Common Shifted > Common Normal; local functions suppress inherited duplicates
only in that mode. See specification section 5.

- [x] Implement Normal-layer Common defaults, local overrides, explicit Disable,
  and non-destructive duplicate suppression for editable ordinary buttons.
- [x] Make existing Mask, exposure up/down, and playback-behavior cycling
  assignable in every mode; expose function categories and effective provenance.
- [x] Wire panel Common editing, Inherit/Disable choices, guide, history,
  revision/held-input protection, and shared owner consistently.
- [x] Version portable presets; read legacy presets without changing effective
  actions; round-trip Common and Disable through save/import/export/restart.
- [x] Validate model/resolver, owner, persistence, and QML behavior; deploy safely.
- [ ] Obtain physical-controller acceptance of Common/override/disable editing.
- [ ] Extend Common rules to Shift/grouped/analog stages and final inherited-wire
  presentation. Separate Stop/direct playback commands still require semantics.

Validation for this slice:

- `python -m unittest discover -s python\test\controller_input -p "test_*.py"`
  - **passed**, 80 tests (baseline 73). Covers inheritance, local suppression,
  multiple disables, restore, common edits, all-mode function availability,
  history, held-input protection, owner guide/provenance, version-1 migration,
  and version-2 save/export/import/restart.
- `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  - **passed**, 2/2.
- `python python\test\controller_input\check_mapping.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  - **passed**, 3 QtTest checks, including Common choices, categorized labels,
  Inherit/Disable requests and inherited/disabled/suppressed provenance.
- `cmake -E copy_directory src\plugin\python_plugins\controller_input build_win11\bin\plugin-python\controller_input`
  - **passed**, safe deployment without dependency reconfiguration.
- Two disposable xstudio launches with isolated preferences and synthetic
  input through the real shared owner - **passed**, eight initial and seven
  restart checks. Verified exposure via Common in all four modes, local Mask
  outside Viewer, all three playback behaviors in Timeline, observable Disable
  and Inherit, local duplicate suppression, reserved Menu priority, version-2
  export/save, and exact saved Common/local/Disable startup restoration.
  Processes stopped; no user preferences changed. This does not resolve the
  earlier broader Viewer media-step timeout or physical-controller acceptance.

- [ ] **1 - Configuration and catalog validation.** Requires 0A.
  - [ ] Define typed preset, binding, input/function catalog, mode/layer, and
    validated parameter structures with stable IDs and schema version.
  - [ ] Represent sticks/D-pad as grouped inputs; derive Normal fallback rather
    than persist duplicate connections.
  - [ ] Validate dedicated Shift exclusion, input cardinality, per-mode
    cross-layer function uniqueness, IDs, availability, and approved compatibility.
  - [ ] Encode approved defaults/migration without changing runtime dispatch.
  - [ ] Pass default/round-trip, invalid/duplicate/unknown/parameter, cross-mode
    reuse, and non-mutating validation tests.
- [ ] **2 - Configuration-driven resolution.** Requires 1 and approved G1/G2 semantics.
  - [ ] Replace hard-coded mapping choices while retaining existing action semantics.
  - [ ] Implement held Shift, mode-local layers, Normal fallback, and fresh
    activation; add approved grouped directional adapters.
  - [ ] Retain connection generations, stale-event rejection, and focus-independent modes.
  - [ ] Pass default parity/approved-change, fallback, unassigned, cross-mode,
    both-release-order, and no-synthetic-press tests.
- [ ] **3 - Atomic edits, history, and revisions.** Requires 1/2 and relevant G5 decisions.
  - [ ] Implement assign, disconnect, and Shift-change transactions.
  - [ ] Remove displaced bindings without swapping; retain other-mode assignments.
  - [x] Serialize edit publication/input resolution and reject stale revisions.
  - [x] Implement Undo/Redo and content-based dirty state; preserve history on
    rejection and avoid corrupting it on no-op requests.
  - [ ] Pass A4/A5/A13, displacement restoration, redo invalidation,
    held-input, stale-client, and atomic-publication tests.
- [ ] **4 - First usable dockable live-edit slice.** Requires 0B/3 and G4.
  - [ ] Add status, mode/layer selection, readable lists, dirty state, and explicit errors.
  - [x] Wire a simple assignment control to authoritative shared transactions.
  - [x] Reassign and test Play/Pause in the same xstudio process without Apply/restart.
  - [ ] Validate A1, the non-drag portion of A2, A14/A17, stale bridge requests,
    panel reopen, and one dispatch per press. Final drag acceptance waits for 10.

### Analog input, capture, and grading

- [ ] **5 - Analog acquisition and continuous resolution.** Requires 2/3 and G2.
  - [ ] Acquire sticks/triggers while preserving ordered samples and button edges.
  - [ ] Implement approved fixed normalization, range endpoints, and D-pad diagonals.
  - [ ] Support continuous timing even when physical input values remain unchanged.
  - [ ] Implement continuous adapters and analog-to-command threshold/hysteresis
    with neutral/re-arm behavior.
  - [ ] End old operations on remap/context loss/disconnect/disable without a
    synthetic action or resetting accumulated user values.
  - [ ] Pass A9/A15, endpoint/noise/held-value/fake-clock/release-order,
    deflected-reconnect, stale-sample, and no-stuck-operation tests.
- [ ] **6 - Assignment capture.** Requires 3/5 and G4/G5.
  - [ ] Add shared-owner capture target, cancel, and visible capture state.
  - [ ] Suppress old/new dispatch from the capture gesture and re-arm safely.
  - [ ] Support approved button, Shift, grouped-control, and analog capture rules.
  - [ ] Pass A3/A15, held/noisy input, cancel/disconnect, target-change,
    multi-panel, and stale-request tests.
- [ ] **7 - Grading adapters and mode.** Requires 5 and approved G3/G1/G2 semantics.
  - [ ] Implement verified Slope/Offset/Power adapters and Grading mode.
  - [ ] Configure Grading + Shift: left stick = Slope, D-pad = Offset,
    right stick = Power through the shared catalog/transactions.
  - [ ] Preserve approved pipeline targeting, limits, and unrelated colour settings;
    report unavailable targets explicitly.
  - [ ] Pass A8/A15 with actual value-change, target-change, and neutral evidence.
    Placeholder functions do not qualify; deferral requires scope approval.

### Presets and complete presentation

- [ ] **8 - Preset storage and safe operations.** Requires 1/3 and G6;
  independent of analog/grading implementation.
  Ordinary-button scope is implemented and verified below; this parent remains
  open for the full Shift/grouped/analog preset schema and acceptance.
  - [x] Reuse repository user-storage conventions for named presets,
    Save / Save As, versioned import/export, and saved startup selection.
  - [x] Validate before activation and write safely before updating baseline/selection.
  - [x] Implement ordered Save/Discard/Cancel; a failed save blocks replacement.
  - [x] Implement approved collision, import, history, and recovery policies.
  - [ ] Pass A10-A13/A17 with round-trip, startup, malformed/unknown schema,
    unsupported/duplicate mapping, permission/write-failure, and no-partial-change tests.
- [ ] **9 - Configuration-derived guide and activity.** Requires 4/5 and G1.
  - [ ] Replace hard-coded guide/modifier/browse descriptions with effective mappings.
  - [ ] Publish active input, dispatched function, layer, and inheritance from
    the shared owner; distinguish input activity from actual dispatch.
  - [ ] Implement approved live-follow/edit-context policy and bounded UI
    publication without losing discrete feedback.
  - [ ] Pass A6/A7/A14/A16 with remapped guides, fallback, paused/empty viewers,
    multiple overlays, and analog-update load checks.
- [ ] **10 - Complete two-column wiring editor.** Requires 4/6/8/9;
  step 7 is also required for full acceptance.
  - [ ] Draw readable left inputs/right functions, accurate connections,
    grouped controls, and visible unassigned entries.
  - [ ] Add drag-to-connect/removal through shared transactions; distinguish
    inherited fallback and other-layer assignments.
  - [ ] Complete capture, Shift, preset/import/export, and Undo/Redo controls.
  - [ ] Preserve line endpoints through docking, resize, scrolling, filtering
    if present, and live updates; follow existing QML styling/focus patterns.
  - [ ] Pass A1-A7/A10-A14/A17, including drag rejection/cancel, keyboard
    controls, geometry changes, and controller operation across focus changes.

### Delivery and acceptance

- [ ] **11 - Windows runtime, lifecycle, and package acceptance.** Requires 7/10
  and resolution of all relevant gates.
  - [ ] Complete A1-A17 with Windows/Xbox hardware; live edits stay in one process.
  - [ ] Test repeated/multiple panels, disable/shutdown, disconnect/reconnect,
    held controls, rapid edits, and session replacement.
  - [ ] Verify saved-preset restart and import/export from clean configuration state.
  - [ ] Verify panel/QML installation and discovery in installed and portable packages.
  - [ ] Re-run existing transport/source/browse/selection/loop/mask/exposure and
    multi-viewer single-owner regressions.
  - [ ] Complete applicable projector/screening-room trials; retain explicitly
    blocked hardware checks rather than claiming success.
  - [ ] Update user documentation and record exact commands/results, manual
    observations/environment, approved scope changes, and remaining limitations.

### Mapping-panel acceptance evidence

These are final evidence checks, separate from implementation progress.

- [ ] **A1:** dock beside the viewer and identify the Play/Pause assignment.
- [ ] **A2:** drag-reassign; the next fresh activation uses it without Apply/restart.
- [ ] **A3:** capture changes the mapping without executing old/new actions.
- [ ] **A4:** displacement leaves former endpoints unassigned; one Undo restores
  both originals and Redo reapplies the edit.
- [ ] **A5:** cross-layer function reassignment removes the former binding only
  in that mode.
- [ ] **A6:** held Shift and visibly inherited Normal fallback behave correctly.
- [ ] **A7:** activity highlights dispatch once and follows approved context rules.
- [ ] **A8:** grouped Grading + Shift Slope/Offset/Power mappings work and cease safely.
- [ ] **A9:** continuous and button-like analog mappings obey approved thresholds
  without noise/held-value repeat errors.
- [ ] **A10:** Save/Discard/Cancel is correct; save failure prevents switching.
- [ ] **A11:** restart restores saved mappings/Shift, not unsaved experiments.
- [ ] **A12:** import/export preserves semantics; invalid files cause explicit
  errors and no partial live/persistent changes.
- [ ] **A13:** dirty state follows content through Undo and subsequent edits.
- [ ] **A14:** multiple/reopened panels share state and never duplicate dispatch.
- [ ] **A15:** remap/context/capture/disconnect/reconnect with held or deflected
  input causes no stale/synthetic action, stuck adjustment, or unintended value change.
- [ ] **A16:** guides/modifier/browse indicators reflect remapped controls;
  existing action semantics remain covered.
- [ ] **A17:** invalid edits, failed persistence, unknown actions, and unavailable
  hardware produce feedback while retaining the last valid configuration.

### Mapping-panel verification record

#### Compatibility-first preview implemented - 2026-10-27

The user approved implementing ordinary-button remapping before replacing
legacy Menu/RB/D-pad chords. Full steps 1-4/9 remain incomplete where they require
Shift layers, grouped controls, capture, or the final activity/follow behavior.
No A1-A17 full-feature acceptance box is closed by the preview.

- [x] Add an immutable validated ordinary-button configuration and preserve the
  original defaults across Viewer/Playlists/Media/Timeline.
- [x] Implement live A/B/X/Y/View assignment/disconnection for Play/Pause,
  Guide, and Viewer Mask/Loop; reserve legacy controls and retain Menu/RB chords.
- [x] Implement atomic displacement, Undo/Redo, revision checks, and dirty
  comparison against startup defaults; rejected edits leave state/history intact.
- [x] Block held controls after edits and reconnect until their release.
- [x] Register a dockable **Controller Mapping** panel through the existing
  Python `register_ui_panel_qml` API and use the supported UUID callback bridge.
- [x] Present the preview using existing xstudio widgets; expose mode selection,
  assignment dropdowns, Unassigned, Undo/Redo, status/errors, and explicit
  unsaved/restart limitations.
- [x] Derive ordinary-button viewport-guide labels from the live configuration.
- [x] Test shared state between two real panel instances, remapped dispatch,
  old-input disconnection, guide updates, and owner survival after panel closure.
- [ ] Obtain user/hardware acceptance of the preview.

Verification:

- `python -m unittest discover -s python\test\controller_input -p test_controller.py`
  before implementation - **passed**, 36 tests.
- `python -m unittest discover -s python\test\controller_input -p test_mapping.py`
  before implementation - **failed as expected**, missing mapping module.
- `python -m unittest discover -s python\test\controller_input -p "test_*.py"`
  after implementation - **passed**, 50 tests, including 14 new model/resolver/
  owner checks. These cover defaults, displacement, Undo/Redo/dirty state,
  invalid/stale/no-op edits, QML numeric revisions, held/reconnect input,
  legacy chord preservation, shared revisions, errors, and guide/dispatch.
- `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  - **passed**, 2/2, using the restored build Python runtime.
- `python python\test\controller_input\check_mapping.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  - **passed**, production panel behavior with callback/styled-widget boundaries
  faked. Exercises assignment/displacement, Undo, mode-specific choices, and
  explicit bridge-error feedback. Added as `controller_input_mapping_test` for
  subsequent CMake configurations; the current generated CTest file was not
  regenerated.
- `cmake --build build_win11 --target COPY_PY_PLUGIN_controller_input` -
  **interrupted** after automatic reconfiguration unexpectedly began replacing
  cached dependencies because of a PowerShell tool-version ABI change. Restored
  all 66 original packages from their exact locally cached ABIs, reconstructed
  their installed-file lists, retained the original installed status, and backed
  up the interrupted transaction records outside the repository. Verified the
  restored Python runtime, CTest checks, and real application startup afterward.
- `cmake -E copy_directory src\plugin\python_plugins\controller_input build_win11\bin\plugin-python\controller_input`
  - **passed**; deployed resources without dependency reconfiguration.
- Disposable `build_win11\bin\xstudio.exe --user-prefs-off` with development
  launcher environment and a temporary probe plugin - **passed**, six live
  checks: registration, two rendered/shared production panels, real QML-to-Python
  edit, remapped B dispatch once/former X unassigned, guide state, and owner/Undo
  after panel closure. Screenshots of both actual styled panels were inspected.
  Input was synthetic through the real owner; no physical controller acceptance
  is claimed. The probe application was stopped after validation.

At this checkpoint the preview used Normal mappings only and manual edit-mode
selection; persistence was still pending. The subsequent preset work is below.

#### Ordinary-button presets implemented - 2026-10-27

The user reported the initial preview was working well and approved G6:
read-only Factory, confirmation before replacing names, non-activating import,
live export without saving locally, history reset on preset load, and explicit
warning/Factory fallback on startup recovery.

- [x] Add versioned ordinary-button JSON presets and a single atomic library
  write for both saved mappings and selected startup preset.
- [x] Add named selection, Save / Save As, confirmed case-insensitive replacement,
  and protected Factory. Save-before-load is one commit, not two partial writes.
- [x] Add Save/Discard/Cancel switching, fresh load history, held-input re-arming,
  and revision checks across asynchronous dialogs/multiple panels.
- [x] Add portable import/export through existing file dialogs. Import never
  activates the imported configuration; export does not mark live edits saved.
- [x] Compare dirty state to the actual selected saved configuration, including
  when an import replaces that saved preset without activating its contents.
- [x] Restore saved selection at startup, warn/fall back without modifying damaged
  entries, and preserve unreadable libraries with explicit write errors.
- [x] Test failure-safe temporary writes, flush/replace failures, schema/device/
  scope/ID validation, duplicate JSON keys/bindings, history, stale confirmations,
  startup recovery, and Factory export as an importable **Factory Copy**.
- [x] Validate actual styled-panel callbacks and a separate application restart
  using an isolated user profile; visually inspect both rendered states.
- [ ] Obtain user acceptance of preset dialogs/save/load/import/export in the
  normal controller workflow.
- [ ] Extend the schema to cover the full Shift/grouped/analog configuration
  when those models are implemented. The current schema explicitly rejects
  unsupported scopes rather than discarding their settings.

Verification:

- `python -m unittest discover -s python\test\controller_input -p test_presets.py`
  before implementation - **failed as expected**, missing preset module.
- `python -m unittest discover -s python\test\controller_input -p "test_*.py"`
  - **passed**, 69 tests (19 added since the preview).
- `python python\test\controller_input\check_mapping.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  - **passed**, including preset Save As, replacement confirmation,
  Save/Discard/Cancel decision paths, Factory Save As before switching,
  import/export, retained export dirty state, and bridge-error feedback with
  callback/dialog/styled-widget boundaries faked.
- `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  - **passed**, 2/2; no CMake reconfiguration or dependency rebuild required.
- `cmake -E copy_directory src\plugin\python_plugins\controller_input build_win11\bin\plugin-python\controller_input`
  - **passed**, deployed the updated plugin/resources.
- Two disposable `build_win11\bin\xstudio.exe --user-prefs-off` launches with
  an isolated `USERPROFILE` and temporary probe plugin - **passed**, four checks
  per launch. Real production-panel callbacks exported/imported without activation,
  saved Review with B = Play/Pause, and left a later A remap unsaved. The second
  process restored B and the original A = Mask, clean with no Undo history.
  A missing-file import reported failure and preserved state. Both actual
  styled-panel screenshots were inspected; probe processes were stopped.

Local data is under xstudio's existing user preference root in
`controller_input\button-presets.json`. An unreadable whole library is kept
untouched and reports that it must be repaired or moved and xstudio restarted before local saves;
portable export remains possible. Presets cover ordinary buttons only, leaving
legacy Menu/RB/D-pad chords unchanged.

Next: user trial of presets, then resolve G1-G5 for Shift, grouped/analog inputs,
capture, grading, and full live-follow. The connective-line editor remains pending.

#### Menu toggle usability update - 2026-10-27

The user found holding Menu while navigating difficult and requested a toggle.
This supersedes historical Menu-held behavior recorded below; it does not change
the planned held Shift-layer requirement.

- [x] Press Menu once to open; release leaves it open; a second fresh press closes.
- [x] Keep mode changes, browsing, A activation, and RB+A Media selection gated
  by the latched menu state, not the physical Menu button.
- [x] Keep the menu open after selection and preserve browse highlights on
  Menu release; do not re-query the browsing list on an unchanged menu state.
- [x] Close/reset on disconnect or input failure; reconnecting with Menu held
  cannot toggle until release and a fresh press. Ignore duplicate Menu-down events.
- [x] Publish `Controller Menu Open` to the overlay and mapping panel, replacing
  the misleading Held attribute. Update guide text and optional runtime probe.
- [x] Preserve View guide independence, ordinary mappings, and preset behavior.
- [x] Obtain user acceptance of press-to-toggle on the physical controller
  (2026-10-27: "Working well so far!").

Validation:

- `python -m unittest discover -s python\test\controller_input -p "test_*.py"`
  - **passed**, 73 tests. New coverage includes release persistence, duplicate
  downs, reconnect-held suppression, independent guide visibility, selection
  without holding Menu, and no release-driven browse refresh.
- `python python\test\controller_input\check_overlay.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  and `python python\test\controller_input\check_mapping.py C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe`
  - **passed**, including updated menu attribute and toggle instructions.
- `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  - **passed**, 2/2 tests, rerun after correcting the owner test expectation.
- Disposable real xstudio session with the updated
  `python\test\controller_input\runtime_probe.py` - **partially passed**, nine
  live checks including release-persistent UI/menu state, timeline/playlist A
  activation, play-state preservation, and RB+A media selection with Menu
  released. The later unrelated viewer A/B media-step check timed out after
  dispatching `next_media`; full runtime regression acceptance is not claimed.
  The disposable process was stopped without touching the user's preferences.
- Focused disposable real-xstudio toggle probe - **passed**, five checks:
  released Menu stays open, mode/browse navigation needs no hold, A activates a
  real playlist and leaves the menu open, a second press closes/reopening
  preserves the highlight, and disconnect/reconnect-held suppression works.
  Input was synthetic through the shared owner; physical-controller acceptance
  remains pending.
- `cmake -E copy_directory src\plugin\python_plugins\controller_input build_win11\bin\plugin-python\controller_input`
  - **passed**, deployed the updated Menu behavior and QML resources without
  dependency reconfiguration.

Baseline command from the repository root:

```powershell
python -m unittest discover -s python\test\controller_input -p test_controller.py
```

If focused tests are split into more modules, use targeted selectors while
iterating and the following at controller integration boundaries:

```powershell
python -m unittest discover -s python\test\controller_input -p "test_*.py"
```

Discover exact existing QML/build/package targets during 0B. Record each command
with its result, effective-binding/dispatch assertions, hardware observations,
and blocked gates. Baseline/integration evidence above closes only the verified
work; 0A's full contract and 0C decisions still precede dependent implementations.

## Acceptance and regression checks

- [ ] Verify browsing alone changes neither application selection nor source; confirmation activates the chosen playlist; immediate mode uses the same activation semantics.
- [ ] Verify media confirmation targets the intended container and item, not a stale row or unrelated playhead selection.
- [ ] Starting from individual media and an unpinned sequence, verify sequence confirmation visibly activates the pinned timeline in every intended viewer.
- [ ] Verify source changes preserve playing/paused state under the agreed policy, including rapid successive activation and asynchronous completion.
- [ ] Test independent viewers and global followers; verify multiple overlays never cause duplicate command execution.
- [ ] Verify relative exposure applies once per distinct pipeline, respects attribute limits, and preserves other display settings.
- [ ] With a fake clock, verify mode/global precedence, dedicated modifiers, one dispatch per press, permitted repeat, and both modifier release orders.
- [ ] During playback, pause, repeat, or modifier hold, verify disconnect changes no source/transport/exposure state and playback continues naturally if already playing.
- [ ] Verify reconnect with held buttons causes no action until neutral; stale events and repeat timers cannot affect the new connection.
- [ ] Verify empty/deleted/reordered lists, session replacement, missing pipelines, invalid profiles, timeouts, and partial failures produce explicit feedback.
- [ ] Verify the guide, highlights, and feedback are readable on the actual projector, update while paused/empty, and work independently of panel focus.
- [ ] Verify agreed capture paths include overlays by default and honor the exclusion option.
- [ ] Verify plugin disable/shutdown, wired/wireless input, hot-plug, dialog/fullscreen focus, and both Windows package formats on the intended setup.

Use the repository's existing CTest infrastructure and targeted Python/Qt tests; record exact commands and results when available. Automated tests do not replace hardware, projection, and capture trials.

## Current execution status — 2026-10-25

**Stage 0 decisions recorded:** the initial controller target is all interactive
on-screen viewers plus video output; exclude quickview. Viewers should share one
source and transport state. If their prior playing/paused states diverge, use the
global review playhead state for the newly activated source. The actual
projector/capture path still needs a runtime trial, so Stage 0 is not complete.

- [x] Confirmed the source-level activation path: `SessionActor` handles
  `session::viewport_active_media_container_atom`, updates `viewedContainer_`,
  and calls `setOnScreenPlayhead(true)`. That method sends the new playhead via
  `ui::viewport::viewport_playhead_atom` to the global playhead events actor.
- [x] Identified candidate output classes from source; this is an inventory, not
  an approved scope matrix:

  | Candidate | Source-backed evidence | Scope status |
  |---|---|---|
  | Main and registered interactive viewers | Viewport actors register with the global playhead event actor; session code observes per-viewport playhead changes. | Included, including secondary and independent viewers; runtime fan-out still needs verification. |
  | Quickview viewers | Session code treats quickview windows separately from the main global-playhead path. | Excluded from the initial target. |
  | Plugin-owned offscreen/video-output viewports | `VideoOutputPlugin` requests an offscreen viewport and attaches it to the current on-screen playhead. | Video output is included; runtime attachment and overlay/capture still need verification. |
  | Snapshot/movie/export renderers | No shared overlay/capture path is established by the inspected evidence. | Not part of the initial target unless later identified as required video output. |

- [x] Named source-level observations for the fixture: `session::viewport_active_media_container_atom`
  with the target container UUID confirms the session's viewed-container state;
  `ui::viewport::viewport_playhead_atom` identifies playhead attachment, and
  per-viewport `playhead::show_atom` events identify onscreen media/source
  changes. For a timeline, also verify `pinned_source_mode` is enabled on the
  effective playhead and confirm timeline media is actually shown. The inspected
  source does not provide one acknowledgement that alone proves all viewers
  rendered the intended pinned-timeline frame.
- [x] Recorded the initial scope and divergent-state policy above. The source
  integration still needs validation that each intended interactive viewer and
  video output receives the global playhead.
- [ ] Select and exercise the first projector/capture path and concrete
  screening-room fixture. **Blocked:** no hardware/projector trial or runtime
  overlay/capture evidence is available in this workspace. Proposed fixture for
  that trial: a session with a playlist, an individual media item initially
  viewed, and a pinned timeline; exercise follower and independent viewers,
  then repeat activation while playing and paused. Add the actual viewer/output
  inventory and expected divergent-state result once agreed.
- [x] Implemented the on-demand viewport guide with shared controller status
  text, connected/disconnected status updates, mode feedback, and a working
  `ToggleGuide` action. Removed the unsupported fifth `Grading` mode so
  controller mode cycling matches Viewer, Playlists, Media, and Timeline.
- [x] Swapped the View and Menu button assignments: Menu is now the dedicated
  mode modifier and View toggles the guide. Updated the on-screen guide text,
  reconnect-baseline handling, and binding/actor tests to match.
- [x] Fixed missing mode feedback: connect the utility plugin's attributes to
  the UI after actor initialization, and separate the current mode from guide
  visibility and status text. A compact badge stays visible while connected;
  View expands/collapses the guide without hiding the badge or losing the mode.
  Connection changes, mode changes, and guide toggles request viewport redraws
  for paused/empty viewers. Quickview is excluded from this overlay.
- [x] Added `OverlayRegistersWithUiAndShowsModeWithoutGuide` to verify initial
  UI-model registration, mode updates with the guide closed, guide toggling,
  disconnect visibility state, and redraw requests through fake UI actors.
- [x] Built the plugin and test targets:
  `& $env:ComSpec /c 'call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && cmake --build build_win11 --target input_test controller_input'`
  — **passed**.
- [x] Ran `ctest --test-dir build_win11 --output-on-failure -R controller_input_input_test`
  — **passed**, 1/1 test, 0 failures. The test includes guide-attribute toggling
  along with the swapped button assignments, input edges, mode bindings, and
  existing actor actions.
- [x] Rebuilt and deployed the mode-overlay fix with the build command above,
  then reran the controller CTest: **passed**, 1/1 registered test. Windows
  initially blocked copying the loaded DLL; deployment succeeded after the user
  closed xSTUDIO. Built and runtime DLL hashes matched after deployment.
- [x] Exercised the production overlay QML in a temporary Qt 6.5.3 harness with
  synthetic attribute-model values:
  `C:\Qt\6.5.3\msvc2019_64\bin\qmltestrunner.exe -platform offscreen -input C:\Users\User\.copilot\session-state\b092939b-0b24-4def-b94e-1b9a670c8f5c\files\controller-overlay-check\tst_controller_overlay.qml -o C:\Users\User\.copilot\session-state\b092939b-0b24-4def-b94e-1b9a670c8f5c\files\controller-overlay-check\results.txt,txt`
  — **passed**, 3 checks, 0 failures. Verified visible/in-bounds badge, mode text
  updates without the guide, guide expansion/collapse, quickview exclusion,
  and hiding after disconnect. Qt warned that its font directory was absent.
  This isolated QML check does not establish real viewer/projector/video-output
  integration; the temporary harness is not part of the repository test suite.
- [x] User confirmed the deployed plugin works when launched with
  `build_win11\run_xstudio.bat`: loop mode, Menu + D-pad mode switching,
  the mode badge, and View guide are working. Projector/video-output capture
  acceptance remains outstanding.
- [x] Committed the user-confirmed native implementation and its planning
  documents as `98764fa3` before starting the Python replacement.
- [x] Recreated the plugin in
  [Python](../src/plugin/python_plugins/controller_input/controller.py), using
  standard-library `ctypes` for XInput 1.4 slot 0. Preserved the four modes,
  Menu modifier, View guide, shared badge, transport, mask callback, loop
  sequence, and relative exposure. Retained the existing reconnect baseline
  behavior, not the stronger neutral-until-release requirement above.
- [x] Removed the native controller implementation/build registration and
  registered the Python plugin with the existing build/install copying macro.
  Removed only the obsolete build/runtime `controller_input.dll` files after
  the user closed xSTUDIO. Startup explicitly rejects a leftover native plugin
  to prevent dual dispatch. Existing install prefixes must also remove that DLL
  before using the replacement; clean installs do not contain it.
- [x] Added Python tests for input ABI/errors, edges/generations, fixed bindings,
  UI state, actions, pipeline address deduplication, failure reporting, and
  worker shutdown. Added a production-QML test using synthetic model boundaries
  for badge geometry, mode changes, guide expansion, quickview exclusion, and
  disconnect visibility.
- [x] `cmake --build build_win11 --target COPY_PY_PLUGIN_controller_input`
  — **passed**, copied the Python plugin and QML into
  `build_win11\bin\plugin-python\controller_input`, used by `run_xstudio.bat`.
  No main-executable rebuild or new dependency was needed.
- [x] `build_win11\vcpkg_installed\x64-windows\tools\python3\python.exe -B -m unittest discover -s python\test\controller_input -v`
  — **passed**, 20 tests.
- [x] `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  — **passed**, 2/2 registered tests. The old native test is no longer registered.
- [x] `git diff --check` — **passed**. SHA256 comparisons confirmed all five
  deployed Python/QML files match their source files; the legacy runtime DLL
  is absent.
- [x] Exercised the deployed Python plugin in a disposable GUI session with
  `--new-session --session controller-python-probe --user-prefs-off`, using the
  launcher's runtime environment and
  [runtime_probe.py](../python/test/controller_input/runtime_probe.py).
  `build_win11\vcpkg_installed\x64-windows\tools\python3\python.exe -B C:\Users\User\.copilot\session-state\b092939b-0b24-4def-b94e-1b9a670c8f5c\files\run_controller_probe.py`
  — **passed** all six action/integration checks: automatic discovery, real
  mode/guide attributes, loop modes, mask callback, viewer exposure, and
  playback toggles/disconnect on generated PNG media. The probe checks
  programmatic input, not physical-controller operation. Its temporary launcher,
  media, and results were removed after verification.
  An additional API-only GUI-shutdown attempt did not exit within 20 seconds;
  the disposable fixture was terminated. Plugin worker stop/join is separately
  covered by tests; normal application-close/package acceptance remains open.
- [x] Confirm physical-controller behavior after relaunching the Python version
  with `build_win11\run_xstudio.bat`. Native runtime confirmation above does not
  establish Python hardware acceptance.
  **User trial:** playback, loop cycling, and mode switching worked, but the
  overlay and input logs were absent. The fixes and stronger checks below
  supersede the earlier overlay/log parity claim; a fresh user trial is pending.
- [x] Fixed Python overlay registration: create the boolean visibility attribute
  first, then attach its QML role. Passing `qml_code` during creation selects a
  `QmlCodeAttribute` (empty string value), which prevents `XsHudItem` from
  instantiating the overlay. Updated fake attribute creation to model this
  backend behavior and added real `OnOffToggle`/boolean/QML-role assertions.
- [x] Restored normalized `Controller Input` and semantic `Controller Command`
  JSON logs at Info level, including connection, button-down and button-up
  events. Forwarded warnings and exception tracebacks too. The Windows API log
  actor reaches the console but not the GUI Log sink in this build, so a single
  application-level QML bridge drains Python records into the Log window model.
  This bridge is separate from viewer overlays; consuming batches removes
  records, avoiding duplicates across consumers.
- [x] `cmake --build build_win11 --target COPY_PY_PLUGIN_controller_input`
  — **passed**, deployed the overlay/logging fix without rebuilding C++.
  `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  — **passed**, 2/2 registered tests, including 24 Python tests.
- [x] Ran the extended
  [GUI probe](../python/test/controller_input/runtime_probe.py) in a separate
  `--new-session --session controller-feedback-probe --port 14449 --user-prefs-off`
  process, leaving the user's running application intact.
  `build_win11\vcpkg_installed\x64-windows\tools\python3\python.exe -B C:\Users\User\.copilot\session-state\b092939b-0b24-4def-b94e-1b9a670c8f5c\files\controller_feedback_probe.py`
  — **passed**, nine integration checks. Unlike the first probe, this exercised
  the actual UI models and `XsHudItem` composition, saved and visually checked
  the rendered mode/button guide, and exported the actual GUI Log model to
  confirm both input and command entries. The application console also contained
  25 input and 10 command JSON records. Temporary fixtures were removed.
- [x] User confirmed the Python overlay and Log window fixes work as expected.
- [x] Changed the compact mode badge to appear only while Menu is held. Release,
  disconnect, input failure, and reconnect baseline clear its held state.
  Per the user's explicit choice, the View guide remains independently visible.
  Quickview remains excluded.
- [x] Implemented the read-only browse-presentation slice of the next task.
  Playlists mode previews session playlists and their nested playable containers
  in API order; Media previews the viewed container's media (falling back to
  the Media-panel container). D-pad
  Up/Down moves a shared highlighted candidate, clamped at the ends, with a
  seven-row window. Mode entry opens the preview and B closes it. The next
  D-pad action reopens it. UUID-based candidates survive list reordering;
  input refreshes lists, missing candidates warn and reset, session replacement
  clears old candidates, and empty lists produce visible feedback.
  This is not a live subscription to list edits or filtered UI rows.
- [x] Kept preview movement independent of application selection, source, and
  playback. A still reports that source activation is unavailable; it does not
  silently accept or activate the preview. Activation/pinning/fan-out remains
  the next implementation task, not a delivered browse-and-confirm workflow.
- [x] `cmake --build build_win11 --target COPY_PY_PLUGIN_controller_input`
  — **passed**, deployed Menu-held state and browse presentation.
  `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  — **passed**, 2/2 registered tests, including 29 Python tests.
  Coverage includes Menu press/release/disconnect/reconnect, independent guide
  visibility, preview geometry, list reordering/removal/emptiness, session and
  container changes, and read-only browsing.
- [x] Extended the disposable
  [GUI probe](../python/test/controller_input/runtime_probe.py):
  `build_win11\vcpkg_installed\x64-windows\tools\python3\python.exe -B C:\Users\User\.copilot\session-state\b092939b-0b24-4def-b94e-1b9a670c8f5c\files\controller_browse_probe.py`
  — **passed**, 11 integration checks, including real Menu-held attributes,
  playlist/timeline/media preview, unchanged viewed source/media selection/
  paused state, and real UI-model rendering of the guide and highlighted media
  preview with the guide closed. Visually checked both captured images.
  Log window records and existing transport/exposure/mask/loop checks passed.
  Temporary fixture files were removed afterward.
- [x] User reported that the Menu-held badge and View guide overlays work after
  relaunch.
- [x] **Bug fixed:** entering Media mode raised
  `RuntimeError: Media preview requires a viewed container` when the session
  had no viewer container (`Session.viewed_container` is None). Media now falls
  back to the Media-panel container (`Session.inspected_container`). If neither
  exists, it shows a visible empty "no playlist open" preview with a warning,
  and the source is unchanged. The Python tests now cover both fallback paths.
  `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  — **passed**, 2/2. Redeployed with `COPY_PY_PLUGIN_controller_input`;
  the deployed `controller.py` hash matches source.
- [x] User accepted the Media mode fix after relaunch. Committed the Python
  rewrite as `e8b50d48`.
- [x] Implemented A activation and RB multi-select. The user chose:
  - A replaces the media selection.
  - RB+A toggles the highlighted media in or out of the selection.
  - RB+D-pad only moves the highlight.
  - Playlist activation also updates the Media panel.

  Behaviour:
  - Browsing still changes nothing until A is pressed.
  - Playlists A re-reads the list and revalidates the highlighted candidate.
    It sets both the inspected and the viewed container, then waits up to 3 s
    until the global viewer playhead is that container's playhead. Otherwise
    it raises a visible failure.
  - Timelines are pinned (`Pinned Source Mode` true).
  - Media A sets the container's playhead selection. If needed, it first
    switches the viewer to the media container. A timeline container is
    unpinned so the selected clips play, matching the Media panel.
  - RB+A cannot remove the last selected item; it warns instead.
  - The global playing/paused state is read before and restored after
    activation.
  - A `●` marker shows the viewed playlist and selected media.
  - Media rows show file names instead of full paths.
  - The guide lists A and RB+A.

  Not covered: rapid successive activation and independent (non-follower)
  viewers.
- [x] `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  — **passed**, 2/2. These include 34 Python tests: bindings, the fake backend
  for timeline pinning, play-state restore, viewer-switch timeout, replace,
  toggle and keep-one, the inspected-timeline unpin, and stale-highlight
  revalidation. The QML test checks the row markers.
- [x] Disposable GUI probe (launcher in the session `files/` folder, removed
  afterward) — **passed**, 13 live checks. These include:
  - A on a real timeline: viewer and Media panel switch, pinned, paused kept.
  - A back to the playlist: playing kept.
  - Real A/RB+A presses: replacing and toggling the playhead selection.
  - The rendered marker overlay, which was checked visually.
  Redeployed; all deployed files match source by hash.
- [x] Reworked the layout at the user's request:
  - Viewer D-pad Left/Right adjusts exposure.
  - Viewer D-pad Up/Down shows the previous/next media. It sends xSTUDIO's own
    "Jump to previous/next media/clip" playhead hotkeys, using IDs generated
    from name + component. In compare modes this cycles the displayed item of
    the multi-selection; for a single item it steps the playlist selection; in
    timelines it steps clips.
  - Menu is now the gate for browsing. Menu + D-pad Left/Right changes mode.
    In Playlists/Media, Menu + Up/Down browses, Menu + A views, and
    Menu + RB + A toggles media.
  - The browse list opens on Menu press and hides on release. No timeout was
    chosen. Without Menu, Playlists/Media ignore the D-pad and A. B is unused.
- [x] `ctest --test-dir build_win11 --output-on-failure -R "controller_input_(python|overlay)_test"`
  — **passed**, 2/2, including 36 Python tests. They cover the new bindings,
  Menu-gated list visibility and the hotkey message. The QML test checks that
  the list is hidden without Menu.
- [x] Disposable GUI probe — **passed**, 14 live checks. These include:
  - Menu-gated playlist/timeline/media activation and RB+A selection.
  - Real Up/Down presses in viewer mode cycling the displayed (key) playhead of
    a two-item A/B selection in both directions.
  - The updated guide rendering, which was checked visually.
  Redeployed; all deployed files match source by hash. Probe files were
  removed.
**Default-mode / menu-only modes slice (2026-10-28):**

- [x] Viewer merged into Common (default); Playlists/Media/Timeline apply only
  while Menu is open and chosen; closing Menu returns to Common; mode state is
  republished to attributes/guide on every change.
- [x] Shift+Y = configurable `cycle_compare` (Factory Common shifted Y); no Shift+D-pad
  function (plain D-pad Up/Down already steps media/sources, per user).
- [x] Preset schema 4 with Viewer-to-Common migration from versions 1-3.
- [x] Unit tests: 100 passing (`python -m unittest` in `python\test\controller_input`);
  QML checks check_overlay.py and check_mapping.py pass with Qt 6.5.3 qmltestrunner.
  Includes a trigger-sample test that checks two media with RT in Media mode.
- [ ] **Media multi-select report not reproduced.** Controller-level tests check and
  mark multiple items, so the cause is unconfirmed; needs a live trial after redeploy.
  The compare-layout cycle probes a fixed list (xstudio gives Python no layout list).
- [ ] Redeploy, update/rerun `runtime_probe.py` in a disposable session (updated
  for Common but NOT run), and user acceptance. Grading mode remains deferred.

- [ ] User acceptance of A activation, RB+A multi-select, Menu-gated browsing
  and the new viewer D-pad layout after relaunch with
  `build_win11\run_xstudio.bat`.
- [ ] Validate guide readability and overlay inclusion on the actual projector
  and video-output path. **Blocked:** no runtime/hardware capture trial has
  been performed; source/QML wiring alone is not acceptance evidence.

**Existing controller work still pending:** after user acceptance, cover rapid successive
activation and independent viewers. Then run the projector/video-output trial.
Stage 0 and Stage 1 remain unchecked: projector and video-output validation,
independent-viewer coverage and the acceptance trial are still outstanding.
