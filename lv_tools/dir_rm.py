#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional


def dir_size_bytes_du(path: Path) -> int:
    """
    使用 `du -sb` 获取目录大小（字节）。这是“磁盘占用”的近似口径，速度快。
    """
    # -s: summary, -b: bytes
    # 输出形如: "<bytes>\t<path>"
    out = subprocess.check_output(["du", "-sb", str(path)], text=True)
    return int(out.split()[0])


def safe_to_clear(path: Path) -> None:
    """
    基础安全校验：避免误删根目录/空路径等明显危险路径。
    你可以按需加更严格的白名单规则。
    """
    rp = path.resolve()
    if str(rp) in ("/", ""):
        raise ValueError(f"Refuse to clear dangerous path: {rp}")
    if not rp.exists():
        raise FileNotFoundError(rp)
    if not rp.is_dir():
        raise NotADirectoryError(rp)


def clear_dir_contents(path: Path, *, exclude_names: Optional[Iterable[str]] = None, dry_run: bool = False) -> None:
    """
    清空目录内容（保留目录本身）。
    exclude_names: 例如 [".keep", "important_subdir"]
    """
    exclude = set(exclude_names or [])
    for entry in path.iterdir():
        if entry.name in exclude:
            continue
        if dry_run:
            print(f"[DRY-RUN] would remove: {entry}")
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink(missing_ok=True)


def clear_dir_if_exceeds(
    target_dir: str | os.PathLike,
    *,
    threshold_bytes: int,
    exclude_names: Optional[Iterable[str]] = None,
    dry_run: bool = False,
) -> bool:
    """
    返回 True 表示触发并执行（或预演）了清空；False 表示未达到阈值。
    """
    p = Path(target_dir)
    safe_to_clear(p)

    size = dir_size_bytes_du(p)
    print(f"dir={p} size={size} bytes threshold={threshold_bytes} bytes")

    if size >= threshold_bytes:
        print("threshold reached, clearing contents...")
        clear_dir_contents(p, exclude_names=exclude_names, dry_run=dry_run)
        return True

    print("threshold not reached, do nothing.")
    return False


if __name__ == "__main__":
    # 目录超过 50 GiB 则清空（保留 .keep）
    clear_dir_if_exceeds(
        "/home/ubuntu/.cache/ov/texturecache",
        threshold_bytes=50 * 1024**3,
        exclude_names=[".keep"],
        dry_run=False,  # 先预演，确认无误后改成 False
    )
