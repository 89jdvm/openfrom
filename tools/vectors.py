"""Read and write the int8 vector files made by embed.mjs.

Row layout: float32 scale, then 384 int8 values; value = int8 * scale.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

DIM = 384
ROW = 4 + DIM


def load(prefix: Path) -> tuple[list[str], np.ndarray]:
    """(uids, float32 matrix of unit vectors)."""
    uids = [u for u in Path(f"{prefix}.uids").read_text(encoding="utf-8").split("\n") if u]
    raw = np.fromfile(f"{prefix}.bin", dtype=np.uint8)
    n = min(len(uids), raw.size // ROW)
    raw = raw[: n * ROW].reshape(n, ROW)
    scale = raw[:, :4].copy().view("<f4").reshape(n, 1)
    q = raw[:, 4:].view(np.int8).astype(np.float32)
    m = q * scale
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    return uids[:n], m


def load_raw(prefix: Path) -> tuple[list[str], np.ndarray]:
    """(uids, uint8 rows exactly as stored) for re-packing without re-quantising."""
    uids = [u for u in Path(f"{prefix}.uids").read_text(encoding="utf-8").split("\n") if u]
    raw = np.fromfile(f"{prefix}.bin", dtype=np.uint8)
    n = min(len(uids), raw.size // ROW)
    return uids[:n], raw[: n * ROW].reshape(n, ROW)


def save_raw(prefix: Path, uids: list[str], rows: np.ndarray) -> None:
    Path(f"{prefix}.uids").write_text("\n".join(uids) + ("\n" if uids else ""), encoding="utf-8")
    rows.astype(np.uint8).tofile(f"{prefix}.bin")
