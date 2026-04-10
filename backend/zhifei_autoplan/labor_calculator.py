from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.zhifei_autoplan.terminology_guard import load_labor_allocation_matrix


def _parse_ratio(v: Any) -> float:
    if isinstance(v, (int, float)):
        n = float(v)
        return n if n <= 1.0 else n / 100.0
    s = str(v or "").strip().replace("%", "")
    if not s:
        return 0.0
    try:
        n = float(s)
        return n if n <= 1.0 else n / 100.0
    except Exception:
        return 0.0


def _normalize_project_type(project_type: str, matrix: Dict[str, Any]) -> str:
    t = str(project_type or "").strip()
    if t in matrix:
        return t
    if any(k in t for k in ("房建", "建筑", "房屋")) and "房屋建筑工程" in matrix:
        return "房屋建筑工程"
    if "市政" in t and "市政基础设施工程" in matrix:
        return "市政基础设施工程"
    return str(next(iter(matrix.keys()), ""))


def _normalize_size(size: str) -> str:
    s = str(size or "").strip()
    if "大型" in s:
        return "大型项目"
    if "中型" in s:
        return "中型项目"
    if "小型" in s:
        return "小型项目"
    return "中型项目"


def _normalize_stage(stage: str) -> str:
    s = str(stage or "").strip()
    if any(k in s for k in ("前期", "基础", "地基", "准备")):
        return "前期"
    if any(k in s for k in ("后期", "收尾", "装修", "装饰", "竣工")):
        return "后期"
    return "中期"


def _pick_trade_stage_map(project_matrix: Dict[str, Any], project_key: str) -> Tuple[str, Dict[str, Any]]:
    root = project_matrix.get("关键工种配置比例")
    if not isinstance(root, dict) or not root:
        return "", {}
    # 常见结构：root[项目类型 or 专业领域] -> {阶段: {工种: {...}}}
    if isinstance(root.get(project_key), dict):
        return project_key, root.get(project_key) or {}
    domain = str(next(iter(root.keys()), ""))
    domain_map = root.get(domain)
    if isinstance(domain_map, dict):
        return domain, domain_map
    return "", {}


def _pick_stage_row(stage_map: Dict[str, Any], stage_bucket: str) -> Tuple[str, Dict[str, Any]]:
    if not isinstance(stage_map, dict) or not stage_map:
        return "", {}
    if isinstance(stage_map.get(stage_bucket), dict):
        return stage_bucket, stage_map.get(stage_bucket) or {}
    candidates = {
        "前期": ("地基与基础", "前期"),
        "中期": ("主体结构", "中期"),
        "后期": ("建筑装饰装修", "后期"),
    }.get(stage_bucket, ("中期",))
    for c in candidates:
        if isinstance(stage_map.get(c), dict):
            return c, stage_map.get(c) or {}
    first = str(next(iter(stage_map.keys()), ""))
    row = stage_map.get(first)
    return first, row if isinstance(row, dict) else {}


def _trade_ratio_cell_to_main_ratio(cell: Any) -> Tuple[float, float, float]:
    if not isinstance(cell, dict):
        v = _parse_ratio(cell)
        return v, v, 0.0
    mid = _parse_ratio(cell.get("中级工及以上等级技能工人占比"))
    senior = _parse_ratio(cell.get("高级工及以上等级技能工人占比"))
    if mid <= 0.0:
        for _, value in cell.items():
            num = _parse_ratio(value)
            if num > 0:
                mid = num
                break
    main = max(mid, senior)
    return main, mid, senior


def get_labor_ui_options(rules_path: str | None = None) -> Dict[str, List[str]]:
    matrix = load_labor_allocation_matrix(rules_path)
    project_types = [str(k) for k in matrix.keys() if "标准" not in str(k)]
    sizes = ["小型项目", "中型项目", "大型项目"]
    stages = ["前期", "中期", "后期"]
    return {"project_types": project_types or ["房屋建筑工程"], "sizes": sizes, "stages": stages}


def generate_labor_plan(
    *,
    project_type: str,
    size: str,
    stage: str,
    total_personnel: int,
    rules_path: str | None = None,
) -> Dict[str, Any]:
    matrix = load_labor_allocation_matrix(rules_path)
    if not matrix:
        return {"ok": False, "error": "劳动力排班算法矩阵未加载"}

    project_key = _normalize_project_type(project_type, matrix)
    size_key = _normalize_size(size)
    stage_bucket = _normalize_stage(stage)
    total = max(1, int(total_personnel or 1))

    project_matrix = matrix.get(project_key)
    if not isinstance(project_matrix, dict):
        return {"ok": False, "error": f"项目类型未命中: {project_type}"}

    # 技能等级比例
    skill_ratio_row: Dict[str, Any] = {}
    skill_root = project_matrix.get("各等级技能工人配备比例")
    if isinstance(skill_root, dict):
        size_map = skill_root.get(size_key)
        if not isinstance(size_map, dict):
            size_map = skill_root.get("中型项目") if isinstance(skill_root.get("中型项目"), dict) else {}
            size_key = "中型项目"
        if isinstance(size_map, dict):
            skill_ratio_row = size_map.get(stage_bucket) if isinstance(size_map.get(stage_bucket), dict) else {}

    # 工种配置比例
    trade_domain, stage_map = _pick_trade_stage_map(project_matrix, project_key)
    stage_label, trade_ratio_row = _pick_stage_row(stage_map, stage_bucket)
    if not trade_ratio_row:
        return {"ok": False, "error": "未命中工种配置比例"}

    plan_rows: List[Dict[str, Any]] = []
    for trade, cell in trade_ratio_row.items():
        trade_name = str(trade or "").strip()
        if not trade_name:
            continue
        main_ratio, mid_ratio, senior_ratio = _trade_ratio_cell_to_main_ratio(cell)
        count = int(round(total * main_ratio))
        if main_ratio > 0 and count == 0:
            count = 1
        plan_rows.append(
            {
                "工种标准称谓": trade_name,
                "建议占比": f"{main_ratio * 100:.1f}%",
                "建议人数": count,
                "中级工及以上占比": f"{mid_ratio * 100:.1f}%",
                "高级工及以上占比": f"{senior_ratio * 100:.1f}%",
            }
        )

    plan_rows.sort(key=lambda x: int(x.get("建议人数") or 0), reverse=True)
    total_suggested = int(sum(int(x.get("建议人数") or 0) for x in plan_rows))

    skill_rows: List[Dict[str, Any]] = []
    if isinstance(skill_ratio_row, dict):
        for k, v in skill_ratio_row.items():
            ratio = _parse_ratio(v)
            skill_rows.append(
                {
                    "技能等级": str(k),
                    "占比": f"{ratio * 100:.1f}%",
                    "建议人数": int(round(total * ratio)),
                }
            )

    return {
        "ok": True,
        "project_type": project_key,
        "size": size_key,
        "stage_bucket": stage_bucket,
        "stage_label": stage_label or stage_bucket,
        "trade_domain": trade_domain or project_key,
        "total_personnel": total,
        "total_suggested": total_suggested,
        "trade_rows": plan_rows,
        "skill_rows": skill_rows,
    }

