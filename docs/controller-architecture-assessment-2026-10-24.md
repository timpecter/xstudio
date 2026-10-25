# Controller-driven screening-room architecture assessment

Date: 2026-10-24  
Status: investigation and recommendations; not an implementation specification  
Repository: AcademySoftwareFoundation/xstudio  
Source revision at document creation: `d9976754f30e3791304419c387960e910acd24dd`  
Branch at document creation: `develop`

## Purpose and evidence status

Assess an incremental controller-driven screening-room workflow for a VFX
supervisor operating through a handheld controller and projector. Workstation
setup and configuration happen before the review.

This document consolidates the repository investigation and subsequent user
decisions from the conversation on 2026-10-24. The
[controller brainstorm](controller-plugin-brainstorm.md), dated 2026-10-23, is the
source of original requirements, ambitions, and open questions. It is not a
technical specification. Later explicit user decisions below refine it.

Evidence labels used throughout:

- **Verified:** source or documentation inspected during the investigation.
  This does not mean the behavior has been demonstrated at runtime.
- **Agreed:** explicitly stated by the user.
- **Recommended:** proposed architecture or behavior, not automatically agreed.
- **Unresolved:** requires a product decision, experiment, or further tracing.

No application implementation, controller testing, runtime UI validation,
dependency installation, or automated test execution was performed for this
assessment. Only this assessment document was added when requested. The
worktree already contained unrelated untracked files, including the brainstorm;
the revision above alone does not capture those files.

Links below are relative to this document. Symbol names and line numbers are
search locators from the investigation, not stable API guarantees. Future agents
must recheck affected code against their working revision.

## 1. Requirements and decision record

### Original requirements to preserve

- Initial platform: Windows and the user's Xbox controller.
- Explicit Viewer, Timeline, Playlists, and Media controller modes, independent
  of mouse/keyboard panel focus.
- Global bindings alongside mode-specific bindings.
- Buttons, modifier-plus-button combinations, optional hold-to-repeat, and one
  semantic action per binding.
- Searchable supported-action selection plus controller-input learning.
- Brief command confirmations, an on-demand mode/button guide, and navigable
  Playlists and Media overlays on the review output.
- Configurable immediate selection versus browsing highlight plus confirmation.
- Personal, persistent, shareable controller configurations.
- Controller disconnect leaves playback unchanged.
- Deferred: analog mappings, double/long presses, user-programmable action
  sequences, and capturing actions performed in the UI.
- Future interests: Wiimote, PlayStation, MIDI, TouchOSC, macOS, and Linux.
  These do not justify a universal device framework in the initial release.

### Explicit user decisions on 2026-10-24

| Topic | Agreed decision | Qualification |
|---|---|---|
| Viewer targeting | "All viewers." | Supersedes the investigation's earlier proposal to configure a single review viewport. The exact treatment of independent/offscreen viewers still needs definition. |
| Playlist navigation | Navigate the on-screen overlay, then select a playlist; selection changes the displayed source. | Browsing highlight is provisional in browse-and-confirm operation. Immediate selection remains a configurable alternative from the brainstorm. |
| Playback during source changes | Preserve playback state. | At minimum, preserve playing versus paused. Position, range, rate, and direction semantics are not fully specified. |
| OS focus | Other applications normally do not require focus during a screening. | Foreground xstudio is an acceptable initial operating assumption; do not promise background operation. |
| Profiles/default controller | Start with Xbox; allow the user to choose something else and save it as their default. | Selecting a device/profile is not a promise that an unsupported backend already exists. |
| Capture presentation | Overlays appear in captures by default. | Capture types and any exclusion option still require precise scope. |
| Other profile options | The user supported including options in profiles, but was unsure about other defaults. | Do not treat the assistant's proposed defaults below as approved product decisions. |

### Subsequent recommendations, not explicit user approvals

- Apply exposure commands to each target viewer's own colour pipeline using the
  same relative adjustment, without copying independent display configurations.
- Share one controller browsing/mode state across viewer overlay instances.
- Default to browse-and-confirm and match existing xstudio list order.
- Remember a manually chosen default profile; show unsupported-device problems.
- Let an exact mode-specific binding override an identical global binding,
  visibly showing the shadowing in configuration and help.
