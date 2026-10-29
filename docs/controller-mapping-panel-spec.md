# Live controller mapping panel specification

Date: 2026-10-27

Status: draft for implementation planning. Agreed requirements are specified
below; unresolved product decisions and implementation gates are explicitly
identified. This document does not claim that the full panel is implemented or that
hardware acceptance has passed.

Execution sequence: [mapping panel implementation plan](controller-mapping-panel-plan.md).

Implementation update (2026-10-27): the user approved a compatibility-first
preview for ordinary button mappings while retaining the existing Menu/RB/D-pad
chords temporarily. The dockable Controller Mapping panel now edits A, B, X, Y,
View, LB, RB, LT, and RT for Play/Pause, Guide, Mask, playback-behavior cycling, and exposure
up/down, with immediate updates, Undo/Redo, revision validation, and held-input
protection. Named presets, Save / Save As, import/export, and saved startup
selection are implemented for button/trigger mappings. Normal and Shifted layers
and configurable held Shift (default LT) are implemented. Capture, continuous
analog/grouped mapping, grading, and the final wiring view remain outstanding.
Manual edit-mode selection is a preview affordance, not resolution of the full
live-follow policy. See the [checklist](controller-todo.md) for validation.

To try the preview in the development build, launch xstudio and select
**Controller Mapping** from a panel's panel-selection menu. Choose the mode to
edit, or choose **common** to edit defaults inherited by all modes. Change a
button's function dropdown; functions are labelled by category, not restricted
to Viewer. In a mode, choose **Inherit Common**, a local function override, or
**Unassigned** (no action, including no Common fallback). In Common,
**Unassigned** removes the default; Inherit Common is not applicable there.
Choose Normal or Shifted in **Edit layer**. In Shifted, **Inherit Normal / Common**
removes the explicit binding and follows the precedence in section 5.
**Unassigned** explicitly blocks that layer's fallback. The selected Shift input
cannot be assigned a standalone action; changing it confirms any disconnected
bindings across modes/layers and is one undoable edit.
The label below each dropdown identifies its effective action, inheritance,
disable, or suppression by another local assignment. Changes are live;
displacement never swaps assignments. Undo/Redo restores complete edits.
The asterisk denotes changes
from the selected saved preset. Use **Save As** to create a personal preset;
**Factory** is read-only. **Save** is disabled on Factory, even after edits;
use Save As for those edits. For personal presets, Save is enabled only when
there are unsaved changes. Use **Save** to update a personal preset. Existing
Menu-gated browsing/mode changes remain available, and the
viewport guide reflects ordinary-button remappings.

Menu interaction update (2026-10-27): press and release **Menu** once to open the
controller menu; press it again to close. Releasing Menu does not hide the
menu or refresh/reset its browsing highlight.

Default-mode update (2026-10-28): the former **Viewer** scope is merged into
**Common**, which is the default mode. Specialized modes (Playlists, Media,
Timeline) are active only while the Menu is open *and* that mode has been chosen
with D-pad Left/Right (the cycle is Common, Playlists, Media, Timeline).
Closing Menu always returns to Common and discards the choice; reopening Menu
starts in Common. While Menu is open, configured Common/local mappings still work
except the reserved navigation controls listed in section 5. Factory Common is
now X=Play/Pause, View=Controller Guide, A=Mask, Y=Cycle Playback Behavior and
Shift+Y=Cycle Compare Layout (a configurable function, `cycle_compare`, available
in every mode). Plain D-pad Up/Down already steps previous/next media (in compare
modes this cycles the compared source), so no extra Shift+D-pad function exists.
Preset schema version 4 stores no Viewer scope; versions 1-3 migrate on load by
folding Viewer bindings into Common (Viewer wins on a clash, a Viewer Unassigned
removes the Common binding) and adding Shift+Y=Cycle Compare Layout when that
input and function are free. The on-disk legacy file is not rewritten until saved.
`cycle_compare` tries a fixed layout order (Off, A/B, String, Grid, Horizontal,
Vertical, Wipe) and keeps the first layout the playhead accepts, because xstudio
exposes no list of registered layouts to Python. Grading remains deferred; the
fourth mode is Timeline.

