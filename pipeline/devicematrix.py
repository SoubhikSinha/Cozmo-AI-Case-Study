from __future__ import annotations

import json
from pathlib import Path


def render_device_matrix(run_log_path: Path) -> str:
    """Read a JSON-lines benchmark run log (tier, device, measured_error_cm)
    and render the device-matrix markdown table. Not implemented until real
    benchmark runs exist to read.
    """
    raise NotImplementedError("no benchmark runs recorded yet")