- Reject duplicate bindings within a scope.
- Reserve dedicated modifier buttons initially; avoid guessing whether a press
  is a standalone action or the beginning of a chord.
- Permit repeat for navigation/exposure, not confirmation or playback toggles.
- Provide an option to exclude overlays from captures, while including them by
  default.

The physical button layout and mode-switch controls have not been chosen.

## 2. Executive recommendation

**Recommended:** use an in-process resident native plugin with QML configuration
and review overlays, a concrete supported action subset, and a small replaceable
input adapter. Begin with XInput 1.4 for the Windows/Xbox trial.

The highest-risk assumptions are playback targeting across all intended viewers,
timeline pinning, and projector-visible navigation. Do not start with an
exhaustive action catalogue, elaborate profile editor, or generic device system.

The initial architecture should separate:

1. Device button/connection acquisition.
2. Mode, binding, modifier, learning, and repeat resolution.
3. Concrete xstudio targeting and supported action execution.
4. Presentation of shared state in configuration and viewer overlays.

These are responsibilities within one plugin, not a proposed service network.

## 3. Reusable infrastructure and repository evidence

### Plugin lifecycle, threading, UI, and packaging

| Verified infrastructure | Evidence and locator | Reuse and limits |
|---|---|---|
| Native discovery and factories | [plugin_manager.cpp](../src/plugin_manager/src/plugin_manager.cpp), `PluginManager::load_plugins`, line 46; [plugin_factory.hpp](../include/xstudio/plugin_manager/plugin_factory.hpp), `PluginFactoryTemplate`, line 79 | Platform library loading and `plugin_factory_collection_ptr` factory export already exist. Factories identify plugin type, UUID, version, and residency. |
| Installation/environment paths | [plugin_manager_actor.cpp](../src/plugin_manager/src/plugin_manager_actor.cpp), constructor, line 27 | Installation paths plus `XSTUDIO_PLUGIN_PATH`; Windows uses semicolon-separated environment paths. |
| Resident enable/disable | [plugin_manager_actor.cpp](../src/plugin_manager/src/plugin_manager_actor.cpp), `PluginManagerActor::enable_resident`, line 492 | Creates/registers/links resident actors and sends shutdown on disable. |
| Actor/module base | [plugin_base.hpp](../include/xstudio/plugin_manager/plugin_base.hpp), `StandardPlugin`, line 84; [plugin_base.cpp](../src/plugin_manager/src/plugin_base.cpp), `StandardPlugin::on_exit`, line 187 | CAF event-based actor plus `Module`; module cleanup exists. Controller timers/workers must explicitly stop during disable/exit. |
| UI panels and widgets | [module.hpp](../include/xstudio/module/module.hpp), `register_ui_panel_qml`, line 340; `register_viewport_dockable_widget`, line 350 | Reuse QML registration, attributes, menus, and configuration panels. |
| Viewport-wide QML | [plugin_base.cpp](../src/plugin_manager/src/plugin_base.cpp), `StandardPlugin::qml_viewport_overlay_code`, line 462 | Registers an attribute in `viewport_overlay_plugins`. Suitable extension hook, not a ready-made navigation interface. |
| Native/QML packaging | [macros.cmake](../cmake/macros.cmake), `default_plugin_options`, line 171; `add_plugin_qml`, line 228; `create_plugin`, line 407 | Existing CMake conventions install plugin libraries and QML. Windows paths and installed dependencies still need package testing. |
| Exported build targets | [xStudioConfig.cmake.in](../xStudioConfig.cmake.in); [CMakeLists.txt](../CMakeLists.txt), exported package setup | Out-of-tree consumption is supported structurally. Do not infer stable native ABI compatibility across versions/build configurations. |
| Existing native utility example | [session snapshots CMake](../src/plugin/utility/session_snapshots/src/CMakeLists.txt); [snapshot_model_ui.cpp](../src/plugin/utility/session_snapshots/src/snapshot_model_ui.cpp), resident utility factory near line 397 | Prior art for a native utility with QML integration. |
| Python plugin alternative | [python_plugins.rst](user_docs/appendix/python_plugins.rst), lines 45-52; [plugin_base.py](../python/src/xstudio/plugin/plugin_base.py), `PluginBase.add_attribute`, line 62; `register_ui_panel_qml`, line 345 | Separate interpreter thread, startup plugin discovery, preference-backed attributes, QML support. Not a reason to run a blocking polling loop in the shared interpreter. |
| Python lifecycle | [module.py](../python/src/xstudio/api/module.py), `ModuleBase.cleanup`, line 619; [connection module](../python/src/xstudio/connection/__init__.py), `Connection.disconnect`, line 484 | Cleanup hook can close/join workers. Connection shutdown invokes plugin cleanup. |