Menu navigation: while open, D-pad Left/Right
changes mode and D-pad Up/Down browses Playlists/Media. In Playlists, A activates
the highlighted item. In Media, RT toggles a checkbox, Y clears all checks, and
A views the checked group (or highlighted item if none are checked).
Activation leaves the menu open for
further choices. Closing restores ordinary mode-specific controls. Disconnect
or input failure closes the menu; reconnecting with Menu held requires release
and a fresh press before reopening. The View guide remains independent.
This replaces the former Menu-held gate; the dedicated
Shift layer remains hold-to-use, not toggled.

Preset controls:

- Choosing another preset prompts Save / Discard / Cancel when mappings are dirty.
  Saving Factory's edits requests a personal name before switching.
- Reusing a name asks before replacing it; name matching is case-insensitive.
- Import adds a saved preset without activating it. Replacing the selected
  preset by import still leaves the live mapping untouched; dirty state then
  compares it against the newly imported saved version.
- **Export Live** writes the current working mapping without saving locally.
  Unlike Save As, it creates a portable file at a chosen location, does not
  create/select a local preset, and does not clear unsaved changes. Save As
  creates/selects a named local preset and marks the current mappings saved.
  Exporting Factory uses the portable name **Factory Copy**, so it can be
  imported without trying to replace the protected Factory entry.
- Loading a preset starts a fresh Undo history. Saving retains edit history;
  Undo can return to an earlier configuration and mark it dirty again.
- Restart restores the last selected saved preset, not unsaved changes.

Local storage follows xstudio's user preference location:
`%USERPROFILE%\.config\DNEG\xstudio\preferences\controller_input\button-presets.json`.
The library and portable files are versioned JSON with device `xinput` and scope
`ordinary-buttons`. Version 3 stores Common and all four modes' editable button/
trigger mappings, explicit Disable, each binding's layer, and dedicated Shift.
It does not store fixed menu controls, temporary checked media, or future
continuous analog settings. Unsupported versions,
scopes, identifiers, and duplicate assignments are rejected rather than ignored.
Version-1/2 libraries/presets remain readable with their explicit bindings in
Normal and default LT Shift; version 1 gains no Common defaults. Loading does not
rewrite files; subsequent saves write version 3. Version-3 exports require the
updated plugin. The former fixed RB+A selection gesture is intentionally
replaced by the menu trial below, not persisted as a legacy preset binding.

Missing/invalid startup selections produce a visible warning and use Factory
without modifying the damaged entry. If the entire library is unreadable, it is
preserved and local writes are blocked with an explicit error until the file is
repaired or moved aside and xstudio restarted; live editing and portable export
remain available.

## 1. Purpose and authority

Allow a user to inspect, change, and test controller mappings inside xstudio
without restarting the application, and save and share different configurations.

The primary interaction is a two-column wiring view: controller inputs on the
left, functions on the right, and editable connections between them. This is a
mapping editor, not a general-purpose node graph.

Sources:

- [Brainstorm](controller-plugin-brainstorm.md): agreed product behavior.
- [Existing working plan](controller-plugin-plan.md): earlier controller work
  and subsequent Python-only implementation direction.
- [Implementation checklist](controller-todo.md): existing acceptance work and
  known limitations.

This specification supersedes the older deferral of analog mapping and the
undecided panel-versus-companion-app location for this feature. It does not
silently approve older proposals for global binding precedence, repeat, or
profile behavior that were not settled in the panel brainstorm.

Terms:

- **Preset:** a named, saved controller configuration.
- **Working configuration:** the editable configuration currently used for live
  controller operation; it may differ from the selected saved preset.
- **Mode:** deliberate controller context, independent of panel keyboard focus.
- **Layer:** Normal or Shifted within a mode.
- **Explicit binding:** a stored input-to-function connection in a mode/layer.
- **Effective binding:** the connection used at runtime, including Normal
  fallback when Shifted has no explicit binding.
- **Function:** a supported semantic controller operation, not an arbitrary
  internal message or executable script.

## 2. Scope

### Required

- Dockable xstudio panel with live mapping edits.
- Windows/Xbox controller support using the current Python controller plugin.
- Buttons, grouped sticks, grouped D-pad, and triggers.
- Normal and held-Shift layers within each supported controller mode.
- Drag-to-connect and physical-input capture assignment.
- One-to-one explicit binding rules, displacement, and Undo/Redo.
- Live activity display and mode/layer following.
- Named local presets, Save / Save As, and file import/export.
- Persistence of the last selected saved preset.
- Existing controller function catalog initially.

### Deferred

