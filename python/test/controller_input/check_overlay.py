# SPDX-License-Identifier: Apache-2.0
"""Exercise production QML with only the xSTUDIO attribute model boundary faked."""
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
source = (
    ROOT / "src" / "plugin" / "python_plugins" / "controller_input" / "overlay.qml"
).read_text(encoding="utf-8")
source = "\n".join(line for line in source.splitlines() if not line.startswith("import "))
source = source.replace("Item {", "Item { id: overlay", 1)
test = """
import QtQuick
import QtTest
Item {
    width: 1280
    height: 720
    visible: true
    QtObject {
        id: view
        property bool isQuickview: false
    }
    QtObject {
        id: state
        property bool connected: false
        property bool guide: false
        property bool menu: false
        property bool browsing: false
        property var rows: ["Review", "Dailies"]
        property string mode: "viewer"
        property string status: "Controller connected"
    }
    component XsModuleData: QtObject {
        property string modelDataName
    }
    component XsAttributeValue: QtObject {
        property string attributeTitle
        property QtObject model
        readonly property var value: attributeTitle === "Controller Connected" ? state.connected :
            attributeTitle === "Controller Mode" ? state.mode :
            attributeTitle === "Controller Menu Held" ? state.menu :
            attributeTitle === "Controller Browse Visible" ? state.browsing :
            attributeTitle === "Controller Browse Rows" ? state.rows :
            attributeTitle === "Controller Browse Index" ? 1 :
            attributeTitle === "Controller Browse Title" ? "Playlists preview" :
            attributeTitle === "Controller Guide" ? state.guide : state.status
    }
    PRODUCTION_OVERLAY
    TestCase {
        name: "ControllerOverlay"
        when: windowShown
        function test_badge_guide_and_visibility() {
            compare(overlay.visible, false)
            state.connected = true
            compare(overlay.visible, false)
            state.menu = true
            tryCompare(overlay, "visible", true)
            tryCompare(guideText, "text", "Controller mode: viewer")
            var badge = content.parent
            verify(badge.width >= 360, "badge width")
            verify(badge.x >= 0 && badge.y >= 0, "badge origin")
            verify(badge.x + badge.width <= overlay.width, "badge right edge")
            verify(badge.y + badge.height <= overlay.height, "badge bottom edge")
            state.mode = "playlists"
            tryCompare(guideText, "text", "Controller mode: playlists")
            var closedHeight = badge.height
            state.guide = true
            tryVerify(function() { return guideText.text.indexOf("Menu + D-pad") !== -1 })
            tryVerify(function() { return badge.height > closedHeight }, 1000, "guide expansion")
            verify(badge.y >= 0, "expanded guide top")
            state.guide = false
            tryCompare(guideText, "text", "Controller mode: playlists")
            state.menu = false
            tryCompare(overlay, "visible", false)
            state.guide = true
            tryCompare(overlay, "visible", true)
            state.guide = false
            state.browsing = true
            tryCompare(overlay, "visible", true)
            compare(guideText.visible, false)
            tryVerify(function() { return badge.height > 100 }, 1000, "browse expansion")
            verify(badge.y >= 0, "browse top")
            state.browsing = false
            tryCompare(overlay, "visible", false)
            view.isQuickview = true
            tryCompare(overlay, "visible", false)
            state.guide = true
            compare(overlay.visible, false)
            view.isQuickview = false
            tryCompare(overlay, "visible", true)
            state.guide = false
            state.connected = false
            tryCompare(overlay, "visible", false)
            state.menu = true
            compare(overlay.visible, false)
        }
    }
}
""".replace("PRODUCTION_OVERLAY", source)

with tempfile.TemporaryDirectory(prefix="xstudio-controller-qml-") as folder:
    path = Path(folder) / "tst_overlay.qml"
    path.write_text(test, encoding="utf-8")
    output = Path(folder) / "results.txt"
    result = subprocess.run(
        [sys.argv[1], "-platform", "offscreen", "-input", str(path),
         "-o", str(output) + ",txt"],
        timeout=30)
    if output.exists():
        print(output.read_text(encoding="utf-8"))
    result.check_returncode()
