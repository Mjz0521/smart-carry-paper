# 实验脚本使用说明

> 目标：把日常调试变成**可复现、可统计、可画图**的实验数据。
> 所有脚本在树莓派上运行，输出 CSV 到 `../data/`。

## 0. 前置条件

| 项 | 要求 |
|---|---|
| 树莓派 | Pi 5，排针串口 `/dev/ttyAMA0`（见 `config.txt` 的 `dtoverlay=uart0-pi5`） |
| STM32 固件 | 工程 `03-树莓派与ZET6通信识别物料追踪` 已烧录 |
| 接线 | Pi GPIO14 → STM32 PB11，GPIO15 → PB10，GND 共地 |
| Python 库 | `pyserial`、`opencv-python`（exp03 需要） |

```bash
sudo apt install -y python3-serial python3-opencv
```

## 1. 把脚本传到树莓派

在电脑上（PowerShell）：

```powershell
scp -r "D:\树莓派\论文\experiments" pi@10.42.0.1:~/
```

在树莓派上：

```bash
cd ~/experiments
python3 exp01_uart_latency.py --port /dev/ttyAMA0 --count 100
```

## 2. 实验清单

| 实验 | 脚本 | 依赖 | 能否现在做 |
|---|---|---|---|
| 01 串口往返时延 | `exp01_uart_latency.py` | 固件 03 | ✅ 能 |
| 02 长时通信可靠性 | `exp02_uart_reliability.py` | 固件 03 | ✅ 能 |
| 03 Pi5 视觉性能边界 | `exp03_pi_performance.py` | 摄像头 + OpenCV | ✅ 能 |
| 04 电机定位重复性 | `exp04_motor_repeatability.md` | 需固件加 `$C,MOVE` / `$R` | ⚠️ 待固件 |
| 05 视觉定位精度标定 | 待写 | 标定板 | ⏳ |
| 06 颜色识别鲁棒性 | 待写 | 固定光照条件 | ⏳ |

## 3. 常用命令

```bash
# 实验 01：背靠背 1000 次
python3 exp01_uart_latency.py --port /dev/ttyAMA0 --count 1000

# 实验 01：每 10 ms 发一次，模拟正常控制周期
python3 exp01_uart_latency.py --port /dev/ttyAMA0 --count 1000 --interval-ms 10

# 实验 02：10 Hz 连续跑 1 小时
python3 exp02_uart_reliability.py --port /dev/ttyAMA0 --rate-hz 10 --duration-s 3600

# 实验 02：先跑 60 秒验证脚本
python3 exp02_uart_reliability.py --port /dev/ttyAMA0 --rate-hz 10 --duration-s 60

# 实验 03：只测采集，3 种分辨率 × 3 次
python3 exp03_pi_performance.py --camera 0 --runs 3

# 实验 03：采集 + 六色检测
python3 exp03_pi_performance.py --camera 0 --detect \
    --tracker ~/color_tracker.py --runs 3
```

## 4. 数据命名与存放

```
论文/
├── data/      原始 CSV + summary.json + meta.json（只追加，不覆盖）
├── figures/   由 data 生成的图（脚本可重跑）
├── records/   实验记录模板与台账
└── paper/     论文正文与大纲
```

- 每次运行自动生成 `实验名_YYYY-MM-DD_HHMMSS.csv`
- 同目录自动生成 `_summary.json` 和 `_meta.json`
- **原始数据永远不要手动改**；清洗/统计在分析脚本里做

## 5. 画图

论文图表建议用 Python + matplotlib 从 CSV 直接生成，保证可复现：

```bash
pip install matplotlib pandas
```

图表要求（普刊）：

- 分辨率 ≥ 300 dpi，PNG
- 坐标轴有单位，图例清晰
- 黑白打印也能区分（线型 + 标记，不只靠颜色）

## 6. 注意事项

1. **先跑短时间验证**（`--duration-s 60`），再跑 1 小时长测。
2. 长测期间不要拔插串口、不要给 STM32 重新上电。
3. 实验 03 会让 Pi 升温，跑完等温度回落再做下一组。
4. 每次实验前在 `records/实验台账.csv` 里登记一行。
5. RTT 是**软件时间戳**，论文里要写清测量边界：
   从 pyserial 写入前到读到回复，不含 STM32 内部处理时间的硬件级测量。