- A broader catalog of xstudio commands or arbitrary UI action discovery.
- Editable sensitivity, dead zones, and inversion.
- Independent stick-axis or D-pad-direction wiring.
- Double presses, long presses, action sequences, or general chord programming.
- Additional controller backends, platforms, or simultaneous device ownership.
- A general-purpose visual programming system.

Optional hold-to-repeat, global binding editing, and interaction with legacy
modifiers require reconciliation before being added to the panel.

## 3. Implementation baseline before the preview

The following is source evidence, not proof of runtime acceptance:

| Surface | Current behavior | Implication |
|---|---|---|
| [Input acquisition](../src/plugin/python_plugins/controller_input/input.py) | Standard-library `ctypes` XInput 1.4 reader, slot zero; button state with connection generations and ordered events | Retain the backend and stale-event protections. Analog fields exist in the ABI structure but are not returned in `State`. |
| [Binding resolver](../src/plugin/python_plugins/controller_input/bindings.py) | Hard-coded Viewer, Playlists, Media, Timeline modes and Menu/RB modifier rules | Replace hard-coded assignment decisions with validated configuration, without losing required controller operations. |
| [Shared action owner](../src/plugin/python_plugins/controller_input/controller.py) | One Python plugin polls input, dispatches commands, and publishes shared attributes | The panel must edit this owner's configuration, not introduce another poller or command dispatcher. |
| [Viewport overlay](../src/plugin/python_plugins/controller_input/overlay.qml) | Shared controller status with hard-coded guide text | Guide text and binding-dependent feedback must reflect effective mappings. |
| [Controller tests](../python/test/controller_input/test_controller.py) | Python `unittest` coverage for acquisition, bindings, and controller behavior | Extend existing tests rather than introducing an unrelated test framework. |

### Existing function inventory

The initial catalog must be reconciled with these source-backed operations:

| Function/action identifier | Current context or constraint |
|---|---|
| `toggle_playback` | Play/Pause; not separate Start and Stop functions |
| `toggle_guide` | Show/hide the controller guide |
| `select_mode` | Currently produced by directional mode cycling; direction is resolved inside the binding logic |
| `exposure_down`, `exposure_up` | Viewer exposure adjustment |
| `previous_media`, `next_media` | Viewer media stepping |
| `toggle_mask` | Viewer mask toggle |
| `cycle_loop` | Viewer loop-mode cycling |
| `browse_previous`, `browse_next` | Playlists/Media browsing |
| `confirm` | Activate the highlighted browsing item |
| `toggle_select` | Media selection toggle |

Catalog entries need stable identifiers, user-facing labels, supported modes,
and supported input semantics. Where an operation needs a direction or other
parameter, the catalog must represent that explicitly rather than infer it from
the physical button name. Do not invent executable support for an unavailable
function merely to populate the UI.

### Important gaps

- Grading is not in the current `MODES` tuple. Slope, Offset, and Power are not
  exposed by the inspected controller function dispatcher.
- The current D-pad is mapped by individual directions. A grouped D-pad UI
  therefore needs semantic adapters for existing directional operations.
- Existing Menu-held mode changes/browsing and Menu+RB+A multi-selection do
  not directly match a single dedicated Shift button.
- Continuous analog acquisition, command semantics, and analog-to-discrete
  activation rules need implementation.
- The inspected plugin exposes viewport overlay and dynamic QML state; a
  dockable-panel registration path still needs verification.

These are implementation gates, not grounds for silently reducing the agreed
feature set.

## 4. Panel behavior

### Layout and state

The panel provides:

1. Preset selection, an unsaved-changes indicator, Save, Save As, import/export,
   and Undo/Redo controls.
2. Controller connection status and explicit error feedback.
3. Mode selection and a Normal / Shifted view switch.
4. The input column, function column, and connecting lines.
5. A way to select the preset-wide dedicated Shift button.
6. A visible assignment-capture state with a cancel affordance.

Use readable controller names, not raw bit masks. Render grouped inputs as one
entry and one connection, not multiple axis/direction sockets.

Unassigned inputs and functions remain visible. Show enough mode/layer context
to explain a function assigned in the other layer. In Shifted view, distinguish
inherited Normal fallback from explicit Shifted bindings; fallback must not look
like a second saved assignment.

The panel highlights live input, the effective connection, and the function
actually dispatched. It follows the active controller mode and layer.
Selecting an editing view must not itself execute a controller command.

