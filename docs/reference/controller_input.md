# Windows controller input (increment 1)

The resident **Controller Input** utility plugin uses the approved XInput 1.4
backend on Windows. It polls **XInput slot 0 only** every 16 ms on a dedicated
thread, not the UI, renderer, or CAF scheduler. Other slots, analog input, device
selection, action bindings, and mode switching are not implemented.

Enable/disable it through the existing plugin manager. Disabling sends the
resident actor a shutdown message; its exit hook cancels the polling wait and
joins the thread before completing normal plugin cleanup. Acquisition errors
are logged and stop the actor. No alternative backend is used.

Normalized events are logged as `Controller Input: <JSON>` and broadcast through
the plugin's existing event group as `(event_atom, "controller_input", JsonStore)`.
Fields are `backend` (`xinput1_4`), `slot` (0), `generation`, `sequence`, `edge`
(`connected`, `disconnected`, `down`, `up`), `button` (the raw XInput button bit,
zero for connection events), and `buttons` (the sampled bitmask). Sequence is
strictly increasing within a plugin instance. Simultaneous button changes are
reported in increasing bit order. Reserved XInput bits are masked out.

A connection starts a new generation. Its raw button snapshot establishes the
baseline without inventing press edges for already-held buttons. Disconnect
reports only the connection transition, not synthetic releases or actions.
Samples from retired generations and duplicate/out-of-order samples are rejected.
This acquisition baseline does **not** define future reconnect/held-action policy.
Identity is a slot plus generation, not a persistent physical-device identity.
As with any sampled input, transitions entirely between polls cannot be observed;
a disconnect/reconnect entirely between polls is also not distinguishable.

## Validation

Follow the Windows build guide, using a build directory configured for this
checkout (the examples use `build`):

```powershell
cmake -B build --preset WinNinjaReleaseLocal -DBUILD_TESTING=ON
cmake --build build --target controller_input input_test
ctest --test-dir build -N -R controller_input
ctest --test-dir build --output-on-failure -R "^controller_input_input_test$"
```

The test source is registered with the existing `create_tests` macro. Confirm
the generated target and CTest registration in the configured tree before using
these commands. Synthetic tests cover normalization, stale generations, errors,
cancellation of a pending poll, and delivery through the actual resident actor
followed by the same shutdown message used on disable.
The tests use `ACTOR_TEST_MINIMAL` plus xSTUDIO type registration rather than
starting the application-wide actor-system singleton.

An opt-in physical test is disabled in normal automated runs. To give yourself a
30-second window to press and release any digital button (no action assignment):

```powershell
$env:PATH = "$PWD\build\bin;$PWD\build\vcpkg_installed\x64-windows\bin;$env:PATH"
& .\build\src\plugin\utility\controller_input\test\input_test.exe --gtest_also_run_disabled_tests --gtest_filter=ControllerInput.DISABLED_PhysicalXInputButtonEdges
```

This runs the real XInput acquisition and plugin actor, not a synthetic source,
but does not test discovery/loading into the GUI application or prove the radio
transport independently of the operator's Bluetooth setup.

For a separate physical trial, enable the plugin, connect the approved controller
over the intended connection (Bluetooth for the current trial), and inspect the
logs. Confirm one connection event, paired down/up events for each deliberate
press/release, no repeated edges while held, a disconnect transition, and no
further input logs after disable. Re-enable starts a fresh plugin instance.
Windows reporting Bluetooth connectivity alone is not XInput evidence.

No action, overlay, source activation, transport, exposure, profile, recording,
capture, projector, or SDI acceptance is established by these tests.
