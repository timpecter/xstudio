# Controller plugin implementation checklist

Source: [controller-plugin-plan.md](controller-plugin-plan.md), reconciled with the brainstorm and the architecture/API investigations. The controller implementation is partial: Windows input, bindings, transport, exposure, mask, loop, and the mode/guide overlay exist; browse/confirm/back source actions remain unavailable. Stage and acceptance boxes stay unchecked until their full exit evidence is met. Current subtask progress, blockers, and verification evidence are recorded below.

## Implementation stages

- [ ] **Stage 0 — Resolve targeting.** Enumerate intended viewers and output paths; define the policy for divergent playback states and choose the initial projection/capture path. Produce a concrete fixture and target matrix, including named completion signals for source activation and timeline pinning.
- [ ] **Stage 1 — Build the thin risk slice.** Implement the Windows/Xbox adapter, minimal bindings, four controller modes, shared browse-and-confirm overlay, source activation, transport, and relative exposure. Pass the controller/projector-only trial for playlists, media, and pinned sequences across follower and independent viewers; verify state preservation, disconnect safety, and overlay presence in an agreed capture.
- [ ] **Stage 2 — Build the configurable workflow.** Add searchable supported actions, input learning, global and mode-specific bindings, modifiers, suitable repeat, profile save/default/import/export, and capture exclusion. Add resolver/profile tests and explicit unsupported-device/error feedback; validate binding precedence and profile schema before profile sharing.
- [ ] **Stage 3 — Validate package acceptance.** Add the immediate-navigation option, complete output coverage, guide/feedback, lifecycle handling, and packaged-runtime validation. Pass the agreed hardware/projector/capture matrix on both installed and portable Windows distributions without workstation interaction after setup.

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
- [ ] User acceptance of the Media mode fix and the read-only previews after
  relaunch with `build_win11\run_xstudio.bat`.
- [ ] Implement browse-state presentation and browse/confirm/back source
  activation for playlists, nested sequences, and media. Ensure browsing does
  not alter session selection or source; confirm must revalidate the target and
  preserve the agreed global playing/paused state.
- [ ] Validate guide readability and overlay inclusion on the actual projector
  and video-output path. **Blocked:** no runtime/hardware capture trial has
  been performed; source/QML wiring alone is not acceptance evidence.

**Next implementation task:** implement A/confirm source activation for the
shared preview candidates through
the source-backed session APIs, with shared browse state for all overlay
instances. Stage 0 and Stage 1 remain unchecked: the target/state policy is
recorded, but source activation, timeline pinning, projector/video-output
validation, and the remaining acceptance trial are still outstanding.
