# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "plugin" / "python_plugins"))
from controller_input.mapping import ButtonBinding, ButtonConfiguration, DISABLED, MODES
from controller_input.presets import PresetStore, decode_preset, encode_preset


class PresetTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "presets.json"
        self.config = ButtonConfiguration.defaults()
        self.changed = self.config.assign("common", "b", "toggle_playback")
        self.store = PresetStore(self.path)

    def test_round_trip_restart_and_factory(self):
        self.assertEqual(self.store.selected, "Factory")
        self.store.save("Review", self.changed)
        restored = PresetStore(self.path)
        self.assertEqual(restored.selected, "Review")
        self.assertEqual(restored.configuration, self.changed)
        restored.select("Factory")
        self.assertEqual(PresetStore(self.path).configuration, self.config)
        with self.assertRaises(ValueError):
            restored.save("Factory", self.changed, replace=True)

    def test_common_and_disabled_round_trip(self):
        config = self.config.assign("common", "a", "exposure_up").assign(
            "media", "x", DISABLED).assign("timeline", "b", "toggle_mask")
        self.store.save("Shared", config)
        self.assertEqual(PresetStore(self.path).configuration, config)
        exported = Path(self.folder.name) / "shared.json"
        self.store.export_file(exported, "Portable", config)
        self.assertEqual(json.loads(exported.read_text())["schema_version"], 4)
        self.store.import_file(exported)
        self.assertEqual(self.store.get("Portable"), config)

    def test_shift_layers_round_trip_and_version_two_migration(self):
        config = self.config.assign("common", "b", "toggle_mask", "shifted").with_shift("rb")
        self.store.save("Layers", config)
        self.assertEqual(PresetStore(self.path).configuration, config)
        encoded = encode_preset("Layers", config)
        self.assertEqual(decode_preset(encoded)[1], config)
        for field, value in (("shift", "a"), ("shift", "menu"), ("shift", None)):
            with self.assertRaises(ValueError):
                decode_preset({**encoded, field: value})
        legacy_config = ButtonConfiguration(tuple(
            b for b in self.config.bindings if b.layer == "normal"))
        legacy = encode_preset("Version Two", legacy_config)
        legacy["schema_version"] = 2
        legacy.pop("shift")
        for binding in legacy["bindings"]:
            binding.pop("layer")
        self.assertEqual(decode_preset(legacy)[1], self.config)
        for binding in ({"mode": "media", "button": "rt", "action": "toggle_mask"},
                        {"mode": "media", "button": "a", "action": "toggle_mask", "layer": "shifted"}):
            with self.assertRaises(ValueError):
                decode_preset({**legacy, "bindings": [binding]})

    def test_legacy_library_folds_viewer_into_common(self):
        legacy = {
            "schema_version": 1, "device": "xinput", "scope": "ordinary-buttons",
            "name": "Legacy", "bindings": [
                {"mode": "viewer", "button": "a", "action": "toggle_mask"},
                {"mode": "viewer", "button": "b", "action": "toggle_playback"},
                {"mode": "media", "button": "x", "action": "toggle_playback"}]}
        self.path.write_text(json.dumps({
            "schema_version": 1, "selected": "Legacy", "presets": {"Legacy": legacy}}))
        before = self.path.read_bytes()
        store = PresetStore(self.path)
        self.assertFalse(store.warning)
        self.assertEqual(self.path.read_bytes(), before)
        config = store.configuration
        self.assertEqual(config.action("common", "a"), "toggle_mask")
        self.assertEqual(config.action("common", "b"), "toggle_playback")
        self.assertEqual(config.action("common", "y", "shifted"), "cycle_compare")
        self.assertEqual(config.action("media", "x"), "toggle_playback")
        self.assertIsNone(config.action("media", "b"))
        self.assertNotIn("viewer", [b.mode for b in config.bindings])
        store.save("Legacy", config, replace=True)
        self.assertEqual(PresetStore(self.path).configuration, config)
        self.assertEqual(json.loads(self.path.read_text())["schema_version"], 4)
        for binding in ({"mode": "common", "button": "a", "action": "toggle_mask"},
                        {"mode": "media", "button": "a", "action": DISABLED}):
            with self.assertRaises(ValueError):
                decode_preset({**legacy, "bindings": [binding]})

    def test_legacy_viewer_disable_removes_common_binding(self):
        legacy = {
            "schema_version": 2, "device": "xinput", "scope": "ordinary-buttons",
            "name": "Legacy", "bindings": [
                {"mode": "common", "button": "x", "action": "toggle_playback"},
                {"mode": "viewer", "button": "x", "action": "disabled"}]}
        self.assertIsNone(decode_preset(legacy)[1].action("common", "x"))

    def test_duplicate_confirmation_and_path_independent_names(self):
        self.store.save("Review", self.config)
        original = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.save("review", self.changed)
        self.assertEqual(self.path.read_bytes(), original)
        self.store.save("Review", self.changed, replace=True)
        self.assertEqual(self.store.configuration, self.changed)
        self.store.save("../portable", self.config)
        self.assertEqual(self.store.selected, "../portable")
        self.assertEqual(len(list(Path(self.folder.name).iterdir())), 1)

    def test_import_adds_without_activating_export_round_trip(self):
        export = Path(self.folder.name) / "mapping.json"
        self.store.export_file(export, "Experiment", self.changed)
        self.assertFalse(self.path.exists())
        self.store.import_file(export)
        self.assertEqual(self.store.selected, "Factory")
        self.assertEqual(self.store.configuration, self.config)
        self.assertEqual(self.store.get("Experiment"), self.changed)
        self.store.select("Experiment")
        self.assertEqual(PresetStore(self.path).configuration, self.changed)

    def test_invalid_import_leaves_state_and_disk_unchanged(self):
        self.store.save("Review", self.config)
        before = self.path.read_bytes()
        imported = Path(self.folder.name) / "bad.json"
        for data in (
                "{", '{"schema_version":999}',
                json.dumps({**encode_preset("Bad", self.config), "device": "unknown"}),
                json.dumps({**encode_preset("Bad", self.config), "scope": "all-controls"}),
                json.dumps({**encode_preset("Bad", self.config), "bindings": [
                    {"mode": "common", "button": "menu", "action": "toggle_playback"}]})):
            imported.write_text(data, encoding="utf-8")
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.store.import_file(imported)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(self.store.selected, "Review")

    def test_failed_replace_and_selection_preserve_last_valid_data(self):
        self.store.save("Review", self.config)
        before = self.path.read_bytes()
        with patch("controller_input.presets.os.replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                self.store.save("Review", self.changed, replace=True)
            with self.assertRaises(PermissionError):
                self.store.select("Factory")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.selected, "Review")
        self.assertEqual(self.store.configuration, self.config)
        self.assertEqual(sorted(p.name for p in Path(self.folder.name).iterdir()), ["presets.json"])

    def test_missing_selected_and_damaged_entry_warn_without_overwriting(self):
        self.store.save("Review", self.changed)
        data = json.loads(self.path.read_text())
        data["presets"]["Review"]["schema_version"] = 999
        self.path.write_text(json.dumps(data))
        damaged = self.path.read_bytes()
        restored = PresetStore(self.path)
        self.assertEqual(restored.selected, "Factory")
        self.assertEqual(restored.configuration, self.config)
        self.assertIn("Review", restored.warning)
        self.assertEqual(self.path.read_bytes(), damaged)
        restored.save("Other", self.config)
        self.assertEqual(json.loads(self.path.read_text())["presets"]["Review"],
                         data["presets"]["Review"])
        data["selected"] = "Missing"
        self.path.write_text(json.dumps(data))
        self.assertIn("Missing", PresetStore(self.path).warning)

    def test_corrupt_library_is_preserved_and_errors_on_write(self):
        self.path.write_text("not json")
        restored = PresetStore(self.path)
        self.assertEqual(restored.selected, "Factory")
        self.assertTrue(restored.warning)
        with self.assertRaises(ValueError):
            restored.save("Review", self.changed)
        self.assertEqual(self.path.read_text(), "not json")
        export = Path(self.folder.name) / "recovery.json"
        restored.export_file(export, "Recovery", self.changed)
        self.assertEqual(decode_preset(json.loads(export.read_text()))[1], self.changed)

    def test_strict_schema_duplicate_bindings_and_canonical_order(self):
        data = encode_preset("Review", self.config)
        for key, value in (("schema_version", True), ("name", ""),
                           ("unexpected", True), ("bindings", None)):
            bad = {**data, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                decode_preset(bad)
        duplicate = {**data, "bindings": data["bindings"] + [data["bindings"][0]]}
        with self.assertRaises(ValueError):
            decode_preset(duplicate)
        reordered = {**data, "bindings": list(reversed(data["bindings"]))}
        self.assertEqual(decode_preset(reordered)[1], self.config)

    def test_export_cannot_overwrite_library(self):
        self.store.save("Review", self.config)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.export_file(self.path, "Oops", self.changed)
        self.assertEqual(self.path.read_bytes(), before)

    def test_import_factory_export_uses_writable_copy_name(self):
        path = Path(self.folder.name) / "factory.json"
        self.store.export_file(path, "Factory", self.changed)
        self.assertEqual(self.store.import_file(path), "Factory Copy")
        self.assertEqual(self.store.selected, "Factory")
        self.assertEqual(self.store.get("Factory Copy"), self.changed)

    def test_save_and_select_failure_is_one_atomic_transaction(self):
        self.store.save("Review", self.config)
        before = self.path.read_bytes()
        with patch("controller_input.presets.os.replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                self.store.save("Experiment", self.changed, select_after="Review")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn("Experiment", [entry["name"] for entry in self.store.entries()])

    def test_import_replacing_selected_updates_saved_not_working_configuration(self):
        self.store.save("Review", self.config)
        path = Path(self.folder.name) / "import.json"
        self.store.export_file(path, "Review", self.changed)
        with self.assertRaises(FileExistsError):
            self.store.import_file(path)
        self.store.import_file(path, replace=True)
        self.assertEqual(self.store.selected, "Review")
        self.assertEqual(self.store.configuration, self.changed)

    def test_duplicate_json_keys_and_failed_flush_leave_saved_data_intact(self):
        self.store.save("Review", self.config)
        before = self.path.read_bytes()
        path = Path(self.folder.name) / "duplicate.json"
        path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):
            self.store.import_file(path)
        with patch("controller_input.presets.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.save("Review", self.changed, replace=True)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.configuration, self.config)
        self.assertFalse(any(Path(self.folder.name).glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
