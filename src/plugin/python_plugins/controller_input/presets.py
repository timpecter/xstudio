# SPDX-License-Identifier: Apache-2.0
"""Versioned ordinary-button presets, committed as one atomic library write."""
import json
import os
from pathlib import Path
import tempfile

from .mapping import ButtonBinding, ButtonConfiguration


FACTORY = "Factory"
SCHEMA_VERSION = 4
SUPPORTED_VERSIONS = (1, 2, 3, SCHEMA_VERSION)
SCOPE = "ordinary-buttons"


def _fold_viewer_into_common(bindings, shift):
    """Version < 4 presets had a Viewer scope; Common is now the default mode."""
    common = [b for b in bindings if b.mode == "common"]
    for viewer in (b for b in bindings if b.mode == "viewer"):
        common = [b for b in common if not (
            (b.button, b.layer) == (viewer.button, viewer.layer)
            or (viewer.action != "disabled" and b.action == viewer.action))]
        if viewer.action != "disabled":
            common.append(ButtonBinding("common", viewer.button, viewer.action, viewer.layer))
    if shift != "y" and not any(
            b.button == "y" and b.layer == "shifted" for b in common) and not any(
            b.action == "cycle_compare" for b in common):
        common.append(ButtonBinding("common", "y", "cycle_compare", "shifted"))
    return [b for b in bindings if b.mode not in ("common", "viewer")] + common


def validate_name(name):
    if not isinstance(name, str) or not name.strip() or name != name.strip():
        raise ValueError("Preset names must be nonempty and have no surrounding whitespace")
    if len(name) > 128 or any(ord(char) < 32 for char in name):
        raise ValueError("Preset names must be at most 128 characters with no control characters")


def encode_preset(name, configuration):
    validate_name(name)
    return {
        "schema_version": SCHEMA_VERSION,
        "device": "xinput",
        "scope": SCOPE,
        "name": name,
        "shift": configuration.shift,
        "bindings": [
            {"mode": b.mode, "button": b.button, "action": b.action, "layer": b.layer}
            for b in configuration.bindings
        ],
    }


