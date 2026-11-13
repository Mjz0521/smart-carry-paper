#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 01：树莓派 ↔ STM32 串口往返时延（RTT）

方法：
    树莓派发 $P,<t_ms>，STM32 回 $P,<tick>（见 pi_link.c 的 Pi_SendPing）。
    每条命令只等一条回复，超时丢弃，避免把自发状态帧 $S 混进来。
    用 perf_counter_ns 记录发送前和收到回复的时刻。

用法（树莓派）：
    python3 exp01_uart_latency.py --port /dev/ttyAMA0
    python3 exp01_uart_latency.py --port /dev/ttyAMA0 --count 1000
    python3 exp01_uart_latency.py --port /dev/ttyAMA0 --interval-ms 10

输出：
    ../../data/exp01_uart_latency_<时间>.csv
    ../../data/exp01_uart_latency_<时间>_summary.json
"""

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (CsvLogger, SerialLink, default_out_path, env_snapshot,
                    percentile, write_json)


def main():
    ap = argparse.ArgumentParser(description="串口往返时延实验")
    ap.add_argument("--port", default="/dev/ttyAMA0", help="树莓派排针串口")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--count", type=int, default=1000, help="有效样本数")
    ap.add_argument("--warmup", type=int, default=20, help="预热次数，不计入结果")
    ap.add_argument("--interval-ms", type=float, default=0.0,
                    help="两次命令之间的间隔，默认 0 = 背靠背")
    ap.add_argument("--timeout-ms", type=float, default=200.0,
                    help="单次等待回复超时")
    ap.add_argument("--out", default="", help="CSV 输出路径，默认 data/ 下")
    args = ap.parse_args()

    out = args.out or default_out_path("exp01_uart_latency")
    meta = env_snapshot(args.port, args.baud)
    meta.update({
        "experiment": "exp01_uart_latency",
        "method": "ping_P",
        "count": args.count,
        "warmup": args.warmup,
        "interval_ms": args.interval_ms,
        "timeout_ms": args.timeout_ms,
        "note": "RTT 为软件时间戳，包含 pyserial 写入/读取与 USB-UART 驱动开销",
    })

    log = CsvLogger(out, [
        "seq", "t_wall", "rtt_us", "ok", "reply", "outlier",
    ], meta=meta)

    link = SerialLink(args.port, args.baud, read_timeout=0.02)
    rtts = []
    timeouts = 0
    seq = 0

    print(f"[exp01] {args.port} @ {args.baud} 8N1")
    print(f"[exp01] warmup={args.warmup}  count={args.count}  "
          f"interval={args.interval_ms}ms  timeout={args.timeout_ms}ms")
    print(f"[exp01] 输出：{out}")

    try:
        # 预热：只发不收，让链路和驱动进入稳态
        for _ in range(args.warmup):
            link.send(f"P,{int(time.monotonic() * 1000) & 0x7FFFFFFF}")
            link.wait_for("P", 0.05)
            if args.interval_ms:
                time.sleep(args.interval_ms / 1000.0)

        # 正式采集
        while len(rtts) + timeouts < args.count:
            seq += 1
            t_send = link.send(
                f"P,{int(time.monotonic() * 1000) & 0x7FFFFFFF}")
            got = link.wait_for("P", args.timeout_ms / 1000.0)

            if got is None:
                timeouts += 1
                log.write({
                    "seq": seq,
                    "t_wall": datetime.now().isoformat(timespec="milliseconds"),
                    "rtt_us": "",
                    "ok": 0,
                    "reply": "",
                    "outlier": "",
                })
            else:
                t_recv, line, _ = got
                rtt = (t_recv - t_send) / 1000.0
                rtts.append(rtt)
                log.write({
                    "seq": seq,
                    "t_wall": datetime.now().isoformat(timespec="milliseconds"),
                    "rtt_us": f"{rtt:.1f}",
                    "ok": 1,
                    "reply": line,
                    "outlier": "",
                })

            if args.interval_ms:
                time.sleep(args.interval_ms / 1000.0)

            done = len(rtts) + timeouts
            if done % max(1, args.count // 10) == 0:
                print(f"[exp01] {done}/{args.count}  超时 {timeouts}", flush=True)

    except KeyboardInterrupt:
        print("\n[exp01] 手动中止，按已采样本汇总")
    finally:
        link.close()
        log.close()

    done = len(rtts) + timeouts
    summary = {
        "experiment": "exp01_uart_latency",
        "time": datetime.now().isoformat(timespec="seconds"),
        "csv": os.path.abspath(out),
        "port": args.port,
        "baud": args.baud,
        "attempted": done,
        "ok": len(rtts),
        "timeouts": timeouts,
        "loss_rate": (timeouts / done) if done else None,
        "interval_ms": args.interval_ms,
        "rtt_us": {
            "min": min(rtts) if rtts else None,
            "p50": percentile(rtts, 0.50),
            "p95": percentile(rtts, 0.95),
            "p99": percentile(rtts, 0.99),
            "max": max(rtts) if rtts else None,
            "mean": (sum(rtts) / len(rtts)) if rtts else None,
        },
    }
    summary["rtt_us"] = {
        k: (round(v, 2) if isinstance(v, float) else v)
        for k, v in summary["rtt_us"].items()
    }

    summary_path = os.path.splitext(out)[0] + "_summary.json"
    write_json(summary_path, summary)

    print("\n========== 结果 ==========")
    print(f"有效样本 {len(rtts)} / {done}，超时 {timeouts}")
    if rtts:
        print(f"RTT (us)  min={summary['rtt_us']['min']:.1f}  "
              f"P50={summary['rtt_us']['p50']:.1f}  "
              f"P95={summary['rtt_us']['p95']:.1f}  "
              f"P99={summary['rtt_us']['p99']:.1f}  "
              f"max={summary['rtt_us']['max']:.1f}  "
              f"mean={summary['rtt_us']['mean']:.1f}")
    print(f"CSV     ：{out}")
    print(f"Summary ：{summary_path}")


if __name__ == "__main__":
    main()
