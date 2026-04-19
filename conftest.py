"""pytest configuration for the pydita test suite.

Sets DITA_OT_DIR if not already set, searching common locations.
This must run before any ditalib module is imported so the DTD-aware
parser gets the catalog path on its first (lazy) call.
"""
import os

def _find_dita_ot() -> str | None:
    """Return the first usable DITA OT directory, or None."""
    candidates = [
        # Oxygen XML Editor (macOS)
        "/Applications/Oxygen XML Editor/frameworks/dita/DITA-OT",
        # Common manual install locations
        os.path.expanduser("~/apps/dita-ot"),
        os.path.expanduser("~/dita-ot"),
        "/usr/local/dita-ot",
    ]
    for path in candidates:
        catalog = os.path.join(path, "catalog-dita.xml")
        if os.path.isfile(catalog):
            return path
    return None


if not os.environ.get("DITA_OT_DIR"):
    found = _find_dita_ot()
    if found:
        os.environ["DITA_OT_DIR"] = found
