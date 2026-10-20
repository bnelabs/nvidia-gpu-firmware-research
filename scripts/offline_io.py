"""Read copied regular artifacts; reject device and kernel pseudo-files first.

This is an accidental-use guard. CPU-only OS isolation remains the real boundary.
"""
from pathlib import Path


def read_artifact(path):
    resolved = Path(path).resolve(strict=True)
    for root in (Path("/dev"), Path("/proc"), Path("/sys")):
        if resolved == root or root in resolved.parents:
            raise ValueError("offline analysis requires a copied regular artifact, not " + str(root))
    if not resolved.is_file():
        raise ValueError("offline input is not a regular artifact file")
    return resolved.read_bytes()
