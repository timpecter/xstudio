# Controller plugin brainstorm

Status: requirements captured through brainstorming on 2026-10-23.
This is a conversation record, not a technical specification or implementation
plan. Technical feasibility has not yet been investigated.

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

The first version can use a searchable list of supported actions. Users choose
an action and learn the controller button or combination to assign to it.

Initial action discovery and assignment should focus on these panels:

- Viewer
- Timeline
- Playlists
- Media

These panel boundaries do not yet constitute an exhaustive action inventory or
a commitment to expose every operation within each panel.

Initial input scope:

- Buttons.
- Modifier-plus-button combinations.
- Optional hold-to-repeat for suitable actions.
- One action per binding.

Analog stick and trigger-value mappings, double presses, long presses, and
multi-action sequences are deferred.

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

- Support explicit Viewer, Timeline, Playlists, and Media modes.
- The same controller input can have different assignments in different modes.
- Allow global bindings alongside mode-specific bindings.
- Mode selection is intended to provide deliberate controller context rather
  than depend solely on mouse or keyboard focus.

The exact mode-switching controls and rules for resolving overlapping global
and mode-specific bindings remain open.

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

Storage format, transfer mechanisms, device identification, and automatic
profile selection remain open.

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
- Should configuration live entirely inside an xstudio plugin panel or in a
  companion application? The user currently has no preference.
- How should assignment conflicts and invalid or unavailable actions be shown?
- How should profiles behave when moved between workstations or controller
  types?
- What technical boundaries will allow future platforms and device types
  without unnecessarily complicating the first version?

No technical investigation, implementation, or controller testing has been
performed as part of this brainstorm.
