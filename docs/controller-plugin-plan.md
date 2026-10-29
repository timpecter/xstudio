# Controller plugin working plan

Menu usability update (2026-10-27): Menu now toggles the controller menu open
and closed on successive presses. Release leaves it open for D-pad mode/browse
navigation, A activation, and RB+A Media selection. Disconnect closes it.
This supersedes historical Menu-held wording below and is separate from the
planned held Shift mapping layer. See the [checklist](controller-todo.md).

Date: 2026-10-24

Status: planning baseline for agent interrogation; not an implementation specification

Implementation and hardware validation: not performed in this planning task

Implementation update (2026-10-25): after confirming the native checkpoint
`98764fa3` works, the user requested a Python-only controller plugin. The current
implementation is in [controller_input](../src/plugin/python_plugins/controller_input),
with standard-library `ctypes` XInput acquisition, a shared Python action owner,
and QML presentation through the existing Python plugin API. No
controller-specific native shim or third-party input package is required.
This supersedes the native-plugin proposal below. See the
[checklist](controller-todo.md) for verification and remaining acceptance work.
The compact mode badge is now Menu-held only; the View guide is independent.
Menu + D-pad Left/Right changes mode. Viewer D-pad Left/Right adjusts
exposure and Up/Down steps the displayed media. Playlists/Media browse only
while Menu is held (Menu + Up/Down, Menu + A). A activates the highlighted playlist or
nested container: it updates the viewer and Media panel and pins timelines. In
Media, A replaces the selection and RB+A toggles the highlighted item in it.
Play/pause state is preserved. User acceptance and the projector trial are
pending.

## 1. Purpose and authority

Enable a supervisor to operate an xSTUDIO screening from a controller and
projector after workstation setup. Start with Windows and the user's Xbox
controller. Keep future platforms and input devices possible without building a
universal device framework.

Read this document alongside:

- [Original brainstorm](controller-plugin-brainstorm.md): original requirements.
- [Architecture assessment](controller-architecture-assessment-2026-10-24.md):
  detailed source investigation, alternatives, and evidence locators.
- [Acceptance-trial API investigation](controller-acceptance-trial-api-investigation-2026-10-24.md):
  action/API traces and limitations.

This plan consolidates those reports, the Windows-input discussion, and the
Evolutionary Architect report supplied by the user. It does not modify the
historical reports or imply that their proposals have all been approved.

Evidence labels:

- **Requirement:** original requirement or behavior described as agreed in the
  user-supplied architect report.
- **Proposal:** recommended default, design, or implementation sequence.
- **Repository evidence:** inspected source/configuration, or a source finding
  attributed to one of the linked investigations; not a runtime guarantee.
- **External documentation:** platform/library claims, with public references;
  not evidence of successful integration in this application.
- **Open:** requires a decision or experiment before the relevant implementation.

When reports disagree, use the explicit decisions recorded below for product
intent. Source findings remain hypotheses about runtime behavior until tested.
Do not silently promote a proposal into an agreed requirement.

## 2. Product decisions and proposed defaults

| ID | Status | Decision |
|---|---|---|
| R1 | Requirement | One review controller drives all viewers, not whichever panel or viewport has keyboard/mouse focus. |
| R2 | Requirement | Source changes apply across viewers. Exposure applies the same relative delta to each viewer's own colour pipeline without replacing independent display configurations. |
| R3 | Requirement | In browse-and-confirm navigation, highlight movement changes neither application selection nor displayed source. Confirming a playlist selects it and activates it for playback. |
| R4 | Requirement | Source changes preserve playing versus paused state. Selecting a sequence activates its pinned timeline, not the previously selected individual media. |
| R5 | Requirement | Controller modes are Viewer, Timeline, Playlists, and Media, independent of panel focus. Assume xSTUDIO owns OS focus during screenings; background operation is not required initially. |
| R6 | Requirement | Start with an Xbox profile; allow selection of another supported controller/profile and saving a personal default. A profile does not implement an input backend. |
| R7 | Requirement | Overlays appear in captures by default, with a profile option to exclude them. Exact capture-path coverage remains open. |
| R8 | Requirement | Disconnect leaves playback unchanged. No stop, source change, or exposure action is caused by disconnect. |
| R9 | Requirement | Buttons, modifier-plus-button combinations, optional suitable repeat, and one semantic action per binding. Profiles are persistent and shareable. |
| P1 | Proposal | Browse-and-confirm is the default; optional immediate navigation performs the same source activation semantics without a separate confirmation. |
| P2 | Proposal | An exact mode-specific binding overrides its global counterpart; configuration and the guide show the override. Reject duplicates within one scope. |
| P3 | Proposal | Dedicated modifier buttons initially have no standalone action. Repeat is opt-in only for suitable actions, such as navigation and exposure, never confirmation or playback toggles. |
| P4 | Proposal | Match application list order; add no controller-only search/filter initially. Show brief automatic command feedback and an on-demand button guide. |
| P5 | Proposal | Remember the user's chosen default profile and explicitly report unsupported devices, controls, actions, and invalid profiles. |

