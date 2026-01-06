#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def build_cmd(args: argparse.Namespace, target: list[str]) -> list[str]:
    """
    构造最终执行命令。
    target：欲透传 token
    """
    if target and target[0] == "--":
        target = target[1:]
    if not target:
        raise SystemExit("未提供目标命令。用法示例：python restart_runner.py -- your_task.py --arg 1")

    prefix = [sys.executable]
    if not args.buffered:
        prefix += ["-u"]

    return prefix + target


def start_process(cmd: list[str], log_file: Path, cwd: str | None, extra_env: dict[str, str] | None) -> subprocess.Popen:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    lf = open(log_file, "ab", buffering=0)  # 注意：这里句柄未关闭（见文末建议）

    env = None
    if extra_env:
        env = dict(os.environ)
        env.update(extra_env)

    popen_kwargs = dict(
        stdout=lf,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        cwd=cwd,
        env=env,
    )

    # 便于“杀进程树”：Unix 用新 session；Windows 用新进程组
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    return subprocess.Popen(cmd, **popen_kwargs)


def terminate_process_tree(p: subprocess.Popen, grace_seconds: int) -> None:
    """优雅退出 -> 超时强杀（含子进程）。"""
    if p.poll() is not None:
        return

    if os.name == "nt":
        try:
            p.send_signal(signal.CTRL_BREAK_EVENT)
            p.wait(timeout=grace_seconds)
            return
        except Exception:
            pass
        subprocess.run(
            ["taskkill", "/PID", str(p.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

        try:
            p.wait(timeout=grace_seconds)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            return

        p.wait(timeout=grace_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="周期性重启运行某个 Python 任务（支持当前解释器），并透传目标命令参数。"
    )

    parser.add_argument("--cycle-seconds", type=int, default=7200, help="每轮最长运行秒数（默认 7200）")
    parser.add_argument("--restart-delay", type=int, default=15, help="重启前等待秒数（默认 15）")
    parser.add_argument("--grace-seconds", type=int, default=30, help="优雅退出等待秒数（默认 30）")

    parser.add_argument("--log-dir", default="/data2/data/infinigen/", help="日志目录")
    parser.add_argument("--buffered", action="store_true", help="给 python 加 -u，减少输出缓冲问题,默认就是无缓冲")

    # 关键：REMAINDER 必须放在最后，否则后面的可选参数都会被吞掉
    parser.add_argument("--max-runs", type=int, default=0, help="最多运行轮数；0 表示无限循环（默认 0）")
    parser.add_argument("target", nargs=argparse.REMAINDER, help="用 -- 分隔后面的目标命令，例如：-- your_task.py --a 1")

    args = parser.parse_args()

    cwd = Path.cwd().as_posix()
    cmd = build_cmd(args, args.target)
    log_dir = Path(args.log_dir)

    print("[runner] command:", cmd)

    run_index = 0
    while args.max_runs <= 0 or run_index < args.max_runs:
        run_index += 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"run_{run_index:04d}_{ts}.log"
        print(f"[runner] start #{run_index}, log={log_file}")
        print(f"[runner] start cmd: {cmd}")

        p = start_process(cmd, log_file, cwd=cwd, extra_env=None)
        start = time.monotonic()

        try:
            try:
                rc = p.wait(timeout=args.cycle_seconds)
                reason = f"exited rc={rc}"
                # app 在达到时延之前正常退出就意味着该终止了，所以看门狗在这里退出循环
                break

            except subprocess.TimeoutExpired:
                reason = f"timeout {args.cycle_seconds}s"
                terminate_process_tree(p, args.grace_seconds)

        except KeyboardInterrupt:
            print("[runner] interrupted, terminating...")
            terminate_process_tree(p, args.grace_seconds)
            return 130

        elapsed = int(time.monotonic() - start)
        print(f"[runner] stop #{run_index} ({reason}), elapsed={elapsed}s; restart in {args.restart_delay}s")

        if args.max_runs > 0 and run_index >= args.max_runs:
            break

        time.sleep(args.restart_delay)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
