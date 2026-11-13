#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 02：串口长时通信可靠性

方法：
    以固定频率持续发 $P，统计回复、超时、CRC/格式错误。
    用 $P 而不是 $S，因为 $P 只在被请求时回复，
    不会和 STM32 每 500 ms 自发的心跳状态帧混淆。

用法（树莓派）：
    python3 exp02_uart_reliability.py --port /dev/ttyAMA0 --rate-hz 10 --duration-s 3600
    python3 exp02_uart_reliability.py --port /dev/ttyAMA0 --rate-hz 20 --duration-s 60

输出：
    data/exp02_uart_reliability_<时间>.csv        每秒一行的统计
    data/exp02_uart_reliability_<时间>_summary.json
"""

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (CsvLogger, SerialLink, default_out_path, env_snapshot,
                    parse_line, write_json)


def wait_reply(link, timeout_s, counters):
    """等一条 $P 回复，期间统计其它帧和坏帧。"""
    deadline = time.perf_counter() + timeout_s

    while True:
        for ns, line in link.read_lines(0.005):
            parsed = parse_line(line)
            if parsed is None:
                counters["bad_frames"] += 1
                continue
            if parsed[0] == "P":
                return ns
            counters["other_frames"] += 1

        if time.perf_counter() >= deadline:
            return None


def main():
    ap = argparse.ArgumentParser(description="串口长时通信可靠性实验")
    ap.add_argument("--port", default="/dev/ttyAMA0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--rate-hz", type=float, default=10.0, help="每秒发送次数")
    ap.add_argument("--duration-s", type=float, default=3600.0,
                    help="持续时长，默认 1 小时")
    ap.add_argument("--timeout-ms", type=float, default=100.0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.rate_hz <= 0:
        raise SystemExit("--rate-hz 必须大于 0")

    out = args.out or default_out_path("exp02_uart_reliability")
    meta = env_snapshot(args.port, args.baud)
    meta.update({
        "experiment": "exp02_uart_reliability",
        "method": "ping_P",
        "rate_hz": args.rate_hz,
        "duration_s": args.duration_s,
        "timeout_ms": args.timeout_ms,
        "note": "bad_frames 指 $ 开头但 CRC/格式不合法的帧；"
                "other_frames 指合法但不是 P 的帧（如自发 $S）",
    })

    log = CsvLogger(out, [
        "second", "sent", "replied", "timeout", "bad_frames",
        "other_frames", "mean_rtt_us",
    ], meta=meta)

    link = SerialLink(args.port, args.baud, read_timeout=0.02)

    totals = {
        "sent": 0, "replied": 0, "timeout": 0,
        "bad_frames": 0, "other_frames": 0,
    }
    rtts_all = []
    period = 1.0 / args.rate_hz
    timeout_s = args.timeout_ms / 1000.0

    print(f"[exp02] {args.port} @ {args.baud} 8N1")
    print(f"[exp02] rate={args.rate_hz}Hz  duration={args.duration_s}s")
    print(f"[exp02] 输出：{out}")

    t_start = time.perf_counter()
    next_send = t_start
    cur_sec = 0
    bucket = {"sent": 0, "replied": 0, "timeout": 0,
              "bad_frames": 0, "other_frames": 0}
    bucket_rtts = []
    last_flush = t_start

    try:
        while True:
            now = time.perf_counter()
            elapsed = now - t_start
            if elapsed >= args.duration_s:
                break

            # 到点才发，避免速率漂移
            if now < next_send:
                time.sleep(min(0.005, next_send - now))
                continue

            sec = int(elapsed)
            if sec != cur_sec:
                if bucket["sent"]:
                    mean_rtt = (sum(bucket_rtts) / len(bucket_rtts)
                                if bucket_rtts else "")
                    log.write({
                        "second": cur_sec,
                        "sent": bucket["sent"],
                        "replied": bucket["replied"],
                        "timeout": bucket["timeout"],
                        "bad_frames": bucket["bad_frames"],
                        "other_frames": bucket["other_frames"],
                        "mean_rtt_us": (f"{mean_rtt:.1f}" if mean_rtt != "" else ""),
                    })
                cur_sec = sec
                bucket = {"sent": 0, "replied": 0, "timeout": 0,
                          "bad_frames": 0, "other_frames": 0}
                bucket_rtts = []

            t_send = link.send(
                f"P,{int(time.monotonic() * 1000) & 0x7FFFFFFF}")
            got = wait_reply(link, timeout_s, bucket)

            bucket["sent"] += 1
            totals["sent"] += 1

            if got is None:
                bucket["timeout"] += 1
                totals["timeout"] += 1
            else:
                rtt = (got - t_send) / 1000.0
                bucket_rtts.append(rtt)
                rtts_all.append(rtt)
                bucket["replied"] += 1
                totals["replied"] += 1

            totals["bad_frames"] += bucket["bad_frames"]
            totals["other_frames"] += bucket["other_frames"]
            bucket["bad_frames"] = 0
            bucket["other_frames"] = 0

            next_send += period
            # 如果上一次等待超时导致已经落后，重新对齐节奏，避免追赶式突发发送
            if next_send < time.perf_counter() - period:
                next_send = time.perf_counter() + period

            # 每 60 s 打印进度并落盘
            if now - last_flush >= 60.0:
                last_flush = now
                log.flush()
                print(f"[exp02] {elapsed:.0f}s  sent={totals['sent']}  "
                      f"replied={totals['replied']}  "
                      f"timeout={totals['timeout']}", flush=True)

    except KeyboardInterrupt:
        print("\n[exp02] 手动中止，按已采样本汇总")
    finally:
        link.close()
        log.close()

    sent = totals["sent"]
    summary = {
        "experiment": "exp02_uart_reliability",
        "time": datetime.now().isoformat(timespec="seconds"),
        "csv": os.path.abspath(out),
        "port": args.port,
        "baud": args.baud,
        "rate_hz": args.rate_hz,
        "duration_s": args.duration_s,
        "sent": sent,
        "replied": totals["replied"],
        "timeout": totals["timeout"],
        "loss_rate": (totals["timeout"] / sent) if sent else None,
        "bad_frame_rate": (totals["bad_frames"] / sent) if sent else None,
        "bad_frames": totals["bad_frames"],
        "other_frames": totals["other_frames"],
        "mean_rtt_us": (sum(rtts_all) / len(rtts_all)) if rtts_all else None,
    }
    if summary["mean_rtt_us"] is not None:
        summary["mean_rtt_us"] = round(summary["mean_rtt_us"], 2)

    summary_path = os.path.splitext(out)[0] + "_summary.json"
    write_json(summary_path, summary)

    print("\n========== 结果 ==========")
    print(f"发送 {sent}，回复 {totals['replied']}，超时 {totals['timeout']}")
    if sent:
        print(f"丢包率 {summary['loss_rate'] * 100:.4f}%  "
              f"坏帧率 {summary['bad_frame_rate'] * 100:.4f}%")
    print(f"CSV     ：{out}")
    print(f"Summary ：{summary_path}")


if __name__ == "__main__":
    main()