**Recommended threading:** scheduled, bounded polling work owned by the plugin.
Do not block Qt UI/render threads or occupy a CAF scheduler thread with a
continuous loop. If a worker becomes necessary, it should emit messages and have
explicit shutdown/join behavior; it must not touch QML objects across threads.
For initial XInput polling, do not introduce a worker just to create an
abstraction.

Native integration avoids an additional Python controller dependency and
worker/GIL coordination. Python remains a viable prototyping route, not an
architectural prerequisite.

### Action discovery and execution

| Verified mechanism | Evidence and locator | Consequence |
|---|---|---|
| Searchable registered hotkeys | [hotkey_ui.cpp](../src/ui/qml/viewport/src/hotkey_ui.cpp), `HotkeysUI::makeFilteredHotkeysData`, line 127; [XsHotkeysDialog.qml](../ui/qml/xstudio/application/dialogs/hotkeys/XsHotkeysDialog.qml), search near line 61 | Searchable hotkey metadata exists. It is not a verified universal supported command catalogue. |
| Module hotkeys and callbacks | [module.hpp](../include/xstudio/module/module.hpp), `register_hotkey`, line 148; [module.cpp](../src/module/src/module.cpp), hotkey dispatch near line 839 | Useful prior art, but callbacks carry context/window and can have press/release semantics. |
| Focus/context-sensitive keyboard handling | [keypress_monitor.cpp](../src/ui/viewport/src/keypress_monitor.cpp), `held_keys_changed`, line 388; [hotkey_ui.cpp](../src/ui/qml/viewport/src/hotkey_ui.cpp), context filtering near line 384 | Keyboard synthesis would inherit context and focus coupling. Avoid it as the core controller execution mechanism. |
| Container inspection/viewing API | [session.py](../python/src/xstudio/api/session/session.py), `Session.viewed_container`, line 98; `inspected_container`, line 139 | Existing semantic distinction can be reused through the API or equivalent native paths. |
| Media selection API | [playhead_selection.py](../python/src/xstudio/api/session/playhead/playhead_selection.py), `PlayheadSelection.set_selection`, line 61 | Reuse selection operations, validating container and media identity. |
| Transport API | [playhead.py](../python/src/xstudio/api/session/playhead/playhead.py), `Playhead.playing`, line 35 | Start/stop the resolved playback target, not an arbitrary cached playhead. |
| Viewport/playhead APIs | [viewport.py](../python/src/xstudio/api/intrinsic/viewport.py), `Viewport.set_playhead`, line 131; [app.py](../python/src/xstudio/api/app.py), `set_global_playhead`, line 113 | Direct attachment and global following exist, but bypassing session bookkeeping can create inconsistent targeting. |
| Exposure API | [viewport.py](../python/src/xstudio/api/intrinsic/viewport.py), `colour_pipeline`, line 59; [colour_pipeline.py](../python/src/xstudio/api/intrinsic/colour_pipeline.py), `ColourPipeline.exposure`, line 35 | Existing per-viewport colour-pipeline attribute can support relative commands. |
| Exposure semantics | [ocio_plugin.cpp](../src/plugin/colour_pipeline/ocio/src/ocio_plugin.cpp), exposure initialization, line 768; `hotkey_pressed`, line 390 | Exposure has range/step/redraw metadata. Exposure hotkey activates mouse scrubbing and checks viewport context; it is not an exposure-increment command. |

**Conclusion:** provide an explicit supported action subset with stable action
IDs, labels/categories, availability checks, target policies, and repeat
permissions. Reuse existing behavior behind those actions. Hotkey metadata can
inform labels and future discovery, but neither raw actor messages nor arbitrary
attributes are automatically safe, discoverable commands.