How manual selection temporarily interacts with automatic following remains a
decision gate; the panel must not move an in-progress drag or capture to a
different context without an explicit policy.

### Assignment

Both workflows edit the same configuration:

- Drag an input connection to a function.
- Select a function, enter capture, and operate the desired controller input.

A successful assignment immediately becomes live. There is no Apply button.
Capture consumes the assignment input without executing its old binding.
It must also prevent a held input from firing the new binding merely because
capture has completed. Capturing Shift or grouped/analog controls requires the
rules in section 10 to be settled.

Assignment is a single transaction:

1. Validate the target mode, layer, input, and function.
2. Remove an existing binding for that input in the edited layer.
3. Remove any explicit assignment of the target function in either layer of
   the same mode.
4. Insert the new binding.
5. Publish the entire validated result as one live revision.

Do not swap displaced connections. Do not remove the same function from other
modes. An invalid edit leaves the previous configuration unchanged and reports
the reason.

A user must also be able to remove a connection without replacing it. The exact
gesture/control is not yet agreed.

### Undo/Redo

- One assignment, including all displaced bindings, is one undoable edit.
- Undo/Redo immediately changes the live configuration.
- Removing a binding and changing Shift must also be covered by edit history.
- Undo/Redo does not itself execute newly assigned actions.
- Dirty state reflects configuration content relative to the saved baseline,
  including when Undo returns to that baseline.
- History boundaries on preset load/import remain to be confirmed.

## 5. Resolution rules

### Approved Menu, Shift, and grouped D-pad contract (2026-10-27)

Updated 2026-10-28: the user corrected the earlier RB default and approved a
trial separating checkboxes from active viewer selection. These rules supersede
RB/Shift+A selection proposals in historical planning:

- Menu is reserved and preset-independent. It toggles the controller menu and
  cannot be assigned as Shift or wired to an ordinary function.
- The dedicated held Shift button is configurable per preset and defaults to
  LT. A and Menu cannot be Shift. The preview offers B, X, Y, View, LB, RB, LT,
  and RT; grouped controls remain unavailable as Shift. It has no standalone
  mapped action in any mode/layer. RB is free for ordinary mappings.
- While Menu is open, reserved menu navigation takes priority over configured
  mappings: D-pad Left/Right changes mode; Up/Down browses Playlists/Media;
  A confirms/activates. Media reserves RT for checking, Y for clearing checks,
  and A for viewing checked media (or the highlight if none checked). Selection
  does not depend on Shift. Reserved controls still work if RT or Y is chosen
  as Shift; their ordinary mapped actions remain unavailable. Other configured
  Common/local mappings stay active while Menu is open. Closing Menu returns to
  Common. Remapping D-pad cannot remove menu navigation.
- Checkbox trial: checked media are transient per session/container and start
  empty, independently of the viewer's active sources. RT never activates media
  or changes playback; the last check can be removed. Y clears all checks without
  changing the viewer. A applies checked media in list order, otherwise just the
  highlight, preserving the existing playback/pinning/target policy. Remove
  deleted media from checks with a logged warning. Checks are not saved in
  controller presets. Checkboxes in the overlay are controller-operated
  indicators in this trial; mouse interaction is not implemented.
- Trigger trial: sample both XInput trigger bytes. Engage at >=30/255, stay held
  down to 20/255, and release below 20/255. No repeat while held. Reconnect-held
  triggers need release and a fresh squeeze; edits and preset loads block held
  inputs until release. Continuous trigger mappings remain deferred.
- The grouped **Viewer navigation** function preserves the existing D-pad
  directions through one connection: Left/Right decreases/increases exposure;
  Up/Down selects previous/next media.
- Single-purpose grouped functions may also be offered. **Exposure adjustment**
  uses Left/Right to decrease/increase exposure; Up/Down performs no action.
  Other grouped functions and compatible input pairs still require definition.
- Reassigning Shift to a mapped button first shows a confirmation listing all
  mappings that will be disconnected across modes/layers. Confirming changes
  Shift and removes those assignments in one undoable transaction; Cancel changes
  nothing. The former Shift button becomes unassigned.
- Pressing or releasing Shift while an action button is held does not trigger
  another action. That button must be released and pressed again before an action
  can fire in the new layer. Continuous-control neutral/re-arm rules remain open.

These decisions partially resolve G1, G2, and G5. The complete default/migration
table, remaining grouped-function semantics, analog rules, and capture behavior
are still gates; this approval does not close them.