def decode_preset(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid controller preset fields")
    version = data.get("schema_version")
    if type(version) is not int or version not in SUPPORTED_VERSIONS:
        raise ValueError("Unsupported controller preset schema version")
    fields = {"schema_version", "device", "scope", "name", "bindings"}
    if set(data) != (fields | {"shift"} if version >= 3 else fields):
        raise ValueError("Invalid controller preset fields")
    if data["device"] != "xinput" or data["scope"] != SCOPE:
        raise ValueError("Unsupported controller preset device or mapping scope")
    validate_name(data["name"])
    if not isinstance(data["bindings"], list):
        raise ValueError("Preset bindings must be a list")
    bindings = []
    for entry in data["bindings"]:
        fields = {"mode", "button", "action"}
        if not isinstance(entry, dict) or set(entry) != (
                fields | {"layer"} if version >= 3 else fields):
            raise ValueError("Invalid preset binding fields")
        if not all(isinstance(value, str) for value in entry.values()):
            raise ValueError("Preset binding identifiers must be strings")
        if version < 3 and entry["button"] not in ("a", "b", "x", "y", "view"):
            raise ValueError("This input requires preset schema version 3")
        if version == 1 and (
                entry["mode"] == "common" or entry["action"] == "disabled"):
            raise ValueError("Common and Disable require preset schema version 2")
        bindings.append(ButtonBinding(**entry))
    shift = data["shift"] if version >= 3 else "lt"
    if version < 4:
        bindings = _fold_viewer_into_common(bindings, shift)
    configuration = ButtonConfiguration(tuple(bindings), shift)
    return data["name"], ButtonConfiguration(tuple(sorted(
        configuration.bindings, key=lambda b: (b.mode, b.button, b.layer))), configuration.shift)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field: " + key)
        result[key] = value
    return result


def _read_json(path):
    with Path(path).open(encoding="utf-8-sig") as source:
        return json.load(source, object_pairs_hook=_unique_object)


def _write_json(path, data):
    path = Path(path)
    payload = json.dumps(data, indent=2, ensure_ascii=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=path.name + ".", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class PresetStore:
    def __init__(self, path):
        self.path = Path(path)
        self.selected = FACTORY
        self.configuration = ButtonConfiguration.defaults()
        self.warning = ""
        self._write_error = ""
        self._presets = {}
        try:
            data = _read_json(self.path)
        except FileNotFoundError:
            return
        except (OSError, ValueError, UnicodeError) as error:
            self._unreadable(error)
            return
        try:
            if not isinstance(data, dict) or set(data) != {"schema_version", "selected", "presets"}:
                raise ValueError("Invalid preset library fields")
            if type(data["schema_version"]) is not int or data["schema_version"] not in SUPPORTED_VERSIONS:
                raise ValueError("Unsupported preset library version")
            if not isinstance(data["selected"], str) or not isinstance(data["presets"], dict):
                raise ValueError("Invalid preset library selection or entries")
            names = set()
            for name in data["presets"]:
                validate_name(name)
                if name.casefold() == FACTORY.casefold() or name.casefold() in names:
                    raise ValueError("Conflicting names in preset library")
                names.add(name.casefold())
            self._presets = data["presets"]
        except ValueError as error:
            self._unreadable(error)
            return
        errors = []
        for name in self._presets:
            try:
                self.get(name)
            except ValueError as error:
                errors.append(name + ": " + str(error))
        try:
            self.configuration = self.get(data["selected"])
            self.selected = data["selected"]
        except ValueError as error:
            errors.append("Could not restore " + data["selected"] + "; using Factory: " + str(error))
        self.warning = "\n".join(errors)

    def _unreadable(self, error):
        self._write_error = (
            "Cannot read preset library " + str(self.path) + ": " + str(error)
            + ". Using Factory. The file is preserved; repair or move it and restart "
            "xstudio before saving locally.")
        self.warning = self._write_error

    def entries(self):
        entries = [{"name": FACTORY, "available": True, "error": ""}]
        for name in sorted(self._presets, key=str.casefold):
            error = ""
            try:
                self.get(name)
            except ValueError as invalid:
                error = str(invalid)
            entries.append({"name": name, "available": not error, "error": error})
        return entries

    def get(self, name):
        validate_name(name)
        if name == FACTORY:
            return ButtonConfiguration.defaults()
        if name not in self._presets:
            raise ValueError("Unknown controller preset: " + name)
        decoded_name, configuration = decode_preset(self._presets[name])
        if decoded_name != name:
            raise ValueError("Preset name does not match library entry")
        return configuration

    def _commit(self, presets, selected):
        if self._write_error:
            raise ValueError(self._write_error)
        _write_json(self.path, {
            "schema_version": SCHEMA_VERSION, "selected": selected, "presets": presets,
        })
        self._presets = presets
        self.selected = selected

    def save(self, name, configuration, replace=False, activate=True, select_after=None):
        validate_name(name)
        if name.casefold() == FACTORY.casefold():
            raise ValueError("Factory is read-only; use Save As with another name")
        existing = next((key for key in self._presets if key.casefold() == name.casefold()), None)
        if existing is not None:
            if not replace:
                raise FileExistsError("A preset named " + existing + " already exists")
            name = existing
        encoded = encode_preset(name, configuration)
        decode_preset(encoded)
        presets = {**self._presets, name: encoded}
        selected = select_after if select_after is not None else (name if activate else self.selected)
        selected_configuration = configuration if selected == name else self.get(selected)
        self._commit(presets, selected)
        self.configuration = selected_configuration
        return name

    def select(self, name):
        configuration = self.get(name)
        self._commit(self._presets, name)
        self.configuration = configuration
        return configuration

    def import_file(self, path, replace=False):
        name, configuration = decode_preset(_read_json(path))
        return self.save(name, configuration, replace=replace, activate=False)

    def export_file(self, path, name, configuration):
        path = Path(path)
        if path.resolve() == self.path.resolve():
            raise ValueError("Export cannot overwrite the local preset library")
        _write_json(path, encode_preset("Factory Copy" if name == FACTORY else name, configuration))
