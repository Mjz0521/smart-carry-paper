# 实验 04：电机定位重复性（设计稿）

> 状态：**待固件支持**。当前 STM32 工程 03 没有"读位置"的 Pi 端命令，
> 树莓派发起的移动只有抓取状态机内部使用。需要先给 `pi_link.c` 加两条命令。

## 1. 目标

量化同一个目标位置往复 N 次后的**到位偏差**，得到：

- 平均偏差、标准差、最大偏差
- 偏差随循环次数的漂移（是否有累积误差）
- 串口位置模式在 16 细分（3200 脉冲/圈）下的实际重复精度

这是论文第 4 章最硬的一组数据，也是最容易做的对比实验的基线。

## 2. 需要的固件扩展（工程 03）

### 2.1 新命令 `$C,MOVE,dx,dy`

| 字段 | 单位 | 含义 |
|---|---|---|
| dx | 0.1 mm | 车体前后（+ 前） |
| dy | 0.1 mm | 车体左右（+ 左） |

收到后调用 `Motion_ChassisMove(dx, dy, speed, acc)`，完成后回 `$K,seq,1`。
速度/加速度用固定实验参数（例如 100 mm/s、acc=150），写死在固件里，
保证每次实验条件一致。

### 2.2 新命令 `$R,seq` → 回 `$R,seq,addr1,pos1,addr2,pos2,...`

`pos` 用 `Emm42_ReadPos()` 读，单位 1/65536 圈（有符号）。
5 台电机全部读一遍，读到哪台回哪台。

### 2.3 参考实现（`pi_link.c` 的 `Pi_HandleLine` 里加分支）

```c
case 'C':
    if (strncmp(p, "MOVE,", 5) == 0)
    {
        int32_t dx, dy;
        p += 5;
        if (!NextInt(&p, &dx)) return;
        if (!NextInt(&p, &dy)) return;
        if (Motion_ChassisMove((int16_t)dx, (int16_t)dy,
                               MOVE_EXP_SPEED_MM_S, MOVE_EXP_ACC))
            Pi_SendAck(0, 1);
        else
            Pi_SendAck(0, 0);
    }
    else if (strncmp(p, "START", 5) == 0) ...
```

`$R` 分支遍历 `MOTOR_FL..MOTOR_LIFT` 调 `Emm42_ReadPos(addr, &pos)`，
用 `PutInt` 拼进回复帧。

> 注意：`Motion_ChassisMove` 是非阻塞的，`$K` 只表示"命令已接受"。
> 实验脚本要等状态帧 `$S` 回到 `1 (IDLE)` 或 `4 (READY)`，
> 再发 `$R` 读位置。或者由固件在运动完成后再主动发一次 `$R`。

## 3. 实验流程（树莓派端脚本）

```
固定起始点：
  1. $C,ZERO（升降清零，仅第一次）
  2. 让底盘回到机械原点（手动或限位开关）

循环 i = 1..50：
  3. $C,MOVE,+200,0      # 前进 20.0 mm
  4. 等运动完成（$S,state=IDLE 或 READY）
  5. $R                  # 读 5 台电机位置
  6. 记录 pos_forward[i]
  7. $C,MOVE,-200,0      # 退回 20.0 mm
  8. 等运动完成
  9. $R
 10. 记录 pos_back[i]
```

## 4. 数据处理

以"相对起点"的脉冲数换算成毫米：

```
轮周长 75.0 mm -> 每圈 3200 脉冲 -> 0.02344 mm/脉冲
位置读数单位 1/65536 圈 -> 1 脉冲 = 3200/65536 圈
```

对每个循环计算：

- 前进到位偏差 `e_f[i] = pos_forward[i] - pos_target`
- 往返净偏差 `e_net[i] = pos_back[i] - pos_start`
- 全部样本的 mean / std / max |e|
- 用箱线图或误差带图展示

## 5. 输出文件

```
data/exp04_motor_repeatability_<时间>.csv
字段：cycle, phase, motor_addr, pos_raw, pos_mm, error_mm, state, err
data/exp04_motor_repeatability_<时间>_summary.json
字段：n, mean_error_mm, std_error_mm, max_abs_error_mm, drift_mm_per_cycle
```

## 6. 对照实验（论文加分项）

| 组 | 条件 | 目的 |
|---|---|---|
| A | 串口位置模式，16 细分 | 基线 |
| B | 串口位置模式，32 细分 | 细分对精度的影响 |
| C | 脉冲模式，STM32 自己发脉冲 | 与串口模式对比（坑记录第 7 条） |

每组至少 50 次，同一负载、同一电压（优先 24 V）。

## 7. 现在能做什么

1. 先按本设计改固件并重新编译（Keil，0 Error / 0 Warning）。
2. 机械未装车前，可以把电机架空、只转单台做**空载**重复性，
   数据同样有效，论文里注明"空载"即可。
3. 装车后再补带负载数据，形成空载 / 负载对比。
