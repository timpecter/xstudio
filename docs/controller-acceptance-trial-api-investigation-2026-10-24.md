# Controller acceptance-trial API investigation

**Investigation date:** 2026-10-24  
**Status:** Source investigation; no code or controller runtime testing performed.  
**Scope:** Whether current xSTUDIO source exposes reliable operations for each step in the “First screening-room acceptance trial” in [the brainstorm](./controller-plugin-brainstorm.md#first-screening-room-acceptance-trial).

This document records source-backed findings for other agents to query. “Reliable” here means that a source-level operation and a plausible invocation path exist; it does not mean the operation was exercised in a running application or tested with a controller.

## Summary

The Python API exposes useful building blocks for playback, selection, container inspection/viewing, and exact viewer-exposure values. The important distinctions are:

- The **inspected container** drives what the Media panel displays.
- The **viewed container** is the container whose playhead is connected for playback.
- A container’s **playhead selection** is distinct from the Session’s selected playlist/timeline rows.
- Exposure is available as a value-bearing colour-pipeline attribute; relative “up/down” behavior is not a named operation.

The API does not establish a complete controller-binding path. In particular, no dedicated gamepad/XInput API was found in the searched application, plugin, and Python API source.

## Action-to-implementation map

| Acceptance-trial action | Verified implementation and invocation | Target and limitations |
|---|---|---|
| Select a playlist from Playlists | `Session.playlists` enumerates playlists. `Session.inspected_container = playlist` sends `active_media_container_atom`; `SessionActor` stores it as `inspectedContainer_`. See [`Session.playlists`](../python/src/xstudio/api/session/session.py), [`Session.inspected_container`](../python/src/xstudio/api/session/session.py), and [`SessionActor` handler](../src/session/src/session_actor.cpp). | This chooses the inspected container, which supplies the Media panel context. It does not necessarily switch playback. `Session.selected_containers` is a getter, not a Python selection setter. The UI's row/multi-selection state is stored separately as `SessionActor::selection_`. |
| Select a media item from Media | For the intended playlist/container, call `container.playhead_selection.set_selection([media.uuid])`. The selector is exposed on `Playlist` and `Timeline`; it sends `select_media_atom`. See [`Playlist.playhead_selection`](../python/src/xstudio/api/session/playlist/playlist.py), [`Timeline.playhead_selection`](../python/src/xstudio/api/session/playlist/timeline/__init__.py), and [`PlayheadSelection.set_selection`](../python/src/xstudio/api/session/playhead/playhead_selection.py). | The call targets that container's playhead selection, not an arbitrary visible row. For Playlist/Subset playback, the selection drives the viewer when that container is viewed. The Media List documentation notes that sequence and compare-mode playback are not changed by media selection. `set_selection` returns `True` after sending its request; that return alone does not confirm what was ultimately selected. |
| Start/stop playback | Set `Playhead.playing = True` or `False`; the property also reads current play state. The active viewport exposes its playhead. See [`Playhead.playing`](../python/src/xstudio/api/session/playhead/playhead.py), [`App.active_viewport`](../python/src/xstudio/api/app.py), and [`Viewport.playhead`](../python/src/xstudio/api/intrinsic/viewport.py). | Select the intended viewport/playhead. `active_viewport` means the UI's currently active and visible viewport; named viewport and global-playhead access are also exposed by `App`. A plugin can obtain the current playhead via [`PluginBase.current_playhead`](../python/src/xstudio/plugin/plugin_base.py). |
| Select a sequence from Playlists | Sequences are `Timeline` containers returned by `Playlist.containers`. The session inspected-container setter can make one the inspected container. See [`Playlist.containers`](../python/src/xstudio/api/session/playlist/playlist.py), [`Session.inspected_container`](../python/src/xstudio/api/session/session.py), and [`SessionActor` row-selection handler](../src/session/src/session_actor.cpp). | Container lookup and inspection are supported; setting the Session's Playlists panel row/multi-selection through the public Python API was not found. The backend does have a row-selection handler, and selection can trigger multi-timeline compare logic. |
| Make that sequence's timeline the active playback source | Set `session.viewed_container = timeline`; the setter sends `viewport_active_media_container_atom`. `SessionActor` updates the viewed container and calls `setOnScreenPlayhead(true)`, which connects that container's playhead. A timeline also exposes its playhead. See [`Session.viewed_container`](../python/src/xstudio/api/session/session.py), [`SessionActor` viewed-container handler](../src/session/src/session_actor.cpp), [`SessionActor::setOnScreenPlayhead`](../src/session/src/session_actor.cpp), and [`Timeline.playhead`](../python/src/xstudio/api/session/playlist/timeline/__init__.py). | This is the source-backed route to switch from the previously viewed media/container to the sequence. Do not assume `Session.set_on_screen_source` does this: despite its name/docstring, it sends `active_media_container_atom` (the inspected-container path), not `viewport_active_media_container_atom`. |
| Raise/lower viewer exposure | `Viewport.colour_pipeline.exposure` returns the `Exposure (E)` attribute; `ModuleAttribute.value()` reads it and `set_value(value)` sets an exact value. See [`Viewport.colour_pipeline`](../python/src/xstudio/api/intrinsic/viewport.py), [`ColourPipeline.exposure`](../python/src/xstudio/api/intrinsic/colour_pipeline.py), and [`ModuleAttribute`](../python/src/xstudio/api/module.py). | Choose a named or active viewport to target its pipeline. The value API supports exact values, not an explicit relative increment/decrement action. The built-in exposure hotkey is a mouse scrub interaction, not a controller increment action. |

## Plugin and input invocation context

- Python scripting can control a running xSTUDIO instance through the embedded interpreter or the remote connection API; see [Python Scripting Introduction](./user_docs/appendix/python_scripting.rst).
- Python plugins inherit module/attribute access and can register keyboard hotkeys through [`ModuleBase.register_hotkey`](../python/src/xstudio/api/module.py). It registers a keycode/modifier, and the callback receives the detected UI-context string. The method's `context` parameter is documented but is not forwarded in its registration request. This is a keyboard API, not a gamepad-button API.
- The OCIO plugin's built-in Exposure Scrubbing hotkey is **E** in the Viewer context. It activates exposure scrubbing, grabs mouse focus, and applies a value based on pointer dragging. See [`OCIOColourPipeline` hotkey registration and handlers](../src/plugin/colour_pipeline/ocio/src/ocio_plugin.cpp).
- A source search for gamepad, joystick, controller, SDL game-controller, and XInput integration found no dedicated controller interface in the searched `src`, `include`, and Python API trees. This is a bounded search finding, not proof that no external/custom integration exists.

## Recommendations (not verified behavior)

1. Define playlist inspection and playback activation as separate controller actions. Use `inspected_container` to change Media-panel context and `viewed_container` only when playback should switch.
2. Make the media-selection action operate on the intended container's `playhead_selection`; decide whether it should also switch the viewed container when the selection belongs to a different one.
3. Prefer explicit Play and Stop commands over a toggle, and target a configured viewport/global playhead rather than relying implicitly on whichever UI viewport currently has focus.
4. Switch a sequence to playback with `viewed_container = timeline`, rather than relying on `set_on_screen_source`.
5. Define exposure as a relative adjustment over the current exposure value, with a product-approved increment, range, and projector-visible feedback.
6. Treat controller hardware bindings and command feedback as a separate integration requirement; the Python operations alone do not provide controller input capture.

## Product decisions and technical unknowns

1. Does “select playlist/sequence” mean highlight a row, set the inspected container, or make it the viewed playback source? Should browsing apply immediately or require confirmation?
2. When media is selected from a container that is not currently viewed, should the controller switch playback to that container, or only change its selection?
3. Is sequence row selection required independently of making its timeline the active source? What should happen when more than one sequence is selected, given existing multi-timeline comparison behavior?
4. Which viewport is the stable projector target: a named viewport, the active visible viewport, or the global playhead? Should commands work if the target viewport is not UI-focused?
5. What are the exposure increment, bounds, reset behavior, and confirmation feedback?
6. What controller/input integration will deliver Windows button events to the plugin or companion process? How will disconnect/reconnect be surfaced while preserving playback?
7. Does the controller need completion/selection confirmation beyond the request response exposed by each API? In particular, `PlayheadSelection.set_selection` returns `True` after issuing its request.

## Source references at a glance

- Trial requirement: [`controller-plugin-brainstorm.md`](./controller-plugin-brainstorm.md#first-screening-room-acceptance-trial)
- Session inspected/viewed containers and playlist enumeration: [`session.py`](../python/src/xstudio/api/session/session.py)
- Container playlist, timeline, and selection accessors: [`playlist.py`](../python/src/xstudio/api/session/playlist/playlist.py), [`timeline/__init__.py`](../python/src/xstudio/api/session/playlist/timeline/__init__.py), [`playhead_selection.py`](../python/src/xstudio/api/session/playhead/playhead_selection.py)
- Playback and viewport API: [`playhead.py`](../python/src/xstudio/api/session/playhead/playhead.py), [`viewport.py`](../python/src/xstudio/api/intrinsic/viewport.py), [`app.py`](../python/src/xstudio/api/app.py)
- Session backend inspected/viewed handling and playhead activation: [`session_actor.cpp`](../src/session/src/session_actor.cpp)
- Exposure and keyboard/mouse implementation: [`colour_pipeline.py`](../python/src/xstudio/api/intrinsic/colour_pipeline.py), [`module.py`](../python/src/xstudio/api/module.py), [`ocio_plugin.cpp`](../src/plugin/colour_pipeline/ocio/src/ocio_plugin.cpp)
- User-facing inspected/viewed and media selection semantics: [`playlists.rst`](./user_docs/interface/playlists.rst), [`media_list.rst`](./user_docs/interface/media_list.rst)