Profiles should store semantic IDs rather than transient hotkey UUIDs, actor
addresses, model row numbers, or user-supplied internal messages. UI action
capture is deferred: observing a message does not establish a reusable command.

## 4. Selection, navigation, and playback targeting

### Distinct states

| State | Meaning |
|---|---|
| Controller mode | Viewer, Timeline, Playlists, or Media binding context. |
| UI focus | Keyboard/mouse routing within xstudio; not controller mode. |
| Browsing highlight | Provisional overlay cursor, with no application selection/source change before confirmation in browse-and-confirm operation. |
| Session selection | Selected playlist/subset/timeline objects; can participate in multi-timeline behavior. |
| Inspected container | Container whose contents are being inspected in application panels. |
| Media selection | Selected media in a container's playhead-selection object. |
| Viewed container | Container selected to drive the session's on-screen playhead. |
| Actual playback source | Playhead attached to each viewer and its effective sources, including whether a timeline is pinned or playing selected media. |

**Verified trace:**

1. [XsSessionData.qml](../ui/qml/xstudio/application/model/XsSessionData.qml),
   session selection near line 270, sets the inspected container. Media selection
   near line 357 separately updates the playhead-selection object.
2. [SessionModel::setCurrentMediaContainer](../src/ui/qml/session/src/session_model_methods_ui.cpp),
   line 1705, sends `active_media_container_atom`.
   `setViewportCurrentMediaContainerIndex`, line 1724, instead sends
   `viewport_active_media_container_atom`.
3. [SessionActor](../src/session/src/session_actor.cpp), inspected-container
   handler at line 1586, only defaults the viewed container when none exists.
   Changing inspection normally does not change the existing playback source.
4. The viewed-container handler at line 1623 calls `setOnScreenPlayhead`, line
   2793, which asynchronously obtains the container's playhead and broadcasts it
   through the global playhead-events actor.
5. [XsTimelinePanel.qml](../ui/qml/xstudio/application/panels/timeline/XsTimelinePanel.qml),
   activation path near line 268, makes the timeline viewed and sets
   `pinnedSourceMode = true`.
6. [XsMediaListMouseArea.qml](../ui/qml/xstudio/application/panels/media/widgets/XsMediaListMouseArea.qml),
   near lines 55 and 106, sets the viewed container but can unpin a timeline to
   display individual selected media. These UI paths use delayed callbacks.
7. [PlayheadActor](../src/playhead/src/playhead_actor.cpp), near line 2872,
   rebuilds source lists when pinning changes.
8. [SessionActor::check_multi_timeline_mode](../src/session/src/session_actor.cpp),
   line 2674, can introduce a comparison playhead based on session selection.

**Risk:** selecting a sequence, or even observing its viewed-container identity,
does not alone prove that its timeline is supplying the review output.

### Recommended semantic activation operation

An "activate selected sequence" action should resolve the target by identity,
update intended selection/inspection, make the sequence viewed, ensure timeline
pinning, and verify actual viewer attachment before reporting completion or
executing dependent transport commands.

This is one semantic action per binding, even if internally it coordinates
several application operations. It is not a user-programmable action sequence.

Preserve playing/paused state across activation. Do not assume the new playhead
inherits it. Avoid reading one old target and accidentally restoring state onto a
stale target after a rapid second activation.

Use state/event confirmation with a bounded timeout, not copied fixed 200 ms UI
delays. Some existing handlers acknowledge initiation or use asynchronous
callbacks; an acknowledgement alone is not source readiness. Errors must be
visible on the projector, not success-shaped confirmations.

### All-viewer implications

The earlier single named-review-viewport recommendation is superseded.

[playhead_global_events_actor.cpp](../src/playhead/src/playhead_global_events_actor.cpp),
global playhead updates near line 187 and named viewport queries near line 312,
provides useful coordination infrastructure.
[Viewport](../src/ui/viewport/src/viewport.cpp), global-update handler near line
1235, only changes attachment when its synchronization setting permits it.
`auto_connect_to_global_selected_playhead`, line 544, explicitly distinguishes
normal following from quickview/snapshot use.