### Common mappings and function categories (approved 2026-10-28)

Function categories organize discovery, independently of controller modes:
Transport, Playback behavior, Image/display, Browsing, Grading, and Controller.
Category membership must not restrict which mode can use a supported function.
Play/Pause and Stop are distinct semantics; the existing implementation provides
Play/Pause, not a separately defined Stop. Unimplemented functions must not appear
as executable choices.

Each preset has Common mappings inherited by every mode, plus mode-specific
overrides. Each scope has Normal and Shifted layers. Reserved menu controls
take priority; otherwise use the mode mapping, then Common, then no action.
For Shift held, precedence is mode Shifted, mode Normal, Common Shifted, Common
Normal. Without Shift it is mode Normal, then Common Normal. Thus a mode's Normal
override remains effective under Shift unless explicitly replaced.

For each mode/input distinguish **Inherit Common**, **Override**, and
**Unassigned** (explicit Disable internally). Disable blocks inherited actions; it is not deletion of an
override. A mode-level Disable blocks both layers unless explicitly overridden
in a layer. Common unassigned means no default action.

A local assignment of a function suppresses inherited assignments of that same
function on other inputs in that mode only. It never removes the saved Common
assignment or changes another mode. Removing the local assignment restores
inheritance. A single activation dispatches at most one action. Uniqueness applies
within a scope across layers, not destructively across Common and local scopes.

The editor offers Common alongside modes. Show inherited effective actions and
their origin, local overrides, explicit disables, and suppressed Common bindings.
The eventual wiring view uses muted/dashed inherited wires and solid overrides,
with Edit Common, Override here, and Disable here affordances.

Controller mode changes must not silently change transport/display targeting.
Preserve the existing action target policy; broader targeting remains a separate
decision.

Common/override/disable now covers editable buttons and discrete triggers in both
layers. Expose existing Mask, exposure up/down, cycle playback behavior and
cycle compare layout actions in every mode. Presets before schema 4 are migrated by
folding their Viewer scope into Common (see the 2026-10-28 default-mode update).
New Factory uses Common X=Play/Pause, View=Controller Guide, A=Mask,
Y=Cycle Playback Behavior and Shift+Y=Cycle Compare Layout.
Separate Stop/direct playback-behavior commands, grouped inputs,
and final wiring interactions remain subsequent work.

### Layer resolution

Each preset has one dedicated Shift button, shared across modes. It has no
standalone function assignment. Shift is held, not toggled.

Within each Common or mode-specific scope, resolve its own layers as follows,
then apply the Common/local precedence and suppression rules above:

- An input has at most one explicit binding per layer.
- A function has at most one explicit binding across both layers.
- Without Shift, use the input's Normal binding.
- With Shift, use its explicit Shifted binding if present; otherwise use its
  Normal binding.
- An input with neither applicable binding performs no action.

Normal fallback is not a duplicate explicit assignment. A function can be
assigned independently in another mode. The Common/local precedence and
non-destructive suppression rules above govern inherited bindings.

Mode/layer changes, remapping, and capture completion must not synthesize a
fresh press for an input already held. Continuous controls must not leave a
previous function active after losing its binding or context. Exact neutral,
release, and re-arm semantics for continuous controls require definition.

## 6. Analog and grouped controls

- Each stick is one grouped input.
- The D-pad is one grouped input.
- Triggers are editable inputs.
- Support continuous operation and button-like commands from sticks/triggers.
- Preserve existing response settings; do not introduce a tuning editor.

Required desired configuration:

| Mode | Layer | Input | Function |
|---|---|---|---|
| Grading | Shifted | Left stick | Slope |
| Grading | Shifted | D-pad | Offset |
| Grading | Shifted | Right stick | Power |

This is a product requirement example, not an assertion that grading adapters
already exist. Axis/direction meaning, affected grading components, adjustment
rate, and neutral behavior must be specified before implementing those adapters.

Input/function compatibility is undecided. Do not silently cast a vector,
trigger value, or grouped directional input into an arbitrary function argument.
Connections lacking defined semantics must be explicitly unavailable rather
than appear to work.

## 7. Presets and persistence

