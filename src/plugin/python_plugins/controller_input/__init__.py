# SPDX-License-Identifier: Apache-2.0
import sys


def create_plugin_instance(connection):
    if sys.platform != "win32":
        raise RuntimeError("Controller Input requires Windows XInput 1.4")
    from .controller import ControllerPlugin
    return ControllerPlugin(connection)