**Unresolved:** "all viewers" must be mapped to actual output types. Do not
silently interpret it as only current global followers, or blindly take over
snapshot/export renderers. Enumerate intended viewers and test independent
viewers as well as followers. Define behavior for viewers opened or closed
during a screening.

For exposure, the recommended interpretation is a relative adjustment in each
target's own pipeline. Reconcile duplicate/shared pipeline identities before
dispatch so a single pipeline is not adjusted twice. Missing pipelines should
be reported, not silently ignored.

## 5. Projector overlays and captures

**Verified:** [XsViewportOverlays.qml](../ui/qml/xstudio/application/panels/viewport/hud/XsViewportOverlays.qml),
near line 14, instantiates viewport-wide plugin QML from the
`viewport_overlay_plugins` attribute group. It is distinct from per-image HUDs
and is not controlled by the ordinary HUD on/off toggle.

[XsHudItem.qml](../ui/qml/xstudio/application/panels/viewport/hud/XsHudItem.qml)
provides dynamic QML instantiation.
[OnScreenVersionNameOverlay.qml](../src/plugin/python_plugins/on_screen_version_name/qml/OnScreenVersionName.1/OnScreenVersionNameOverlay.qml),
near line 45, demonstrates timer-based disappearance.

**Gap:** these hooks/examples do not provide controller-driven hierarchical
playlist/media navigation. A new review overlay is required.

Recommended content:

- Confirmed command result, including playback source or resulting exposure.
- On-demand current mode and effective button bindings.
- Playlists/sequences and Media views using existing application identities and
  data, not a second authoritative session model.
- Visually distinct browsing highlight, selected item, and on-screen source.
- Visible connection status and actionable unavailable-action/error feedback.

All overlay instances consume shared plugin state. They do not each process
input or dispatch actions. UI navigation must work without keyboard focus or a
mouse, with readable type and selection indication at screening-room distance.
Test updates while paused and when no media is loaded.

**Output-path caveat:** [XsOffscreenViewportOverlays.qml](../ui/qml/xstudio/application/panels/viewport/XsOffscreenViewportOverlays.qml),
near line 40, documents a separate QML engine.
[offscreen_viewport.cpp](../src/ui/qt/viewport_widget/src/offscreen_viewport.cpp),
near line 612, creates a separate thread; overlay inclusion is conditional near
line 1129. Desktop/fullscreen, secondary viewers, DeckLink, snapshots, and movie
rendering must not be assumed equivalent.

Pass serializable/attribute-backed presentation state rather than references to
workstation QML objects. Verify the actual projection chain. Capture inclusion
is agreed as the default, but implementation must determine which capture paths
include the overlay and how review-state filtering works there.

## 6. Preferences and shareable profiles

**Verified:** [preference_files.rst](user_docs/appendix/preference_files.rst),
line 41, documents JSON user preferences, periodic/exit saves, and startup
`--pref` overrides. Its documented user directory is
`$HOME/.config/DNEG/xstudio`; confirm actual platform resolution before coding a
path. Defaults in this checkout are under [share/preference](../share/preference).

[module.cpp](../src/module/src/module.cpp), near line 1274, propagates
preference-backed attributes. [GlobalStoreActor](../src/global_store/src/global_store_actor.cpp),
save handler near line 25, uses temporary-file replacement.

No ready-made controller profile import/export workflow was identified.

**Recommended:**

- Versioned JSON controller profiles with semantic action/button identifiers,
  scoped bindings, repeat settings, and presentation/navigation options.
- Preferences store personal defaults and the chosen active/default profile.
- Explicit import/export of the controller profile only; do not export unrelated
  preferences, credentials, session actor addresses, or transient device slots.
- Validate unknown actions, unsupported controls, incompatible schema versions,
  duplicates, and shadowing before activation; show failures explicitly.
- Store controller family separately from the transient connected device.
- Begin with explicit/manual profile selection. XInput slot numbers are not a
  robust identity for automatic personal-device matching.

Default suggestions remain recommendations: browse-and-confirm, matching
application order, no separate controller-only filter, brief result feedback,
on-demand help, and capture overlays included.

## 7. Windows input options and portability