- Live edits change only the working configuration until explicitly saved.
- Save updates the selected writable preset; Save As creates a named preset.
- Presets include mappings for all modes/layers and the dedicated Shift input.
- Loading another preset with unsaved edits offers Save, Discard, or Cancel.
- Save must succeed before a Save-and-load operation continues.
- Cancel preserves the working configuration and active preset.
- Loading a valid preset changes live mappings without restarting xstudio.
- Startup restores the last selected saved preset, not unsaved experiments.
- Export writes a portable configuration file; import validates a file before
  making it available for use.

Do not partially apply invalid imports or overwrite a saved preset on failure.
Report malformed data, unsupported schema versions, unknown identifiers,
assignment conflicts, unsupported device controls, and I/O failures explicitly.
Do not execute imported content.

The persistence format must be versioned and use stable mode, input, and function
identifiers, not display labels or transient actor handles. Write safely so a
failed save cannot corrupt the last valid preset. Update the startup selection
only after the corresponding saved preset is available.

The user approved the following policies: Factory is read-only; duplicate names
require replacement confirmation; import adds without activation; export uses
the live unsaved configuration without marking it saved locally; load clears
Undo history; missing/corrupt startup selection warns and uses Factory without
overwriting damaged data. The ordinary-button implementation is described above.
Do not silently discard edits or substitute a successful-looking configuration.

## 8. Integration and regression constraints

- Retain the Python-only controller direction and current XInput backend.
- There is one shared input/action owner even with several panel or overlay
  instances; one physical activation dispatches at most once.
- Serialize configuration edits with input resolution. A sample must not
  resolve against a partially updated configuration.
- Give edits a revision or equivalent ordering mechanism so stale UI requests
  cannot overwrite newer configuration undetected.
- Keep QML presentation separate from acquisition and command execution.
- Update binding-dependent guides, modifier indicators, and browse visibility
  from configuration rather than retaining hard-coded Menu/RB assumptions.
- Closing the panel must not disable normal controller operation.
- Preserve existing action semantics, including source activation, selection,
  playback-state preservation, and exposure targeting.
- Disconnect must not change playback, source, or grading/exposure values.
  Clear capture/held state and avoid stale input after reconnect.
- Reconnect with held controls must not immediately invoke their assignments;
  analog neutral/re-arm rules require explicit tests.
- Surface controller, validation, and persistence failures through visible
  feedback and repository-standard logging.

## 9. Logical data contract

The implementation must represent:

| Entity | Required information |
|---|---|
| Saved preset | Schema version, identity/name, supported controller kind, dedicated Shift input, complete explicit bindings |
| Binding | Mode identifier, layer, input identifier, function identifier, any required validated semantic parameters |
| Function catalog entry | Stable identity, display label, available modes, defined input semantics and availability |
| Working state | Selected preset, saved baseline, current validated configuration, dirty state, edit history and revision |
| Runtime state | Connection, active mode/layer, held/neutral state, capture state, latest effective activity and errors |

Runtime connection generations, transient input state, and undo history are not
portable preset mappings. Keep inherited fallback derived from explicit
bindings rather than persisting duplicate connections.

Choose concrete storage and UI bridge shapes using existing repository patterns
after verifying the panel integration path. This specification does not require
a new service, native controller shim, dependency, or general device framework.

## 10. Decision gates before affected implementation

The following were not decided in the brainstorm. Resolve them explicitly
rather than treating a developer guess as an approved behavior change.

| Gate | Decision needed | Affected work |
|---|---|---|
| G1 | Partially resolved: reserved Menu, configurable held Shift default LT (A/Menu excluded), staged RT/Y/A Media checkbox trial, Common/local precedence and duplicate suppression implemented for buttons/triggers. Grouped Viewer navigation approved; full grouped default table remains open | Resolver and initial preset |
| G2 | Discrete trigger trial approved and implemented (>=30 press, <20 release, no repeat, held-input re-arm). Remaining grouped directional adapters and continuous analog semantics still need definition | Capture, validation, analog resolution |
| G3 | Define Grading mode support and Slope/Offset/Power behavior, or explicitly agree how that requirement is staged | Grading adapters and acceptance scope |
| G4 | Decide how manual editing temporarily overrides live mode/layer following | Panel context behavior |
| G5 | Unassigned/Inherit and confirmed undoable Shift reassignment implemented for buttons/triggers. Capture of Shift/grouped/analog controls remains open | Editing transactions |
| G6 | Resolved: read-only Factory, confirmed replacement, non-activating import, live export, fresh history on load, warning/Factory startup recovery | Implemented for ordinary-button scope; full Shift/analog preset schema remains future work |
| G7 | Verify a dockable QML panel can communicate with the shared Python plugin using supported xstudio extension mechanisms | Panel integration |

