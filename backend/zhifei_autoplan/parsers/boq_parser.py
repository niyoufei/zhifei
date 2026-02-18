from __future__ import annotations

import asyncio
import re
from typing import Dict, List, Tuple, Any

import pdfplumber
import json
from pathlib import Path

from backend.zhifei_autoplan.models import BoQItem, ConstructionProcess, Resource


class BoQParser:
    """
    清单智能识别与统计引擎（Module 2）
    - MECE 原则：清单项按“材料/工序/资源”三段映射，互不重复但覆盖所有项目
    """

    async def parse(self, path: str) -> Tuple[List[BoQItem], Dict[str, Any]]:
        if path.lower().endswith((".xlsx", ".xls")):
            rows = await asyncio.to_thread(self._read_excel, path)
        elif path.lower().endswith(".pdf"):
            rows = await asyncio.to_thread(self._read_pdf_tables, path)
        else:
            rows = []

        items = [self._row_to_item(r) for r in rows if r.get("name")]
        stats = self._calc_stats(items)
        return items, stats

    def _read_excel(self, path: str) -> List[Dict[str, Any]]:
        """
        Read BoQ Excel without pandas to avoid heavy C-extension dependencies.
        Supports:
        - .xlsx via openpyxl
        - .xls via xlrd (optional; if not installed, returns empty)
        """
        p = str(path or "")
        if not p:
            return []
        lower = p.lower()
        if lower.endswith(".xls") and not lower.endswith(".xlsx"):
            return self._read_xls_xlrd(p)
        return self._read_xlsx_openpyxl(p)

    def _read_xlsx_openpyxl(self, path: str) -> List[Dict[str, Any]]:
        try:
            from openpyxl import load_workbook
        except Exception:
            return []
        try:
            wb = load_workbook(path, data_only=True, read_only=True)
        except Exception:
            return []
        ws = wb.active

        def _to_str(v: Any) -> str:
            return str(v).strip() if v is not None else ""

        header_row_idx = None
        header_cells: List[str] = []
        for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if r_idx > 30:
                break
            if not row:
                continue
            cells = [_to_str(c) for c in row]
            if not any(cells):
                continue
            # Heuristic: detect a header row by presence of code+name-like columns.
            has_code = any(c in {"清单编码", "编码", "项目编码", "清单号", "清单项目编码", "子目编码"} for c in cells)
            has_name = any(c in {"项目名称", "名称", "清单项目名称", "分部分项工程名称", "子目名称"} for c in cells)
            if has_code and has_name:
                header_row_idx = r_idx
                header_cells = cells
                break

        if header_row_idx is None:
            # Fallback: first non-empty row as header
            for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                if not row:
                    continue
                cells = [_to_str(c) for c in row]
                if any(cells):
                    header_row_idx = r_idx
                    header_cells = cells
                    break

        if header_row_idx is None:
            return []

        header_map: Dict[str, int] = {}
        for idx, name in enumerate(header_cells):
            if name and name not in header_map:
                header_map[name] = idx

        def _pick_col(names: List[str]) -> int | None:
            for n in names:
                if n in header_map:
                    return header_map[n]
            return None

        idx_code = _pick_col(["清单编码", "清单项目编码", "项目编码", "清单号", "子目编码", "编码"])
        idx_name = _pick_col(["项目名称", "清单项目名称", "分部分项工程名称", "子目名称", "名称", "项目"])
        idx_qty = _pick_col(["工程量", "清单工程量", "数量", "计量数量", "合计数量"])
        idx_unit = _pick_col(["单位", "计量单位", "单位名称"])
        idx_unit_price = _pick_col(["综合单价", "单价", "材料单价", "综合价", "unit_price"])
        idx_total_price = _pick_col(["合价", "总价", "金额", "合计", "total_price"])

        def _cell(row: tuple[Any, ...], idx: int | None) -> Any:
            if idx is None:
                return None
            if idx < 0:
                return None
            if idx >= len(row):
                return None
            return row[idx]

        rows: List[Dict[str, Any]] = []
        for row in ws.iter_rows(min_row=header_row_idx + 1, values_only=True):
            if not row:
                continue
            code = _to_str(_cell(row, idx_code))
            name = _to_str(_cell(row, idx_name))
            qty = _cell(row, idx_qty)
            unit = _to_str(_cell(row, idx_unit))
            unit_price = _cell(row, idx_unit_price)
            total_price = _cell(row, idx_total_price)
            # Skip blank rows
            if not any([code, name, qty, unit, unit_price, total_price]):
                continue
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "qty": qty,
                    "unit": unit,
                    "unit_price": unit_price,
                    "total_price": total_price,
                }
            )
        return rows

    def _read_xls_xlrd(self, path: str) -> List[Dict[str, Any]]:
        """
        Optional .xls support (requires xlrd). If unavailable, returns empty.
        """
        try:
            import xlrd  # type: ignore
        except Exception:
            return []
        try:
            book = xlrd.open_workbook(path)
            sheet = book.sheet_by_index(0)
        except Exception:
            return []

        def _to_str(v: Any) -> str:
            return str(v).strip() if v is not None else ""

        header_row_idx = None
        header_cells: List[str] = []
        for r in range(min(30, sheet.nrows)):
            cells = [_to_str(sheet.cell_value(r, c)) for c in range(sheet.ncols)]
            if not any(cells):
                continue
            has_code = any(c in {"清单编码", "编码", "项目编码", "清单号", "清单项目编码", "子目编码"} for c in cells)
            has_name = any(c in {"项目名称", "名称", "清单项目名称", "分部分项工程名称", "子目名称"} for c in cells)
            if has_code and has_name:
                header_row_idx = r
                header_cells = cells
                break

        if header_row_idx is None:
            for r in range(sheet.nrows):
                cells = [_to_str(sheet.cell_value(r, c)) for c in range(sheet.ncols)]
                if any(cells):
                    header_row_idx = r
                    header_cells = cells
                    break
        if header_row_idx is None:
            return []

        header_map: Dict[str, int] = {}
        for idx, name in enumerate(header_cells):
            if name and name not in header_map:
                header_map[name] = idx

        def _pick_col(names: List[str]) -> int | None:
            for n in names:
                if n in header_map:
                    return header_map[n]
            return None

        idx_code = _pick_col(["清单编码", "清单项目编码", "项目编码", "清单号", "子目编码", "编码"])
        idx_name = _pick_col(["项目名称", "清单项目名称", "分部分项工程名称", "子目名称", "名称", "项目"])
        idx_qty = _pick_col(["工程量", "清单工程量", "数量", "计量数量", "合计数量"])
        idx_unit = _pick_col(["单位", "计量单位", "单位名称"])
        idx_unit_price = _pick_col(["综合单价", "单价", "材料单价", "综合价", "unit_price"])
        idx_total_price = _pick_col(["合价", "总价", "金额", "合计", "total_price"])

        def _cell(r: int, idx: int | None) -> Any:
            if idx is None:
                return None
            if idx < 0 or idx >= sheet.ncols:
                return None
            return sheet.cell_value(r, idx)

        rows: List[Dict[str, Any]] = []
        for r in range(header_row_idx + 1, sheet.nrows):
            code = _to_str(_cell(r, idx_code))
            name = _to_str(_cell(r, idx_name))
            qty = _cell(r, idx_qty)
            unit = _to_str(_cell(r, idx_unit))
            unit_price = _cell(r, idx_unit_price)
            total_price = _cell(r, idx_total_price)
            if not any([code, name, qty, unit, unit_price, total_price]):
                continue
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "qty": qty,
                    "unit": unit,
                    "unit_price": unit_price,
                    "total_price": total_price,
                }
            )
        return rows

    def _read_pdf_tables(self, path: str) -> List[Dict[str, Any]]:
        rows = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for t in tables:
                    for row in t[1:]:
                        if not row or len(row) < 4:
                            continue
                        rows.append(
                            {
                                "code": (row[0] or "").strip(),
                                "name": (row[1] or "").strip(),
                                "qty": row[2],
                                "unit": (row[3] or "").strip(),
                                "unit_price": row[4] if len(row) > 4 else None,
                                "total_price": row[5] if len(row) > 5 else None,
                            }
                        )
        return rows

    def _row_to_item(self, r: Dict[str, Any]) -> BoQItem:
        qty = self._to_float(r.get("qty"))
        unit_price = self._to_float(r.get("unit_price"))
        total_price = self._to_float(r.get("total_price"))
        if total_price is None and qty is not None and unit_price is not None:
            total_price = qty * unit_price
        item = BoQItem(
            boq_code=r.get("code") or "",
            name=r.get("name") or "",
            quantity=qty,
            unit=r.get("unit") or None,
            unit_price=unit_price,
            total_price=total_price,
        )
        process, resources = self.map_boq_to_process(item)
        item.process = process
        item.resources = resources
        return item

    def map_boq_to_process(self, boq_item: BoQItem) -> Tuple[ConstructionProcess, List[Resource]]:
        # 三维映射逻辑：清单 -> 工序 -> 资源
        name = boq_item.name
        mapping = self._load_process_rules() or [
            (["混凝土"], "混凝土浇筑", ["搅拌车", "泵车"]),
            (["钢筋"], "钢筋绑扎", ["钢筋工", "电焊机"]),
            (["模板"], "模板安装", ["模板工", "支撑材料"]),
            (["回填"], "土方回填", ["压路机", "装载机"]),
            (["管道"], "管道安装", ["挖机", "起重机"]),
            # Extra common rules (kept after the core five to preserve first-match behavior).
            (["防水", "卷材"], "防水施工", ["防水工", "热风焊机"]),
            (["砌体", "砌筑", "加气块", "砖"], "砌体砌筑", ["砌筑工", "砂浆搅拌机"]),
            (["抹灰", "粉刷"], "抹灰工程", ["抹灰工", "砂浆搅拌机"]),
            (["保温"], "保温施工", ["保温工", "切割机"]),
            (["电缆", "桥架"], "电气安装", ["电工", "电缆牵引机"]),
            (["消防"], "消防安装", ["管道工", "电工"]),
            (["通风", "空调", "暖通"], "暖通安装", ["管道工", "焊工"]),
            (["门窗"], "门窗安装", ["安装工", "电钻"]),
            (["幕墙"], "幕墙安装", ["安装工", "吊篮"]),
            (["沥青"], "沥青路面施工", ["摊铺机", "压路机"]),
            (["路基"], "路基施工", ["推土机", "压路机"]),
        ]

        proc = ConstructionProcess(name="通用施工工序", standard=None, risks=[])
        res: List[Resource] = []
        for kws, proc_name, res_names in mapping:
            if any(str(kw) in (name or "") for kw in (kws or [])):
                proc = ConstructionProcess(name=str(proc_name), standard=None, risks=[])
                res = [Resource(name=str(r)) for r in (res_names or [])]
                break
        return proc, res

    _PROCESS_RULES_CACHE: List[Tuple[List[str], str, List[str]]] | None = None
    _PROCESS_RULES_MTIME_NS: int | None = None

    def _load_process_rules(self) -> List[Tuple[List[str], str, List[str]]] | None:
        """
        Optional user-configurable mapping rules.
        File: backend/data/autoplan/boq_process_rules.json
        Format:
          {
            "rules": [
              {"match": ["混凝土", "现浇"], "process": "混凝土浇筑", "resources": ["搅拌车", "泵车"]},
              ...
            ]
          }
        """
        cfg = Path("backend/data/autoplan/boq_process_rules.json")
        if not cfg.exists() or not cfg.is_file():
            return None
        try:
            mtime = int(cfg.stat().st_mtime_ns)
        except Exception:
            mtime = None
        if self._PROCESS_RULES_CACHE is not None and mtime is not None and self._PROCESS_RULES_MTIME_NS == mtime:
            return self._PROCESS_RULES_CACHE

        try:
            obj = json.loads(cfg.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(obj, dict):
            return None
        rules = obj.get("rules")
        if not isinstance(rules, list) or not rules:
            return None

        parsed: List[Tuple[List[str], str, List[str]]] = []
        for r in rules:
            if not isinstance(r, dict):
                continue
            raw_match = r.get("match") or r.get("keywords") or r.get("kw") or []
            if isinstance(raw_match, str):
                raw_match = [raw_match]
            if not isinstance(raw_match, list):
                continue
            kws = [str(x).strip() for x in raw_match if str(x).strip()]
            proc = str(r.get("process") or r.get("process_name") or "").strip()
            raw_res = r.get("resources") or r.get("res") or []
            if isinstance(raw_res, str):
                raw_res = [raw_res]
            res = [str(x).strip() for x in (raw_res or []) if str(x).strip()] if isinstance(raw_res, list) else []
            if kws and proc:
                parsed.append((kws, proc, res))
        if not parsed:
            return None
        self._PROCESS_RULES_CACHE = parsed
        self._PROCESS_RULES_MTIME_NS = mtime
        return parsed

    def _calc_stats(self, items: List[BoQItem]) -> Dict[str, Any]:
        # 统计分析：数量级与密度（简化版）
        total_qty = 0.0
        count = 0.0
        for it in items:
            if it.quantity is not None:
                total_qty += it.quantity
                count += 1.0
        density = total_qty / count if count else 0.0
        top_quantity = sorted(
            [it for it in items if it.quantity is not None],
            key=lambda x: float(x.quantity or 0),
            reverse=True,
        )[:8]
        top_unit_price = sorted(
            [it for it in items if it.unit_price is not None],
            key=lambda x: float(x.unit_price or 0),
            reverse=True,
        )[:8]
        top_total_price = sorted(
            [it for it in items if it.total_price is not None],
            key=lambda x: float(x.total_price or 0),
            reverse=True,
        )[:8]
        material_keywords = (
            "钢筋",
            "混凝土",
            "水泥",
            "砂",
            "石",
            "沥青",
            "管",
            "电缆",
            "模板",
            "防水",
            "保温",
        )
        top_material_demand = sorted(
            [it for it in items if any(k in (it.name or "") for k in material_keywords)],
            key=lambda x: float(x.quantity or 0),
            reverse=True,
        )[:8]

        def _brief(it: BoQItem) -> Dict[str, Any]:
            return {
                "boq_code": it.boq_code,
                "name": it.name,
                "quantity": it.quantity,
                "unit": it.unit,
                "unit_price": it.unit_price,
                "total_price": it.total_price,
            }

        hazard_keywords = ("危化", "易燃", "易爆", "有毒", "溶剂", "油漆", "涂料", "沥青", "气瓶")
        special_keywords = ("高性能", "特种", "抗渗", "防腐", "不锈钢", "高强", "预应力", "四新")
        ppe_keywords = ("安全帽", "安全带", "防护服", "防毒面具", "护目镜", "绝缘手套", "劳保")

        hazard_items = [it for it in items if any(k in (it.name or "") for k in hazard_keywords)][:12]
        special_items = [it for it in items if any(k in (it.name or "") for k in special_keywords)][:12]
        ppe_items = [it for it in items if any(k in (it.name or "") for k in ppe_keywords)][:12]

        return {
            "total_quantity": total_qty,
            "item_count": count,
            "density": density,
            "top_quantity_items": [_brief(it) for it in top_quantity],
            "top_unit_price_items": [_brief(it) for it in top_unit_price],
            "top_total_price_items": [_brief(it) for it in top_total_price],
            "top_material_demand_items": [_brief(it) for it in top_material_demand],
            "special_material_items": [_brief(it) for it in special_items],
            "hazardous_material_items": [_brief(it) for it in hazard_items],
            "ppe_items": [_brief(it) for it in ppe_items],
        }

    def _to_float(self, v) -> float | None:
        if v is None:
            return None
        s = str(v)
        s = re.sub(r"[^\d.]+", "", s)
        try:
            return float(s)
        except Exception:
            return None