No existing controller backend or XInput/SDL/gamepad dependency was found in the
inspected native source and [vcpkg.json](../vcpkg.json). This is a bounded search
finding, not a proof that no incidental controller-related code can exist.

| Option | Benefits | Costs, focus, and packaging considerations |
|---|---|---|
| XInput 1.4 | Recommended for first Windows/Xbox trial. Inbox Windows DLL; SDK headers/import library; no third-party controller runtime to distribute. State polling supports button transitions and disconnect detection. | Xbox-compatible devices, up to four indexed slots; no dependable persistent personal-device identity. Must implement edges, polling cadence, reconnect baseline, and focus testing. Windows SDK use remains subject to its terms, not an added open-source controller library licence. |
| SDL3 | Broader gamepad/platform coverage and mappings; permissive zlib licence. | New pinned build/package dependency, notices, subsystem/update lifecycle, and Qt coexistence tests. Background events have an explicit setting, disabled by default. Audit supported device/backend behavior rather than assuming every controller works. |
| Microsoft GameInput | Modern polling/callback API, device notifications, and explicit focus policy; broader Windows device handling. | NuGet integration and runtime deployment/redistribution review. Official package notes distinguish MIT public headers/static library from runtime deployment; do not assume the whole runtime is MIT. Windows-specific rather than a macOS/Linux portability solution. |

Authoritative external references consulted on 2026-10-24:

- Microsoft: [Getting started with XInput](https://learn.microsoft.com/en-us/windows/win32/xinput/getting-started-with-xinput).
- Microsoft: [XInput versions and inbox deployment](https://learn.microsoft.com/en-us/windows/win32/xinput/xinput-versions).
- Microsoft: [XInputEnable and focus](https://learn.microsoft.com/en-us/windows/win32/api/xinput/nf-xinput-xinputenable).
- SDL: [background joystick/gamepad events](https://wiki.libsdl.org/SDL3/SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS).
- SDL: [SDL_UpdateGamepads](https://wiki.libsdl.org/SDL3/SDL_UpdateGamepads).
- SDL: [licence](https://www.libsdl.org/license.php).
- Microsoft: [GameInput introduction](https://learn.microsoft.com/en-us/gaming/gdk/docs/features/common/input/overviews/input-overview).
- Microsoft: [GameInput package/deployment notes](https://www.nuget.org/packages/Microsoft.GameInput).
- Microsoft: [IGameInput::SetFocusPolicy](https://learn.microsoft.com/en-us/gaming/gdk/docs/reference/input/gameinput/interfaces/igameinput/methods/igameinput_setfocuspolicy).

These lookups used public documentation; repository content was not submitted
to an external research service. Versions/terms should be rechecked when a
dependency is actually selected.

### Initial input behavior

Recommended implementation rules:

- Poll the selected controller with bounded scheduled work; probe missing slots
  less frequently.
- Emit normalized button transitions and connection status. Keep raw Windows
  structures out of bindings/action execution.
- Generate hold-to-repeat from held state and a clock, not only changed XInput
  packet numbers.
- On disconnect, cancel modifiers/repeat and discard pending device inputs.
  Do not send stop, source-change, or synthetic actionable release commands.
- On reconnect, require a neutral baseline before accepting button presses.
- Suppress ordinary actions while learning a binding.
- Cancel repeat on mode/profile changes; define modifier-release behavior.
- Do not implicitly introduce trigger thresholds or analog mappings.

Foreground operation is the agreed initial scenario. Microsoft documents
focus-related reporting behavior; independent polling does not prove reliable
background operation. Test xstudio dialogs, panel focus, full-screen windows,
and application focus transitions on the actual Windows/controller setup.

Future gamepad support may justify SDL. Wiimote requires a separate
pairing/protocol/hardware investigation; MIDI and TouchOSC need different
adapters. A small input boundary allows extension without pretending one
library covers them all.

## 8. Integration approach and minimal boundaries

### In-process recommendation

Use a resident native `StandardPlugin` and QML. It fits application lifecycle,
session events, attributes, projector overlays, and Windows SDK input without a
new process or Python controller package.

A companion is technically possible through
[Connection.connect_remote](../python/src/xstudio/connection/__init__.py), line
300, and existing Python APIs. It offers input fault isolation but adds
authentication, reconnect, stale-state, two-process deployment, and startup
coordination. It still needs xstudio-side projector presentation.

Reconsider a companion only if measured focus behavior, a required device SDK,
or fault-isolation needs materially justify it.

### Boundaries worth keeping

1. **Input adapter:** button transitions, timestamps, connection events. One
   concrete XInput implementation and a synthetic test source initially.
2. **Binding resolver:** modes, globals, modifiers, learning, and repeat;
   independent of CAF/session objects and testable with a fake clock.
3. **Concrete xstudio action adapter:** supported catalogue, target resolution,
   execution, readiness/result checks. No universal transport or action bus.
4. **QML presentation/configuration:** reads shared state and submits explicit
   requests; no duplicate input processing per viewer.

Keep profile encoding concrete and small. The input contract and synthetic
testing seam genuinely need replaceability; the rest need clear responsibilities,
not speculative inheritance trees or plugin-of-plugins systems.

Cheap to revise: initial button layout, polling cadence, overlay styling, and
the input backend. More expensive after sharing profiles: action IDs/semantics,
button naming, precedence, and schema. Avoid prematurely publishing unstable
semantics.

## 9. Staged implementation path

### Stage 1: thin end-to-end risk slice

Prepare a fixture with a playlist, recognizable media, and a visually distinct
sequence. Use minimal bindings and overlay controls; a full profile editor is
not required yet. Retain the four explicit controller modes.

Exercise the real path:

1. Xbox button input reaches the plugin without depending on panel focus.
2. Projector overlay browsing highlights a playlist, then confirmation activates
   its displayed source while preserving playing/paused state.
3. Media navigation/confirmation chooses the intended item.
4. Sequence activation coordinates viewed container, timeline pinning, and all
   intended viewer attachments.
5. Transport and exposure operate on the resulting targets.
6. Disconnect changes neither playback target nor transport state.

The decisive case begins with individual media already displayed, then selects
a sequence and proves its timeline supplies the output. Include a previously
unpinned timeline and an independently attached viewer in the experiment.

Temporary fixed bindings are acceptable exploratory implementation debt here,
not the finished configuration architecture.

### Stage 2: binding and profile workflow

Add searchable supported actions, input learning, global/mode bindings,
modifiers, opt-in repeat, profile persistence/import/export, and saved controller
defaults. Resolve precedence and modifier semantics before publishing profiles.

### Stage 3: screening-room acceptance

Complete both navigation policies, projector readability, guide/confirmations,
error and connection feedback, all-viewer coverage, and default capture
inclusion. Test the installed Windows package, not just a development build.

Only then expand toward broader timeline/review actions or another backend.

## 10. Acceptance criteria and validation strategy

### First screening-room acceptance

After workstation setup, with no mouse/keyboard interaction and no workstation
display needed, the user can:

1. Open the Playlists overlay, browse, and confirm a playlist.
2. See the selected playlist become the displayed source across all intended
   viewers, preserving playing/paused state.
3. Open the Media overlay, select an item, and start/stop playback.
4. Select a sequence and activate its pinned timeline rather than continuing to
   display the previously selected media item.
5. Raise/lower exposure in all intended viewers.
6. Display a correct mode/button guide and receive readable command results.
7. Capture output with overlays included by default.
8. Disconnect the controller without changing playback.

Selection labels alone are not proof: inspect actual playhead/source identity
and visually distinguish the media and sequence output.

### Validation matrix

| Layer | Required coverage |
|---|---|
| Resolver unit tests | All four modes; global fallback/override once agreed; modifiers in both release orders; one dispatch per press; only permitted repeat; repeat cadence with a fake clock; cancellation on release, mode/profile change, learning, and disconnect. |
| Navigation tests | Browse-and-confirm does not alter selection/source before confirmation; immediate navigation uses agreed selection semantics; cancellation is non-destructive; empty lists and removed/reordered items are handled by identity. |
| Targeting integration | Inspection differs from viewing; selected media belongs to intended container; sequence activation sets viewed identity, pinning, and actual viewer attachment; previous media and unpinned timelines do not leak through; single selection avoids unintended multi-timeline comparison. |
| Playback-state tests | Activate while playing and while paused; switch repeatedly; follow commands with transport; verify no stale callback restores state to an obsolete target. Position/range/rate/direction expectations need definition. |
| All-viewer tests | Normal followers, independent viewers, intended projector/video outputs, duplicate/shared pipeline identities, and viewer open/close during operation. No duplicate exposure increments or overlay-driven command dispatch. |
| Failure tests | Missing/deleted targets, session replacement, unavailable colour pipeline/action, timeout, rapid asynchronous changes, invalid profiles, and unsupported devices produce visible errors rather than silent success. |
| Disconnect/reconnect | Disconnect while playing/paused and during held navigation/exposure/modifier. No further repeat, no source/transport mutation, no synthetic release action; reconnect with buttons held requires neutral baseline. Playback position continues naturally if playing. |
| Hardware/focus/package | Intended wired/wireless Xbox connection, hot-plug, slot changes, xstudio panel/dialog/fullscreen focus, OS focus changes, plugin enable/disable/shutdown, and clean installed-package operation. |
| Projector/capture | Readability at actual viewing distance; paused/empty-source updates; same shared state across outputs; capture inclusion across the agreed capture types; operation without workstation interaction. |

Use existing GTest/CTest conventions rather than new tooling. The
[Windows build/test guide](reference/build_guides/windows.md), near line 98,
documents enabling `BUILD_TESTING`, building selected targets, and running
`ctest --test-dir build --output-on-failure -R <registered-test-name>`.
Controller-specific targets do not exist yet; select exact commands after
implementation. Existing unrelated baseline failures must be distinguished from
new regressions. Hardware/projector acceptance cannot be replaced by unit tests.

No validation commands were run for this documentation-only consolidation.

## 11. Unresolved decisions and implementation gates

| Question | Current position / next evidence needed |
|---|---|
| What exactly counts as "all viewers"? | User intent is all viewers. Enumerate main, secondary, quickview, independent, DeckLink/offscreen, snapshot, and render destinations; distinguish ongoing interactive targets from transient capture renderers. |
| What is the projection chain? | Not established. Verify actual Windows display/video-output path before claiming overlays reach the projector. |
| How are multiple playing states reconciled? | Preserve playback state is agreed. If viewers initially have different sources/states, define whether one review transport state or per-target restoration applies. |
| What else is preserved on source changes? | Playing/paused is the minimum interpretation. Position, looping/range, direction, and rate policies remain unspecified. |
| What is the exact all-viewer exposure policy? | Relative delta in each pipeline is recommended, not explicitly approved. Define partial failures and shared pipelines. |
| What does immediate navigation commit? | Configurable immediate selection is required; playlist selection changes displayed source. Confirm behavior for Media and sequence lists and the profile scope of the option. |
| Which button layout and conflict rules? | Physical layout, mode switches, modifier reservations, and precedence remain recommendations awaiting confirmation/ergonomic trial. |
| Which list contents/order/filter? | Match application order and avoid a separate filter initially is recommended. Define hierarchy/group expansion, subsets, sequences, and existing media-filter interaction. |
| How are profiles matched to devices? | Xbox default and user-saved alternatives are agreed. Start manually; robust identity/automatic matching is not established. |
| Which captures include controls? | Included by default is agreed. Enumerate snapshots, screenshots, rendered movies, and video-output paths; define optional exclusion behavior. |
| What happens on focus loss/reconnect? | Foreground xstudio is the initial assumption; neutral reconnect and repeat cancellation are recommendations to validate. |
| Is XInput sufficient on the actual hardware? | Test the user's controller/connection and focus behavior. If not, evaluate GameInput or SDL against the specific failure rather than building both preemptively. |

## Recommended next implementation step

Agree the concrete viewer/output set and ambiguous preservation semantics, then
implement Stage 1: Windows/Xbox input, minimal projector browsing, all-target
source activation, timeline pinning, transport, and exposure.

**Success criterion:** from previously displayed media, using only the
controller and projector, select a playlist/media item, start/stop playback,
activate a selected sequence's pinned timeline across the intended viewers,
adjust exposure, capture with overlays, and disconnect without changing
playback. Confirm actual source identity and image output, not merely selection
or a success notification. Expand configuration and device support after that
slice passes.
