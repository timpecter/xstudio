# Controller plugin brainstorm

Status: requirements captured through brainstorming on 2026-10-23, updated with
the live mapping panel brainstorm on 2026-10-27.
This is a conversation record, not a technical specification or implementation
plan. The panel requirements below have not yet been checked against the
existing controller implementation.

The follow-on [mapping panel specification](controller-mapping-panel-spec.md)
records the agreed panel requirements, current implementation gaps, decision
gates, and acceptance criteria.

## Goal and review setting

Enable a VFX supervisor to drive an xstudio review in a facility screening room
using a handheld controller and the main projector screen, without needing to
sit in front of a workstation monitor.

Before the review, the supervisor logs into the workstation, starts xstudio,
loads a prepared session, connects the controller, and checks that it works.
Configuration can happen at the workstation; operating the review should require
only the controller and projector.

## Initial platform and controller

- Start with Windows and the Xbox controller the user already owns.
- Wiimote support remains a priority for later exploration; the user does not
  currently own a Wiimote.
- Longer-term device interests include PlayStation controllers, MIDI controllers,
  and TouchOSC devices.
- macOS and Linux are future platform targets, not first-release requirements.
- Virtual controllers and a possible virtual Wiimote were raised as testing
  ideas. Their availability and suitability have not been established.

## Action assignment

The original assignment concept was a searchable list of supported actions,
with users choosing an action and learning the controller input to assign.
The live mapping panel described below develops this into a visual wiring
editor with both drag-to-connect and input-capture assignment.

Initial action discovery and assignment should focus on these panels:

- Viewer
- Timeline
- Playlists
- Media

These panel boundaries do not yet constitute an exhaustive action inventory or
a commitment to expose every operation within each panel.

The updated mapping panel input scope is:

- Buttons.
- A dedicated, held Shift button for alternate mappings.
- Analog sticks and triggers, supporting continuous controls and button-like
  commands.
- Sticks and the D-pad represented as whole controls, rather than individually
  wired stick axes or D-pad directions.
- One function per explicit input binding, with uniqueness rules described below.

This expands the original button-focused scope, which deferred analog stick
and trigger-value mappings. Optional hold-to-repeat was previously discussed
for suitable actions; its treatment in the panel is not yet defined. Double
presses, long presses, and multi-action sequences remain deferred.

## Live controller mapping panel

### Purpose and layout

Try different controller mappings without closing and relaunching xstudio.
The panel should be dockable inside xstudio, so the viewer can remain visible
while experimenting.

The visual inspiration is a pair of node-style columns with connective lines,
not a general-purpose node graph:

- Left column: controller inputs, including buttons, grouped sticks, grouped
  D-pad, and triggers.
- Right column: available controller functions.
- Connecting lines: the current assignments, editable by dragging.
- A mode selector, with a Normal / Shifted view switch within each mode.
- Live activity highlights the active input, connection, and triggered function.
  The displayed mode and layer follow the controller's active mode and layer.

The initial function list should use the existing controller functions. A
broader xstudio command catalog is a later extension, not a requirement for
this panel's first version.

### Assignment and live testing

- Mapping edits take effect immediately, without an Apply step or restart.
- Support both dragging an input-to-function connection and selecting a
  function before pressing the desired physical controller input.
- While capturing an assignment, suppress the captured input's existing action.
  Outside capture mode, the controller operates normally for live testing.
- Undo/Redo restores complete mapping edits, including displaced connections.

Assignments are one-to-one within a mode: an input has at most one explicit
function per layer, and a function has at most one explicit assignment across
that mode's Normal and Shifted layers. The same function may be assigned again
in a different mode.

Connecting an already-assigned input or function disconnects the old
connections; it does not swap assignments. For example, if A controls
Play/Pause and B controls Stop, connecting A to Stop leaves B and Play/Pause
unassigned. Undo must restore both original connections.

### Shift layers and grouped controls

- Choose one dedicated Shift button per preset, shared across all modes.
- The shifted layer is active only while Shift is held, not toggled.
- An input without a shifted mapping falls back to its normal mapping.
- That fallback does not constitute a second explicit function assignment.
- Normal and Shifted mappings are viewed separately, rather than displaying
  all connections together.

A concrete desired mapping in Grading mode is:

| Context | Input | Function |
|---|---|---|
| Grading + Shift | Left stick | Slope |
| Grading + Shift | D-pad | Offset |
| Grading + Shift | Right stick | Power |

Each stick and the D-pad has one grouped connection. The precise axis or
direction behavior behind those grouped functions still needs specification.
How sticks and triggers fire button-like commands also remains open.

The first panel version preserves existing sensitivity, dead zones, and
inversion settings. Editing those response settings is a later extension.

### Unresolved panel behavior

