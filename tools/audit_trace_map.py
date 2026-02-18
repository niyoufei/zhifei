#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_trace_map.py
Read build/export_audit_chain.json and render:
- build/audit_trace_map.xlsx
- build/audit_trace_map.pdf
Fields: timestamp, source, output, paper, orientation, margins, heading_rules
"""
import os, json
from datetime import datetime
import pandas as pd

CHAIN_PATH = "build/export_audit_chain.json"
XLSX_PATH  = "build/audit_trace_map.xlsx"
PDF_PATH   = "build/audit_trace_map.pdf"

def load_chain():
    if not os.path.exists(CHAIN_PATH):
        return []
    with open(CHAIN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    return data.get("chain", [])

def flatten(entry):
    audit = (entry.get("audit_trace") or {}).get("decisions", {})
    margins = audit.get("margins_mm") or {}
    return {
        "时间戳": entry.get("timestamp"),
        "输入DOCX": entry.get("source"),
        "输出DOCX(优化后)": entry.get("output"),
        "纸张": audit.get("paper"),
        "方向策略": audit.get("orientation"),
        "页边距(mm)": f"top:{margins.get('top')} right:{margins.get('right')} bottom:{margins.get('bottom')} left:{margins.get('left')}",
        "标题规则": audit.get("heading_rules"),
    }

def write_xlsx(rows):
    df = pd.DataFrame(rows)
    if not len(df):
        # 写一个空模板，便于后续核查
        df = pd.DataFrame([{
            "时间戳":"", "输入DOCX":"", "输出DOCX(优化后)":"",
            "纸张":"", "方向策略":"", "页边距(mm)":"", "标题规则":""
        }])
    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="AuditTrace")
    print(f"📊 Excel -> {XLSX_PATH}")

def write_pdf(rows):
    # 简洁表格渲染
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit

    page = landscape(A4)
    c = canvas.Canvas(PDF_PATH, pagesize=page)
    width, height = page
    x0, y = 15*mm, height - 15*mm

    title = "Audit Trace Map（导出审计追溯图）"
    c.setFont("Helvetica-Bold", 16); c.drawString(x0, y, title); y -= 10*mm
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"); y -= 8*mm

    headers = ["时间戳","纸张","方向策略","页边距(mm)","输入DOCX","输出DOCX(优化后)","标题规则"]
    col_w = [35*mm, 12*mm, 40*mm, 45*mm, 80*mm, 90*mm, 80*mm]
    c.setFont("Helvetica-Bold", 9)
    x = x0
    for i,h in enumerate(headers):
        c.drawString(x, y, h); x += col_w[i]
    y -= 6*mm
    c.line(x0, y+3*mm, x0+sum(col_w), y+3*mm)

    c.setFont("Helvetica", 8)
    for r in rows if rows else []:
        cells = [
            r["时间戳"], r["纸张"], r["方向策略"], r["页边距(mm)"],
            r["输入DOCX"], r["输出DOCX(优化后)"], r["标题规则"]
        ]
        # 行高自适应（简化版）
        lines_per_col = []
        for i, text in enumerate(cells):
            text = str(text or "")
            wrapped = simpleSplit(text, "Helvetica", 8, col_w[i]-2*mm)
            lines_per_col.append(len(wrapped))
        row_h = max(lines_per_col)*4.2*mm
        if y - row_h < 15*mm:
            c.showPage()
            c.setFont("Helvetica", 8)
            y = height - 20*mm
        x = x0
        for i, text in enumerate(cells):
            text = str(text or "")
            wrapped = simpleSplit(text, "Helvetica", 8, col_w[i]-2*mm)
            yy = y
            for line in wrapped:
                c.drawString(x, yy, line)
                yy -= 4.2*mm
            x += col_w[i]
        y -= row_h
    c.save()
    print(f"🗺️  PDF  -> {PDF_PATH}")

def main():
    chain = load_chain()
    rows = [flatten(e) for e in chain]
    write_xlsx(rows)
    write_pdf(rows)
    print("✅ Audit Trace Map generated.")

if __name__ == "__main__":
    main()
