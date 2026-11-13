#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成《智能搬运项目与论文工作进度报告》docx。

用法（Windows）：
    python -P build_progress_doc.py

输出：
    D:\\树莓派\\论文\\docs\\论文进度报告_2026-11-13.docx
"""

import os
from datetime import datetime

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "论文进度报告_2026-11-13.docx")

REPORT_DATE = "2026-11-13"


# ============================================================================
# 样式工具
# ============================================================================

def set_run_font(run, size=10.5, bold=False, east="宋体",
                 ascii_font="Times New Roman", color=None):
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), east)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)


def add_para(doc, text="", size=10.5, bold=False, east="宋体",
             align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_indent=True,
             space_before=0, space_after=6, line_spacing=1.5):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line_spacing
    if first_line_indent:
        pf.first_line_indent = Pt(size * 2)
    if text:
        run = p.add_run(text)
        set_run_font(run, size=size, bold=bold, east=east)
    return p


def add_bullet(doc, text, size=10.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.left_indent = Pt(21)
    pf.first_line_indent = Pt(-10.5)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.4
    run = p.add_run("• " + text)
    set_run_font(run, size=size)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    set_run_font(run, size=9, bold=True, east="黑体")
    return p


def shade_cell(cell, fill="D9E2F3"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_cell(cell, text, bold=False, size=9, east="宋体",
             align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(str(text))
    set_run_font(run, size=size, bold=bold, east=east)


def add_table(doc, headers, rows, widths=None, font_size=9,
              first_col_left=False):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        set_cell(hdr[i], text, bold=True, size=font_size, east="黑体")
        shade_cell(hdr[i])

    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            align = (WD_ALIGN_PARAGRAPH.LEFT
                     if (first_col_left and i == 0)
                     else WD_ALIGN_PARAGRAPH.CENTER)
            set_cell(cells[i], text, size=font_size, align=align)

    if widths:
        for r in table.rows:
            for i, w in enumerate(widths):
                r.cells[i].width = Cm(w)

    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)
    set_run_font(run, size=9)


def setup_document():
    doc = Document()

    cp = doc.core_properties
    cp.title = "智能搬运项目与论文工作进度报告"
    cp.subject = "面向智能搬运的树莓派–STM32 分层控制架构设计与性能评估"
    cp.author = "项目组"
    cp.comments = "内部进度记录，数据不作为论文结论"
    cp.created = datetime(2026, 11, 13, 12, 0)
    cp.modified = datetime(2026, 11, 13, 12, 0)

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(3.0)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.space_after = Pt(0)

    for level, (size, east) in enumerate(
            [(16, "黑体"), (14, "黑体"), (12, "黑体")], start=1):
        st = doc.styles[f"Heading {level}"]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        rPr = st.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:eastAsia"), east)
        rFonts.set(qn("w:ascii"), "Times New Roman")
        rFonts.set(qn("w:hAnsi"), "Times New Roman")
        color = rPr.find(qn("w:color"))
        if color is not None:
            for attr in ("w:themeColor", "w:themeShade", "w:themeTint"):
                if color.get(qn(attr)) is not None:
                    del color.attrib[qn(attr)]
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.25

    # 页眉
    header_p = section.header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hr = header_p.add_run("智能搬运项目 · 论文进度报告 v0.1")
    set_run_font(hr, size=9, color=(0x66, 0x66, 0x66))

    # 页脚页码
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number(footer_p)

    return doc


def add_heading(doc, text, level=1):
    h = doc.add_heading(level=level)
    run = h.add_run(text)
    set_run_font(run, size=(16 if level == 1 else 14 if level == 2 else 12),
                 bold=True, east="黑体")
    return h


# ============================================================================
# 正文
# ============================================================================

def build():
    doc = setup_document()

    # ---------- 封面标题 ----------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("智能搬运项目与论文工作进度报告")
    set_run_font(r, size=22, bold=True, east="黑体")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("——面向智能搬运的树莓派–STM32 分层控制架构设计与性能评估")
    set_run_font(r, size=13, bold=False, east="楷体")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run(f"报告日期：{REPORT_DATE}    版本：v0.1")
    set_run_font(r, size=10.5, color=(0x55, 0x55, 0x55))

    add_table(doc, ["项目", "内容"], [
        ["赛事", "2027 年中国大学生工程实践与创新能力大赛"],
        ["赛道", "智能 + 工程创新赛道 · 智能搬运"],
        ["论文题目", "面向智能搬运的树莓派–STM32 分层控制架构设计与性能评估"],
        ["论文目标", "中文普刊（知网收录、非预警），本科一作、导师通讯"],
        ["项目阶段", "硬件基础调试完成；论文工作区与实验框架已建立"],
        ["报告性质", "内部进度记录，数据为现状描述，不作为论文结论"],
    ], widths=[3.2, 11.6], font_size=9.5, first_col_left=True)

    # ---------- 一、项目概况 ----------
    add_heading(doc, "一、项目概况", 1)
    add_para(doc,
             "本项目面向智能搬运赛项，构建一套“树莓派负责视觉与决策、"
             "STM32 负责实时运动控制”的异构分层系统。树莓派 5 通过 USB "
             "摄像头完成颜色目标识别，经串口把目标相对爪心的偏差发送给 "
             "STM32F103ZET6；STM32 驱动麦克纳姆轮底盘、升降机构和夹爪，"
             "并向上位机回传状态。系统同时承担论文的工程验证任务。")
    add_para(doc,
             "论文定位为工程应用型：不追求算法创新，而是给出一种低成本、"
             "可复现的架构，并用实测数据量化通信、视觉、运动三个层面的"
             "性能边界。核心贡献包括分层架构设计、四组量化实验，以及"
             "串口位置模式与脉冲模式的定位精度对比。")

    # ---------- 二、硬件现状 ----------
    add_heading(doc, "二、硬件现状", 1)
    add_table(doc, ["类别", "型号 / 规格", "数量", "状态"], [
        ["主控板", "树莓派 5（2 GB）", "1", "可用"],
        ["显示", "创乐博 7 寸 IPS 屏（1024×600）", "1", "可用"],
        ["摄像头", "200 万像素 USB 工业摄像头", "1", "可用（最高 1280×720）"],
        ["MCU 板", "正点原子 M144Z-M3（STM32F103ZET6，512 KB）", "1", "可用"],
        ["电机", "张大头 Emm42_V5.0 闭环步进", "1", "已上电验证"],
        ["调试器", "ATK-HSWLDBG 高速无线调试器", "1", "可用"],
        ["电池", "12 V 级（实测 11.3 V）", "1", "仅够空载"],
        ["电机电源", "24 V / 3 A 以上", "0", "未采购（硬卡点）"],
        ["机械结构", "底盘 / 升降 / 夹爪", "0", "未开始"],
    ], widths=[2.6, 8.0, 1.6, 3.6], font_size=9)
    add_caption(doc, "表 1  硬件现状")

    # ---------- 三、软件现状 ----------
    add_heading(doc, "三、软件现状", 1)

    add_heading(doc, "3.1 树莓派端", 2)
    add_para(doc,
             "视觉程序 color_tracker.py 已实现六色（红、黄、蓝、绿、黑、"
             "浅蓝）HSV 分割、形态学去噪、轮廓圆度过滤与卡尔曼滤波跟踪，"
             "支持 headless 打印、VNC 显示、录像及串口输出。另有 "
             "hsv_calibrate.py 用于实机标定阈值。")
    add_bullet(doc, "运行环境：亚博 Pi-OS-ROS 镜像，OpenCV 4.8.1")
    add_bullet(doc, "串口：/dev/ttyAMA0，115200 8N1，需在 config.txt 中加 "
                    "dtoverlay=uart0-pi5 与 dtparam=uart0=on")
    add_bullet(doc, "输出：$F/$T 帧，含颜色编号与相对画面中心的像素偏差")

    add_heading(doc, "3.2 STM32 端", 2)
    add_para(doc,
             "工程 03《树莓派与ZET6通信识别物料追踪》已实现五台 Emm42 "
             "电机控制、非阻塞运动层、抓取状态机与树莓派链路。2026-11-11 "
             "以 Keil V5.06 完整编译链接：0 Error / 0 Warning，"
             "Code 11902 B，RO 378 B，RW 128 B，ZI 2496 B。")
    add_table(doc, ["模块", "作用"], [
        ["pi_link.c/.h", "USART3 接收树莓派 ASCII 报文，环形缓冲、CRC 校验、应答"],
        ["motion.c/.h", "非阻塞运动层，四轮按距离分配转速，支持急停"],
        ["emm42.c/.h", "Emm42 串口协议封装，位置模式 / 速度模式 / 同步触发"],
        ["gripper.c/.h", "舵机夹爪，TIM4_CH1 / PB6，50 Hz"],
        ["main.c", "抓取状态机、串口调试台、KEY0 启动"],
    ], widths=[3.4, 11.4], font_size=9, first_col_left=True)
    add_caption(doc, "表 2  STM32 工程模块")

    add_heading(doc, "3.3 通信协议", 2)
    add_para(doc,
             "采用 ASCII 行协议，帧格式为 $body*XX，XX 为 body 所有字节"
             "异或的两位十六进制；波特率 115200，8N1。")
    add_table(doc, ["方向", "帧", "含义"], [
        ["Pi → STM32", "$H,t_ms", "心跳，200 ms 一次"],
        ["Pi → STM32", "$P,t_ms", "探活，STM32 回 $P"],
        ["Pi → STM32", "$S", "请求状态"],
        ["Pi → STM32", "$C,START/STOP/RESET/ZERO", "任务启动 / 急停 / 复位 / 升降清零"],
        ["Pi → STM32", "$F,seq,state,count", "扫描结果帧头，state=1 表示画面稳定"],
        ["Pi → STM32", "$T,seq,color,dx,dy,r,conf,flags", "单目标，dx/dy 单位 0.1 mm"],
        ["STM32 → Pi", "$S,seq,state,err", "状态，变化时立即发并每 500 ms 发一次"],
        ["STM32 → Pi", "$K,seq,ok", "对 $F/$T 的应答"],
        ["STM32 → Pi", "$P,t_ms", "探活应答"],
    ], widths=[2.8, 6.2, 5.8], font_size=8.5, first_col_left=True)
    add_caption(doc, "表 3  树莓派与 STM32 通信帧")

    add_heading(doc, "3.4 当前已知问题：两端协议尚未统一", 2)
    add_para(doc,
             "color_tracker.py 目前仍按 02 工程的约定发送：$F 的第二个"
             "字段是 t_ms，$T 的字段是像素偏差、面积与速度，$C 用于发送"
             "标定参数。而工程 03 要求 $F 的第二个字段是稳定标志（1/0），"
             "$T 携带 0.1 mm 偏差、半径与置信度，$C 用于 START/STOP 等"
             "命令。两者不一致，直接联调会出现结果帧被丢弃、命令误解析。")
    add_table(doc, ["待改项", "现状", "目标"], [
        ["每色单目标", "每种颜色 1 个卡尔曼跟踪器", "同色多目标关联（贪心 / IoU）"],
        ["坐标单位", "像素 du/dv + 标量 mm_per_px", "0.1 mm 的 dx/dy"],
        ["稳定性判断", "无", "连续 N 帧中位数 + 离散度阈值，稳定才发 state=1"],
        ["状态机", "无心跳、不解析 $S", "200 ms $H，仅在 state=4 时发结果"],
        ["任务码", "无", "二维码识别后发 $Q,seq,<任务码>"],
    ], widths=[3.0, 6.2, 5.6], font_size=8.5, first_col_left=True)
    add_caption(doc, "表 4  树莓派端待改造项")

    # ---------- 四、已完成验证 ----------
    add_heading(doc, "四、已完成的验证", 1)
    add_table(doc, ["验证项", "结果", "日期"], [
        ["电机上电", "使能 → 30 RPM 反转 → 停止 → 3200 脉冲一圈 → 正转 → 失能，六步全部通过", "2026-11-06"],
        ["电机回包", "每条命令均收到状态 02（执行成功）", "2026-11-06"],
        ["Pi 排针串口", "/dev/ttyAMA0 可收发，与 STM32 通信链路验证", "2026-11"],
        ["视觉识别", "六色 HSV + 卡尔曼跟踪可在 headless / VNC 下运行", "2026-10"],
        ["工程 03 编译", "0 Error / 0 Warning，Code 11902 B（2026-11-11 20:41）", "2026-11-11"],
        ["整机联调", "尚未开始", "—"],
    ], widths=[3.2, 9.6, 2.4], font_size=9, first_col_left=True)
    add_caption(doc, "表 5  验证记录")
    add_para(doc,
             "需要说明：11.3 V 电池只完成了空载验证，带负载时必须换 24 V / "
             "3 A 以上电源，否则驱动板欠压、电机失步。")

    # ---------- 五、当前问题与风险 ----------
    add_heading(doc, "五、当前问题与风险", 1)
    add_table(doc, ["#", "问题", "影响", "状态 / 对策"], [
        ["1", "缺 24 V / 3 A 电源", "带负载无法验证，比赛无法进行", "硬卡点，尽快采购"],
        ["2", "机械结构未定", "整机实验无法开始，论文缺整机数据", "P2 最高优先级"],
        ["3", "两端协议不一致", "联调丢帧、命令误解析", "按表 4 改造 color_tracker.py"],
        ["4", "现场参数为占位值", "距离、抓取高度不准", "装车后逐项标定"],
        ["5", "无实验数据", "论文实验章节为空", "已建框架，先跑 exp01–03"],
        ["6", "代码按 5 台电机规划但只有 1 台", "多机同步未实测", "采购后补测"],
    ], widths=[0.9, 4.6, 5.2, 4.8], font_size=8.5, first_col_left=True)
    add_caption(doc, "表 6  问题与风险清单")

    # ---------- 六、论文工作计划 ----------
    add_heading(doc, "六、论文工作计划", 1)

    add_heading(doc, "6.1 选题与贡献", 2)
    add_para(doc,
             "题目确定为《面向智能搬运的树莓派–STM32 分层控制架构设计与"
             "性能评估》。三项可写进摘要的贡献为：")
    add_bullet(doc, "分层架构：Pi 负责视觉决策、STM32 负责实时运动，"
                    "轻量 ASCII + 异或 CRC 协议在 115200 下实现毫秒级往返。")
    add_bullet(doc, "量化评估：给出串口往返时延、长时通信可靠性、Pi5 "
                    "视觉帧率与温度、电机定位重复性四组实测数据。")
    add_bullet(doc, "模式对比：同一负载下串口位置模式与脉冲模式的定位"
                    "精度对比，给出控制方式选择依据。")

    add_heading(doc, "6.2 论文结构（约 6000 字）", 2)
    add_table(doc, ["章节", "字数", "主要内容", "图表"], [
        ["摘要 + 关键词", "250", "背景、方法、四组数据、结论", "—"],
        ["1 引言", "800", "竞赛背景、研究现状、本文工作", "表 1"],
        ["2 总体设计", "1200", "需求分析、架构、硬件选型、协议", "图 1、表 2–3"],
        ["3 关键实现", "1500", "视觉、坐标变换、串口链路、运动控制、状态机", "图 2–3"],
        ["4 实验与结果", "2000", "四至五组实验，每组一图一表", "图 4–7、表 4–6"],
        ["5 结论", "300", "指标复述、局限、后续工作", "—"],
        ["参考文献", "—", "12–15 篇", "—"],
    ], widths=[3.2, 1.8, 7.6, 2.6], font_size=9, first_col_left=True)
    add_caption(doc, "表 7  论文结构与字数预算")

    add_heading(doc, "6.3 实验计划", 2)
    add_table(doc, ["编号", "实验", "样本量", "产出", "现在可做"], [
        ["exp01", "串口往返时延", "1000 次", "延迟直方图、P50/P95", "是"],
        ["exp02", "长时通信可靠性", "1 小时 / 约 3.6 万条", "丢包率、坏帧率", "是"],
        ["exp03", "Pi5 视觉性能边界", "3 分辨率 × 3 次", "帧率–温度折线图", "是"],
        ["exp04", "电机定位重复性", "50 次往复", "误差散点、标准差", "需固件扩展"],
        ["exp05", "串口 vs 脉冲模式", "各 50 次", "丢步率对比表", "需固件扩展"],
        ["exp06", "视觉定位精度标定", "30/45/60 cm 各 20 点", "误差曲线", "待标定板"],
    ], widths=[1.6, 4.4, 3.4, 4.2, 2.6], font_size=9, first_col_left=True)
    add_caption(doc, "表 8  实验计划")

    add_heading(doc, "6.4 时间表", 2)
    add_table(doc, ["时间", "任务", "产出"], [
        ["2026-11", "实验框架搭建，跑通 exp01–03", "第一批 CSV"],
        ["2026-12", "固件扩展，完成 exp04–05；补文献综述", "电机数据、文献表"],
        ["2027-01", "视觉实验，整理全部论文数据", "图表初稿"],
        ["2027-02", "完成论文初稿", "v1.0 全文"],
        ["2027-03", "导师修改、查重、投稿", "投稿回执"],
        ["2027-04 至 06", "备赛整机联调", "比赛"],
        ["2027-07 至 09", "按审稿意见修改", "录用 / 见刊"],
    ], widths=[3.2, 8.2, 4.4], font_size=9, first_col_left=True)
    add_caption(doc, "表 9  论文工作时间表")

    # ---------- 七、本次完成 ----------
    add_heading(doc, "七、本次完成的工作（2026-11-13）", 1)
    add_bullet(doc, "建立论文工作区 D:\\树莓派\\论文\\，分 paper、experiments、"
                    "data、figures、records、refs、docs、tools 八个目录。")
    add_bullet(doc, "编写实验公共模块 common.py：协议编解码、带纳秒时间戳的"
                    "串口封装、CSV 与元信息记录、环境快照、分位数统计。")
    add_bullet(doc, "编写 exp01 串口往返时延、exp02 长时通信可靠性、exp03 "
                    "Pi5 视觉性能边界三个可直接运行的实验脚本。")
    add_bullet(doc, "编写 exp04 电机定位重复性设计稿，明确固件扩展接口 "
                    "$C,MOVE 与 $R。")
    add_bullet(doc, "编写论文大纲 v0.1、文献检索清单、实验记录模板与实验台账。")
    add_bullet(doc, "生成本进度报告。")

    # ---------- 八、下一步 ----------
    add_heading(doc, "八、下一步计划（两周内）", 1)
    add_table(doc, ["优先级", "任务", "验收标准"], [
        ["P0", "在树莓派上跑通 exp01（100 次）与 exp02（60 s）", "生成 CSV + summary，无超时异常"],
        ["P0", "跑 exp03 三种分辨率 × 3 次", "得到 FPS、CPU、温度表"],
        ["P0", "采购 24 V / 3 A 电源", "下单并到货"],
        ["P1", "确定机械方案（底盘 / 升降 / 夹爪）", "输出选型与采购清单"],
        ["P1", "给工程 03 加 $C,MOVE 与 $R 命令并重新编译", "0 Error / 0 Warning"],
        ["P1", "统一 color_tracker.py 与工程 03 的协议", "联调不丢帧"],
        ["P2", "建立 git 仓库并打基线 tag", "代码与实验数据版本对应"],
    ], widths=[1.6, 8.2, 6.0], font_size=9, first_col_left=True)
    add_caption(doc, "表 10  两周内任务")

    # ---------- 九、关键参数速查 ----------
    add_heading(doc, "九、关键参数速查", 1)
    add_table(doc, ["项目", "参数"], [
        ["Emm42 供电", "7–32 V，推荐 24 V / 3 A 以上"],
        ["Emm42 通信", "115200 8N1，地址默认 1，校验 0x6B"],
        ["细分 / 脉冲", "默认 16 细分，3200 脉冲 / 圈"],
        ["编码器", "16384 线，控制精度 < 0.08°"],
        ["Pi 串口", "/dev/ttyAMA0，需 dtoverlay=uart0-pi5 + dtparam=uart0=on"],
        ["摄像头", "最高 1280×720，默认请求 640×480"],
        ["对准容差", "2.0 mm，连续两次满足才抓取"],
    ], widths=[3.4, 11.4], font_size=9, first_col_left=True)
    add_caption(doc, "表 11  关键参数")

    # ---------- 十、说明 ----------
    add_heading(doc, "十、说明", 1)
    add_para(doc,
             "本报告用于记录项目与论文工作的当前状态，便于团队和导师同步"
             "进度。文中所有“可用 / 已通过”均指已完成对应验证；未注明"
             "的数据（如帧率、时延、重复精度）尚待实验采集，不得直接引用"
             "到论文中。")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print(f"已生成：{OUT}")


if __name__ == "__main__":
    build()