Physical button assignments and mode-switch controls remain configurable and
subject to controller trials. The architect report's recommended binding rules
and defaults are retained as proposals, not retroactively treated as approvals.

Deferred: analog mappings, double/long presses, user-programmable action
sequences, learning actions by observing arbitrary UI operations, and exhaustive
action exposure. Future interests include PlayStation, Wiimote, MIDI, TouchOSC,
macOS, and Linux; none is an initial backend commitment.

## 3. Reconciliation and important corrections

1. **Backend recommendation differs between reports.** The earlier input answer
   favored SDL3 for a prototype expected to grow; the architecture assessment
   favors XInput 1.4 for the smallest Windows/Xbox risk slice. Neither is a user
   decision. This plan proposes XInput first because cross-platform delivery is
   deferred and the immediate risks are application integration, not gamepad
   coverage. SDL3 is the leading alternative when broader gamepad/platform
   support becomes a near-term requirement. Do not implement both initially.
2. **All viewers supersedes single-target assumptions.** A named or active
   viewport is not the product target. Global-playhead broadcasting alone does
   not establish that independently attached viewers will change.
3. **Source activation is more than selection.** Inspection, viewed container,
   media selection, timeline pinning, and actual viewer attachments are distinct.
   API request acknowledgement alone is not completed activation.
4. **Shared state is essential.** All overlay instances display one browsing
   state and mode; they must not each consume input or execute commands.
5. **Capture inclusion is not automatic.** A normal viewport QML overlay does
   not prove that offscreen, snapshot, movie, or video-output paths include it.
6. **State preservation needs a policy for divergent viewers.** If viewers
   initially disagree about playing/paused state, preserving one review state
   and preserving every old state are different behaviors. This remains open.

## 4. Evidence and dependency implications

### Repository evidence

The Windows setup uses CMake and vcpkg, with Visual Studio and Ninja presets.
The inspected local Windows cache used Ninja, Release, `x64-windows`, Qt 6.5.3,
and `X_VCPKG_APPLOCAL_DEPS_INSTALL=ON`. These are local build observations, not
minimum supported versions. See [presets](../CMakePresets.json),
[manifest](../vcpkg.json), and [Windows build script](../scripts/build_windows.ps1).

The inspected manifest has no direct SDL3/controller dependency. Bounded source
searches found no existing dedicated gamepad backend. Native plugin and QML
installation conventions exist in [CMake macros](../cmake/macros.cmake).
Windows has an NSIS packaging configuration and a portable staging target;
[Qt deployment](../scripts/qt_install/CMakeLists.txt) invokes `windeployqt`.
[Portable staging](../scripts/portable/portable.cmake.in) checks core paths and
prunes development artifacts, but is not a controller-runtime dependency test.

The linked architecture/API investigations report:

- Resident native plugins, module attributes, preferences, and viewport-wide QML
  provide integration hooks, not a finished controller UI or action catalogue.
- Inspected and viewed containers are separate. `Session.set_on_screen_source`
  must not be assumed equivalent to setting `viewed_container`.
- Sequence activation must include pinned-source mode. Viewing a timeline alone
  does not prove the timeline is the effective source.
- Viewers may opt out of following the global playhead.
- Exposure is a per-pipeline value; the existing exposure hotkey is a mouse
  scrubbing interaction, not a suitable relative controller command.
- Offscreen output has separate rendering/QML considerations.

Those findings are attributed to the investigations; recheck affected source
against the implementation revision rather than treating locators as stable APIs.

### External documentation and proposed application consequences

The following platform claims are documented externally and were referenced in
the earlier assessment. They were not independently revalidated during this
document consolidation. Recheck versions, terms, and deployment instructions
before selecting a package.