- Inventory existing controller inputs, modes, and functions before defining
  the initial catalog and compatibility rules.
- Decide which input/function combinations are valid and how incompatible
  connections appear; no compatibility policy was agreed during brainstorming.
- Define how manual mode/layer selection for editing interacts with live
  mode/layer following.
- Define how input capture works for grouped controls and analog inputs.
- Define how to remove a connection without replacing it.

### Future action-learning workflow

The original inspiration is Ableton Live's MIDI assignment workflow, adapted
to make xstudio actions discoverable:

1. Open an action-capture panel.
2. Perform an action in xstudio.
3. Find the action in a scrolling history.
4. Select that entry and press a controller input to bind it.

This is a future ambition, not essential to the first release.

A discussed design direction is to expose meaningful, supported actions rather
than raw internal messages. An observed action may need interpretation before
it becomes a useful binding: setting exposure to an exact value is different
from increasing exposure, and selecting a particular media item is different
from selecting the next item. The available xstudio infrastructure and the
details of this interpretation remain uninvestigated.

## Modes and global bindings

- Interaction update (2026-10-27): Menu toggles the controller menu open/closed
  on successive presses rather than requiring a hold. While open, D-pad
  Left/Right changes mode; Up/Down browses Playlists/Media and A activates the
  highlighted item. RB+A toggles Media selection. Release and activation leave
  the menu open; a second Menu press closes it. This is separate from the
  planned held Shift layer.
- Support explicit Viewer, Timeline, Playlists, and Media modes.
- The same controller input can have different assignments in different modes.
- Allow global bindings alongside mode-specific bindings.
- Mode selection is intended to provide deliberate controller context rather
  than depend solely on mouse or keyboard focus.
- The mapping panel edits separate Normal and Shifted assignments per mode;
  Grading mode is also included in the desired panel workflow above.

The exact mode-switching controls and rules for resolving overlapping global
and mode-specific bindings remain open. How global bindings interact with the
panel's per-mode uniqueness and Shift rules also needs definition.

## Projector interface

Provide:

- Brief visual confirmation of executed commands.
- An on-demand display of the current mode and its button assignments.
- Browsing overlays in Playlists and Media modes showing list contents and the
  currently selected item.

List navigation must support configurable selection behavior:

- Immediately select items as the user navigates; or
- Move a browsing highlight and confirm before changing the active selection.

The scope of that configuration, overlay layout, timing, and presentation have
not yet been decided.

## Personal configurations and sharing

- Users should be able to save their configuration for a particular controller.
- The expected workflow is personal: the person driving the review logs into
  the workstation and brings their controller.
- Configurations should be saveable and shareable between users.
- Provide named local presets, plus file import/export.
- Live changes are an unsaved working copy until explicitly saved with Save
  or Save As; do not automatically overwrite the selected preset.
- Loading another preset with unsaved edits prompts Save, Discard, or Cancel
  before replacing the live configuration.
- At startup, restore the last selected saved preset, not unsaved experiments.

Storage format, device identification, and automatic device-based profile
selection remain open. File import/export is the agreed transfer mechanism,
but file validation and behavior for incompatible devices or functions still
need definition.

## Disconnect behavior

A controller disconnect must leave playback unchanged.

Connection-status feedback and reconnection behavior still need definition.

## First screening-room acceptance trial

Using only the controller and projector, the supervisor can:

1. Select a playlist from the Playlists panel.
2. Select a media item from the Media panel.
3. Start and stop playback.
4. Select a sequence from the Playlists panel.
5. Make that sequence's timeline the active playback source, rather than
   continuing to play the previously selected media item.
6. Raise and lower viewer exposure.

This is the concrete first-trial success criterion, not the complete eventual
feature set.

## Broader review actions discussed

The initial review ambitions also include:

- Skipping backward and forward between timeline clips.
- Switching timelines and playlists.
- Switching media within playlists.
- Controlling loop and continuous playback.
- Comparing timeline tracks by hiding and revealing them.

Exact semantics and first-release coverage beyond the acceptance trial remain
to be worked out. Specific physical button layouts have deliberately not been
chosen.

## Open technical and product questions

- Which review actions can xstudio expose through existing interfaces?
- How should bindings target the intended viewer, playlist, media selection,
  and active timeline?
- How can projector-visible overlays be integrated?
- What Windows controller support is available?
- How should the dockable mapping panel connect to the existing controller
  implementation so edits take effect live?
- How should assignment conflicts and invalid or unavailable actions be shown?
- How should profiles behave when moved between workstations or controller
  types?
- What technical boundaries will allow future platforms and device types
  without unnecessarily complicating the first version?

No technical investigation, implementation, or controller testing has been
performed as part of these brainstorming conversations. This document does not
supersede separate technical investigations or implementation records.
