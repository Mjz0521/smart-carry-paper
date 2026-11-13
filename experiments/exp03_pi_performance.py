#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 03：树莓派 5（2GB）视觉性能边界

测量不同分辨率下的：
    帧率 FPS、进程 CPU 占用、SoC 温度、进程内存峰值。
可选 --detect：在采集循环里同时跑 color_tracker 的 HSV 六色检测，
用来对比「纯采集」和「采集 + 识别」的开销。

用法（树莓派）：
    python3 exp03_pi_performance.py --camera 0
    python3 exp03_pi_performance.py --camera 0 --detect
    python3 exp03_pi_performance.py --camera 0 --detect \
        --resolutions 320x240,640x480,1280x720 --seconds 15 --runs 3
    python3 exp03_pi_performance.py --camera 0 --detect \
        --tracker ~/color_tracker.py --colors red,yellow,blue

输出：
    data/exp03_pi_performance_<时间>.csv
    data/exp03_pi_performance_<时间>_meta.json
"""

import argparse
import importlib.util
import os
import sys
import time
from datetime import datetime

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import CsvLogger, default_out_path, env_snapshot, read_soc_temp_c


def load_tracker(path):
    """从指定路径加载 color_tracker.py，复用它的 HSV 检测函数。"""
    if not path or not os.path.isfile(path):
        raise SystemExit(f"找不到 color_tracker.py：{path}")

    spec = importlib.util.spec_from_file_location("ct_module", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_resolutions(text):
    out = []
    for item in text.split(","):
        item = item.strip().lower()
        if not item:
            continue
        if "x" not in item:
            raise SystemExit(f"分辨率格式应为 宽x高：{item}")
        w, h = item.split("x", 1)
        out.append((int(w), int(h)))
    if not out:
        raise SystemExit("--resolutions 不能为空")
    return out


def rss_mb():
    """当前进程常驻内存 MB（Linux /proc/self/status）。"""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    return None


def open_camera(index, width, height):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise SystemExit(
            f"打不开摄像头 {index}。先确认 ls /dev/video*，再试 --camera 0/1/2")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def run_one(cap, seconds, detect_mod, selected, kernel):
    """跑一次测量，返回统计字典。"""
    # 预热：读掉启动阶段的不稳定帧
    warm_end = time.perf_counter() + 2.0
    while time.perf_counter() < warm_end:
        cap.read()

    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    temp0 = read_soc_temp_c()
    frames = 0
    last_frame = None

    while True:
        now = time.perf_counter()
        if now - wall0 >= seconds:
            break

        ok, frame = cap.read()
        if not ok or frame is None:
            break

        if detect_mod is not None:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            if kernel is None:
                kernel = cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE, (5, 5))
            for name in selected:
                detect_mod.detect_candidates(
                    hsv, detect_mod.COLOR_RANGES[name],
                    150.0, 7.0, 0.35, kernel)

        last_frame = frame
        frames += 1

    wall = time.perf_counter() - wall0
    cpu = time.process_time() - cpu0
    temp1 = read_soc_temp_c()

    return {
        "frames": frames,
        "seconds": round(wall, 3),
        "fps": round(frames / wall, 2) if wall > 0 else 0.0,
        "cpu_pct": round(cpu / wall * 100.0, 2) if wall > 0 else None,
        "temp_before_c": temp0,
        "temp_after_c": temp1,
        "rss_mb": (round(rss_mb(), 1) if rss_mb() is not None else None),
        "actual_w": int(last_frame.shape[1]) if last_frame is not None else None,
        "actual_h": int(last_frame.shape[0]) if last_frame is not None else None,
        "cpu_seconds": round(cpu, 3),
    }


def main():
    ap = argparse.ArgumentParser(description="树莓派视觉性能边界实验")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--resolutions", default="320x240,640x480,1280x720")
    ap.add_argument("--seconds", type=float, default=15.0,
                    help="每个分辨率的测量时长")
    ap.add_argument("--runs", type=int, default=1,
                    help="每个配置重复几次")
    ap.add_argument("--detect", action="store_true",
                    help="采集循环里同时跑 HSV 六色检测")
    ap.add_argument("--tracker", default="",
                    help="color_tracker.py 路径；--detect 时必填")
    ap.add_argument("--colors", default="red,yellow,blue,green,black,lightblue")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.detect and not args.tracker:
        raise SystemExit("--detect 需要 --tracker 指向 color_tracker.py")

    resolutions = parse_resolutions(args.resolutions)
    selected = [c.strip().lower() for c in args.colors.split(",") if c.strip()]

    detect_mod = load_tracker(args.tracker) if args.detect else None
    if detect_mod is not None:
        unknown = [c for c in selected if c not in detect_mod.COLOR_RANGES]
        if unknown:
            raise SystemExit(f"color_tracker.py 里没有这些颜色：{unknown}")

    out = args.out or default_out_path("exp03_pi_performance")
    meta = env_snapshot()
    meta.update({
        "experiment": "exp03_pi_performance",
        "camera": args.camera,
        "resolutions": [f"{w}x{h}" for w, h in resolutions],
        "seconds": args.seconds,
        "runs": args.runs,
        "mode": "detect" if args.detect else "capture",
        "colors": selected if args.detect else [],
        "tracker": os.path.abspath(args.tracker) if args.detect else "",
        "note": "cpu_pct 是本进程 CPU 时间/墙钟时间，OpenCV 多线程时可能超过 100",
    })

    log = CsvLogger(out, [
        "run", "mode", "request_w", "request_h", "actual_w", "actual_h",
        "frames", "seconds", "fps", "cpu_pct", "cpu_seconds",
        "temp_before_c", "temp_after_c", "rss_mb",
    ], meta=meta)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    print(f"[exp03] camera={args.camera}  mode={meta['mode']}  "
          f"seconds={args.seconds}  runs={args.runs}")
    print(f"[exp03] 输出：{out}")

    run_id = 0
    try:
        for w, h in resolutions:
            for r in range(args.runs):
                run_id += 1
                cap = open_camera(args.camera, w, h)
                try:
                    stats = run_one(
                        cap, args.seconds, detect_mod, selected, kernel)
                finally:
                    cap.release()

                row = {
                    "run": run_id,
                    "mode": meta["mode"],
                    "request_w": w,
                    "request_h": h,
                    "actual_w": stats["actual_w"],
                    "actual_h": stats["actual_h"],
                    "frames": stats["frames"],
                    "seconds": stats["seconds"],
                    "fps": stats["fps"],
                    "cpu_pct": stats["cpu_pct"],
                    "cpu_seconds": stats["cpu_seconds"],
                    "temp_before_c": stats["temp_before_c"],
                    "temp_after_c": stats["temp_after_c"],
                    "rss_mb": stats["rss_mb"],
                }
                log.write(row)
                log.flush()

                print(f"[exp03] {w}x{h} run {r + 1}/{args.runs}: "
                      f"实际 {stats['actual_w']}x{stats['actual_h']}  "
                      f"FPS={stats['fps']:.2f}  CPU={stats['cpu_pct']}%  "
                      f"温度 {stats['temp_before_c']}->{stats['temp_after_c']}C",
                      flush=True)

    except KeyboardInterrupt:
        print("\n[exp03] 手动中止，已采数据已落盘")
    finally:
        log.close()

    print(f"\n完成。CSV：{out}")
    print(f"元信息：{os.path.splitext(out)[0]}_meta.json")


if __name__ == "__main__":
    main()