| Option | External documentation | Proposed consequence for xSTUDIO |
|---|---|---|
| XInput 1.4 | Windows SDK API and inbox Windows runtime; state polling, up to four indexed controller slots, disconnected-device result. Windows-only. | Call the inbox DLL with Python `ctypes`. No new third-party controller DLL to bundle. Implement button edges, disconnect detection, reconnect baseline, and polling cadence. Slots are not persistent personal identities. |
| GameInput | Windows input API with polling/callbacks and device notification/focus facilities; package/runtime deployment requirements. | Add explicit SDK/package integration and verify current runtime redistribution requirements for both installer and portable use. Do not assume vcpkg app-local copying provisions its runtime. No macOS/Linux solution. |
| SDL3 | Gamepad mappings, lifecycle/input events, and Windows/macOS/Linux support. Input update/event pumping has threading and subsystem requirements. | Add a version-controlled dependency through the existing vcpkg setup; verify availability at the pinned baseline or select an explicit supported version. Link SDL3 and test Qt coexistence. With dynamic linkage, stage the runtime and notices for both Windows packages; audit macOS bundle and Linux runtime packaging later. |

Sources: [XInput versions](https://learn.microsoft.com/en-us/windows/win32/xinput/xinput-versions),
[XInputGetState](https://learn.microsoft.com/en-us/windows/win32/api/xinput/nf-xinput-xinputgetstate),
[GameInput package](https://www.nuget.org/packages/Microsoft.GameInput),
[SDL3 gamepad API](https://wiki.libsdl.org/SDL3/CategoryGamepad),
[SDL_UpdateGamepads](https://wiki.libsdl.org/SDL3/SDL_UpdateGamepads),
[SDL background-input setting](https://wiki.libsdl.org/SDL3/SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS).

Qt deployment does not deploy arbitrary controller runtimes. Test installed and
portable outputs on a clean non-development Windows environment. XInput and
GameInput need replacement backends for other platforms; SDL portability does
not guarantee every device or pairing method works. Wiimote needs a separate
hardware/protocol investigation. SDL3 is not a MIDI or OSC backend.

## 5. Proposed architecture and event boundary

Use one application-owned Python plugin with QML presentation/configuration. Keep four
responsibilities separate without introducing services or a general event bus:

1. **Input adapter:** acquire native input and connection status.
2. **Binding resolver:** modes, modifiers, scoped bindings, learning, and repeat.
3. **Action adapter:** supported semantic actions, target resolution, completion,
   and visible failure results.
4. **Presentation:** shared browsing/mode/result state rendered by each output.

Proposal for a small device-neutral event contract:

| Field | Meaning |
|---|---|
| Source instance | Runtime connection identity, including a generation to reject stale events after reconnect; separate from saved profile/controller family. |
| Event kind | Connected, disconnected, control change, or explicit source error. |
| Control address | Namespaced logical control, not an SDK enum: e.g. `gamepad/button/south`, a MIDI channel/note/controller address, or an OSC path. |
| Typed payload | Initially button down/up. Extend with continuous, relative, or typed message payloads only when an adapter needs them. |
| Ordering | Monotonic timestamp and per-source ordering sufficient for deterministic resolver tests. |
| Device metadata | Optional capabilities and display labels; do not require a persistent hardware serial number. |

Keep XInput structures, SDL IDs, actor addresses, and QML objects out of this
contract. MIDI/OSC adapters can later map their native semantics explicitly;
do not encode everything as a fake gamepad button. Future OSC transport,
validation, and access policy are separate work.

The resolver emits semantic action requests, not keyboard events. Profiles store
versioned action/control identifiers and options, not transient slots or actor
addresses. A small explicit supported-action catalogue owns availability,
parameters, repeat permission, and result semantics.

Use bounded scheduled polling for XInput, not a blocking UI/CAF loop. Stop all
scheduled work on disable/shutdown. Disconnect cancels held state, modifiers,
repeat, and queued device input without dispatching actionable releases.
Reconnect requires a neutral baseline. Learning suppresses ordinary dispatch;
mode/profile changes cancel repeat. A synthetic input source and fake clock
provide a test seam, not a second production backend.

Action execution coordinates source activation and readiness before dependent
transport commands. Use bounded completion checks and reject stale asynchronous
results; do not copy fixed UI delays. Deduplicate shared playheads/pipelines so
one command is not applied twice. Report unavailable targets, timeouts, and
partial failures visibly rather than displaying success.

## 6. Implementation sequence and exit evidence

| Stage | Deliverable | Exit evidence |
|---|---|---|
| 0: resolve targeting | Enumerate intended viewers/output paths; define divergent playback-state policy and the projection/capture path. | Concrete fixture and target matrix, with named completion signals for source activation and timeline pinning. |
| 1: thin risk slice | Windows/Xbox adapter, minimal bindings, four modes, shared browse-and-confirm overlay, source activation, transport, and relative exposure. | Controller/projector-only trial reaches a playlist, media item, and pinned sequence across follower and independent viewers; state preservation and disconnect pass; overlay appears in an agreed capture. |
| 2: configurable workflow | Searchable supported actions, input learning, global/mode bindings, modifiers, suitable repeat, profile save/default/import/export, capture exclusion option. | Resolver/profile tests and explicit unsupported-device/error feedback; agreed precedence and schema validated before sharing profiles. |
| 3: package acceptance | Immediate-navigation alternative, output coverage, guide/feedback, lifecycle and packaged runtime validation. | Both installed and portable Windows distributions pass the agreed hardware/projector/capture matrix without workstation interaction after setup. |

Temporary fixed bindings are acceptable for Stage 1 only. Do not make broad
profile-editor work a prerequisite for proving the risky application behavior.
Do not defer basic capture feasibility until packaging.

## 7. Acceptance and regression checklist

- [ ] Browsing alone changes neither selection nor source; confirmation activates
  the chosen playlist. Immediate mode uses the same activation semantics.
- [ ] Media confirmation targets the intended container and item, not a stale
  row or an unrelated playhead selection.
- [ ] Starting from individual media and an unpinned sequence, sequence
  confirmation visibly activates the pinned timeline in every intended viewer.
- [ ] Source changes preserve playing/paused state under the agreed policy,
  including rapid successive activation and asynchronous completion.
- [ ] Independent viewers and global followers are both tested; multiple
  overlays never cause duplicate command execution.
- [ ] Relative exposure applies once per distinct pipeline, respects attribute
  limits, and preserves other display settings.
- [ ] Mode/global precedence, dedicated modifiers, one dispatch per press, and
  permitted repeat work with a fake clock and both modifier release orders.
- [ ] Disconnect during playback, pause, repeat, or a modifier hold changes no
  source/transport/exposure state; playback continues naturally if playing.
- [ ] Reconnect with held buttons produces no action until neutral; stale events
  and repeat timers cannot affect the new connection.
- [ ] Empty/deleted/reordered lists, session replacement, missing pipelines,
  invalid profiles, timeouts, and partial failures produce explicit feedback.
- [ ] Guide, highlights, and feedback are readable on the actual projector,
  update while paused/empty, and work independently of panel focus.
- [ ] Agreed capture paths include overlays by default and honor exclusion.
- [ ] Plugin disable/shutdown, wired/wireless input, hot-plug, dialog/fullscreen
  focus, and both Windows package formats pass on the intended setup.

Use existing GTest/CTest infrastructure and targeted tests. See the
[Windows build/test guide](reference/build_guides/windows.md). Controller test
targets do not yet exist; record exact commands and results when implemented.
Automated tests cannot substitute for hardware, projection, and capture trials.

## 8. Questions for interrogating agents

Before implementation, answer or explicitly defer each relevant question:

1. Which main, secondary, independent, quickview, and video-output viewers are
   controlled? Which snapshot/export renderers merely consume shared overlay
   state? What happens when viewers open or close?
2. If initial viewer transport states differ, what state does a source change
   preserve? Is one review transport authoritative? What about position, range,
   loop mode, speed, and direction?
3. Which existing source-activation path preserves session bookkeeping and
   proves timeline pinning plus actual attachments? What signals prove readiness?
4. How are shared pipeline identities handled? What is the exposure increment,
   clamping behavior, and partial-failure policy?
5. Which projection and capture paths must work first, and how does the profile
   exclusion flag reach each render path without taking over transient renderers?
6. Are proposed precedence, modifier, repeat, and navigation defaults approved?
   How do list hierarchy and existing application filters affect browsing?
7. What is the supported Windows floor, actual controller/connection method,
   polling target, and acceptable input latency? Does hardware testing support
   choosing XInput, or reveal a concrete reason to select SDL3 instead?
8. Which profile schema and stable action/control IDs can safely be shared?
   How are unknown versions/actions and unsupported device profiles presented?

Agents should cite source paths/symbols or authoritative external documentation,
state whether evidence is static or runtime, identify affected requirement IDs,
and propose the smallest experiment that resolves each uncertainty. Do not
claim another backend, capture path, or viewer type works solely because an API
exists.
