#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验公共模块：树莓派 ↔ STM32 串口协议、CSV 记录、环境快照。

协议（与 STM32 工程 03 的 pi_link.c 一致）：
    $body*XX\r\n
    XX = body 所有 ASCII 字节的异或，两位大写十六进制
    波特率 115200，8N1

本模块只依赖 pyserial；实验脚本在树莓派上运行。
"""

from __future__ import annotations

import csv
import json
import os
import platform
import socket
import sys
import time
from datetime import datetime


# ============================================================================
# 一、协议
# ============================================================================

def crc8_xor(body: str) -> int:
    """$ 与 * 之间所有字节的异或。"""
    c = 0
    for b in body.encode("ascii", "ignore"):
        c ^= b
    return c


def frame(body: str) -> bytes:
    """拼成可直接写入串口的一整帧。"""
    return f"${body}*{crc8_xor(body):02X}\r\n".encode("ascii")


def parse_line(line: str):
    """
    解析一行。成功返回 (op, args)，失败返回 None。
    op   单字符，例如 'S' / 'P' / 'K'
    args 逗号分隔的字符串列表（不含 op）
    """
    line = line.strip()
    if not line.startswith("$") or "*" not in line:
        return None

    body, _, tail = line[1:].partition("*")
    if len(tail) < 2:
        return None
    try:
        want = int(tail[:2], 16)
    except ValueError:
        return None
    if crc8_xor(body) != want:
        return None

    parts = body.split(",")
    return parts[0], parts[1:]


# ============================================================================
# 二、串口
# ============================================================================

class SerialLink:
    """带纳秒时间戳的串口封装。

    send() 返回写入前的 monotonic_ns，read_lines() 返回接收时的
    monotonic_ns，两者相减就是软件层面的往返时延。
    """

    def __init__(self, port: str, baud: int = 115200, read_timeout: float = 0.02):
        try:
            import serial
        except ImportError:
            raise SystemExit("未安装 pyserial。树莓派执行：sudo apt install -y python3-serial")

        self.port = port
        self.baud = baud
        self.ser = serial.Serial(
            port, baud,
            bytesize=8, parity="N", stopbits=1,
            timeout=read_timeout)
        self.ser.reset_input_buffer()
        self._buf = b""

    # ---- 发送 ----
    def send(self, body: str) -> int:
        """发送一行 body（不含 $ 和 CRC），返回发送前的时间戳 ns。"""
        data = frame(body)
        t0 = time.perf_counter_ns()
        self.ser.write(data)
        self.ser.flush()
        return t0

    # ---- 接收 ----
    def read_lines(self, wait_s: float = 0.01):
        """
        读一小段时间，返回 [(recv_ns, line_str), ...]。
        只返回完整行（已去掉 CR/LF/空格）。
        """
        out = []
        deadline = time.perf_counter() + wait_s

        while True:
            n = self.ser.in_waiting
            if n:
                chunk = self.ser.read(n)
                ns = time.perf_counter_ns()
                self._buf += chunk

                while b"\n" in self._buf:
                    raw, self._buf = self._buf.split(b"\n", 1)
                    raw = raw.strip(b"\r ")
                    if raw:
                        out.append((ns, raw.decode("ascii", "ignore")))
                continue

            if time.perf_counter() >= deadline:
                break
            time.sleep(0.001)

        return out

    def wait_for(self, op: str, timeout_s: float):
        """
        等一条指定 op 的合法帧。
        返回 (recv_ns, raw_line, (op, args)) 或 None（超时）。
        期间收到的其它帧直接丢弃。
        """
        deadline = time.perf_counter() + timeout_s
        while True:
            for ns, line in self.read_lines(0.005):
                parsed = parse_line(line)
                if parsed is not None and parsed[0] == op:
                    return ns, line, parsed
            if time.perf_counter() >= deadline:
                return None

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


# ============================================================================
# 三、数据记录
# ============================================================================

class CsvLogger:
    """写 CSV，并把实验元信息另存为同名 _meta.json。"""

    def __init__(self, path: str, fieldnames, meta=None):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        self._f = open(path, "w", newline="", encoding="utf-8-sig")
        self._w = csv.DictWriter(self._f, fieldnames=list(fieldnames))
        self._w.writeheader()

        self.meta_path = os.path.splitext(path)[0] + "_meta.json"
        if meta is not None:
            with open(self.meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, ensure_ascii=False, indent=2)

    def write(self, row: dict):
        self._w.writerow(row)

    def close(self):
        self._f.close()

    def flush(self):
        self._f.flush()


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================================
# 四、环境快照与统计
# ============================================================================

def read_soc_temp_c():
    """树莓派 SoC 温度，读不到返回 None。"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        return None


def env_snapshot(port: str = "", baud: int = 115200) -> dict:
    snap = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "serial_port": port,
        "baud": baud,
        "soc_temp_c": read_soc_temp_c(),
    }
    try:
        snap["loadavg"] = list(os.getloadavg())
    except Exception:
        snap["loadavg"] = None
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    snap["mem_total_kb"] = int(line.split()[1])
                    break
    except Exception:
        pass
    return snap


def percentile(xs, p: float):
    """线性插值分位数，p 取 0~1。xs 为空返回 None。"""
    if not xs:
        return None
    xs = sorted(xs)
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return float(xs[lo] + (xs[hi] - xs[lo]) * (k - lo))


def default_out_path(name: str) -> str:
    """默认输出到 论文/data/，文件名带日期时间。"""
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(here), "data")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.join(data_dir, f"{name}_{stamp}.csv")