The panel's full acceptance is blocked until these are resolved and tested.
Implementation can be sequenced around the gates, but unavailable functionality
must not be presented as complete.

## 11. Acceptance criteria

| ID | Scenario and required result |
|---|---|
| A1 | Open the dockable panel beside the viewer. Inspect the active configuration and identify the input assigned to Play/Pause. |
| A2 | Drag Play/Pause to another supported input. The next fresh activation uses the new mapping in the same xstudio process, without Apply or restart. |
| A3 | Capture an input already mapped to an observable action. Assignment changes, but neither the old nor new action executes from the capture gesture. |
| A4 | Within one scope, with A assigned to Play/Pause and B to another supported function, connect A to that function. Displaced explicit assignments are removed; one Undo restores both originals; Redo reapplies the displacement. Common inheritance is resolved separately, never destructively removed by a local edit. |
| A5 | Assign a function in Shifted when it was assigned in Normal in that mode. The former explicit assignment is removed. An assignment of the same function in another mode remains intact. |
| A6 | Hold and release the dedicated Shift button. The layer changes only while held. An input without a Shifted binding uses Normal fallback, visibly identified as inherited. |
| A7 | Press controls while the panel is open. Input, effective connection, and dispatched function highlight once; live mode/layer following obeys the approved editing policy. |
| A8 | Exercise the approved Grading+Shift Slope/Offset/Power mappings with grouped left stick, D-pad, and right stick. Values change according to the agreed semantics and cease appropriately at neutral/context change. |
| A9 | Demonstrate a continuous analog mapping and a button-like analog mapping using approved thresholds. Noise/held values do not produce unintended repeated discrete commands. |
| A10 | Make unsaved edits, then load another preset. Save persists before switching; Discard loads without saving; Cancel changes nothing. A save failure prevents switching. |
| A11 | Save As, restart, and verify exact saved mappings and Shift selection are restored. Unsaved later experiments do not survive restart as saved mappings. |
| A12 | Export/import between clean configurations and verify semantic equivalence. Invalid or incompatible files produce explicit errors and no partial live/persistent changes. |
| A13 | Undo back to the saved configuration clears dirty state; a subsequent differing edit marks it dirty again. |
| A14 | Open multiple panel/overlay instances and close/reopen the editor. Controller actions dispatch once and all views reflect the shared configuration. |
| A15 | Remap, change context, cancel capture, disconnect, and reconnect with controls held/deflected. No synthetic toggle, stale command, stuck continuous action, or disconnect-induced playback/source/value change occurs. |
| A16 | Verify guides and modifier/browse indicators reflect remapped controls rather than obsolete hard-coded assignments. Existing transport, browse/activation, selection, and exposure regressions remain covered. |
| A17 | Verify invalid edits, failed persistence, unknown actions, and unavailable hardware produce explicit feedback while retaining the last valid configuration. |
| A18 | Edit Common and verify inheritance in every mode; override or disable in one mode without changing the others. Inherit restores Common. A local duplicate suppresses the inherited function only in that mode. Provenance and effective guide agree with dispatch. |
| A19 | Load a version-1 preset with deliberate unassigned inputs; preserve its exact behavior without injecting Common defaults. Save/restart/export/import version-2 Common/override/disable configurations without loss. |

## 12. Validation and delivery

Extend the existing controller unit tests with pure configuration validation,
resolver, transaction, history, capture, and persistence tests. Use fake input,
clocks, and action owners to cover both Shift release orders, stale revisions,
displacement across layers, neutral/re-arm behavior, and failure paths.

Baseline targeted test command from the repository root:

```powershell
python -m unittest discover -s python\test\controller_input -p test_controller.py
```

Add targeted test selectors for any new tests and record exact commands/results
when implementing. Add QML/panel integration validation using existing project
tooling after the registration mechanism is established. Automated state checks
must assert the actual effective mappings and dispatched actions, not just that
a UI operation returned success.

Complete a Windows/Xbox runtime trial for live edits, analog behavior, docking,
save/load/restart, and guide synchronization. Existing multi-viewer and
screening-room acceptance remains required; this panel does not substitute for
that trial.

The original specification-writing task was documentation-only. Subsequent
preview implementation and verification are recorded in the implementation
update above and the checklist; physical hardware acceptance remains pending.
