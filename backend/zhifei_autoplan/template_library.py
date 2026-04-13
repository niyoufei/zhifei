from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.evidence import search_ingested_docs
from backend.zhifei_autoplan.project_types import normalize_project_type, ordered_project_types

TEMPLATE_LIBRARY_SCOPE = "template_library"
TEMPLATE_LIBRARY_TAG = "template_library"
TEMPLATE_BENCHMARK_TAG = "benchmark_case"
DEFAULT_AUDIT_PATH = Path("backend/data/audit/ingest.jsonl")
TEMPLATE_LEARNING_CACHE_DIR = Path("backend/data/autoplan/cache/template_learning")
TEMPLATE_PAGE_BUCKETS = ["50_pages", "le_200_pages", "gt_200_pages"]
TEMPLATE_PAGE_BUCKET_LABELS = {
    "50_pages": "50页施组",
    "le_200_pages": "小于等于200页施组",
    "gt_200_pages": "大于200页施组",
}
_TEXT_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_PROJECT_CODE_RE = re.compile(r"[A-Za-z0-9]{8,}")
_TOC_HEADING_RE = re.compile(r"(?:[\.．·…]{4,}\s*-?\d{1,4}\s*|-+\s*\d{1,4}\s*-+\s*)$")
_GENERIC_TEMPLATE_QUERY_TOKENS = {
    "施工组织设计",
    "施工组织",
    "施组",
    "样板",
    "案例",
    "优秀案例",
    "优秀样板",
    "高分样板",
    "维修改造",
    "房建",
    "装修",
    "市政道路",
    "市政排水",
    "工程",
    "项目",
}
_NON_CHAPTER_FIELD_PREFIXES = (
    "项目名称",
    "项目编号",
    "项目类别",
    "项目类型",
    "招标人",
    "建设地点",
    "计划工期",
    "建设规模",
    "招标内容",
    "质量标准",
    "合同估算价",
    "计划开工日期",
    "计划竣工日期",
    "序号",
    "名称",
    "具体内容",
)
_CHAPTER_HEADING_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百0-9]+章\s*.+$"),
    re.compile(r"^(?!\d{1,2}\.\d)\d{1,2}\s*[\.、\)）]\s*\S.+$"),
    re.compile(r"^[一二三四五六七八九十]{1,3}\s*[\.、\)）]\s*\S.+$"),
]
_CHAPTER_THEME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("编制说明", ("编制说明", "编制依据", "编制原则", "编制范围", "说明与依据")),
    ("工程概况", ("工程概况", "项目概况", "工程简介", "工程特征", "项目特征", "建设概况")),
    ("施工部署", ("施工部署", "总体部署", "部署安排", "施工组织总体", "施工部署及资源安排")),
    ("组织机构与资源", ("组织机构", "劳动力", "资源配置", "机械设备", "材料计划", "人员计划", "班组配置")),
    ("施工进度", ("进度计划", "工期", "关键线路", "节点计划", "网络计划", "进度安排")),
    ("施工总平面", ("施工总平面", "平面布置", "现场布置", "临建", "临时设施")),
    ("主要施工方法", ("主要施工方法", "施工方案", "施工工艺", "技术措施", "关键工序", "重难点", "专项方案")),
    ("质量管理", ("质量管理", "质量保证", "质量控制", "质量目标", "检验", "验收", "实测实量")),
    ("安全文明施工", ("安全文明施工", "安全管理", "安全生产", "文明施工", "消防保卫", "临时用电", "职业健康")),
    ("绿色环保", ("环境保护", "环保", "绿色施工", "扬尘", "噪声", "污水", "固废", "节能")),
    ("应急管理", ("应急", "应急预案", "事故处置", "抢险", "防汛", "消防应急")),
    ("信息化与资料", ("信息化", "BIM", "资料管理", "档案", "台账", "智慧工地")),
    ("成品保护与交付", ("成品保护", "交付", "移交", "保修", "竣工移交")),
]
_LEARNING_ANCHOR_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("适用范围与编制依据", ("编制依据", "适用范围", "编制范围", "引用标准")),
    ("组织分工与岗位责任", ("组织机构", "岗位职责", "责任岗位", "责任人", "职责分工")),
    ("流程步骤与工序衔接", ("施工流程", "工艺流程", "施工顺序", "工序", "步骤", "衔接")),
    ("资源配置与机械材料", ("劳动力", "资源配置", "机械设备", "材料计划", "设备投入")),
    ("控制指标与验收标准", ("验收标准", "质量标准", "允许偏差", "控制指标", "抽检", "检测频次")),
    ("进度计划与节点纠偏", ("进度计划", "节点", "关键线路", "纠偏", "工期")),
    ("风险控制与应急处置", ("风险", "应急", "预案", "处置", "响应流程")),
    ("环保文明与现场管理", ("文明施工", "环境保护", "扬尘", "噪声", "围挡", "保洁")),
    ("资料归档与交付闭环", ("资料", "台账", "记录表", "归档", "交付", "移交")),
]
_NOTE_PRIORITY_RULES: list[tuple[float, tuple[str, ...]]] = [
    (3.6, ("评分高", "高分", "高评分", "得分高", "优质", "优秀", "精品", "标杆", "推荐")),
    (2.4, ("目录完整", "章节完整", "结构清晰", "逻辑清晰", "体系完整", "覆盖全面")),
    (1.8, ("表达干净", "语言规范", "文字成熟", "可复用", "通用性强", "文风稳", "表述成熟")),
    (1.4, ("量化充分", "数据充分", "措施具体", "针对性强", "重难点清晰", "细节完整")),
]
_SCENE_RULES_COMMON: list[tuple[str, tuple[str, ...]]] = [
    ("医院", ("医院", "门诊", "病房", "医技", "康复", "急诊", "医疗中心")),
    ("学校", ("学校", "幼儿园", "中学", "小学", "校园", "教学楼", "体育馆")),
    ("住宅", ("住宅", "小区", "安置房", "公寓", "住宅楼")),
    ("办公", ("办公", "办公楼", "行政楼", "研发楼")),
    ("厂房", ("厂房", "车间", "生产线", "仓储", "仓库", "工业园")),
    ("地下室", ("地下室", "地库", "地下车库", "基坑", "地下工程")),
    ("装配式", ("装配式", "pc构件", "预制构件", "叠合板")),
    ("钢结构", ("钢结构", "钢桁架", "钢梁", "钢柱")),
    ("幕墙", ("幕墙", "玻璃幕墙", "石材幕墙", "铝板幕墙")),
    ("老旧小区", ("老旧小区", "旧改", "老旧社区", "棚改")),
    ("加固", ("加固", "结构加固", "抗震加固", "补强")),
    ("局部改造", ("局部改造", "局部维修", "局部翻修", "局部更新")),
    ("改扩建", ("改扩建", "扩建", "扩容", "扩建工程")),
    ("交通导改", ("交通导改", "导改", "保通", "交通疏解")),
    ("桥梁", ("桥梁", "桥", "桥面", "箱梁", "现浇梁")),
    ("管网", ("管网", "污水管", "雨水管", "综合管网", "给排水管线")),
    ("泵站", ("泵站", "泵房", "提升泵站")),
    ("景观", ("景观", "绿化", "园林", "铺装", "公园")),
    ("河道", ("河道", "河涌", "清淤", "驳岸", "水系")),
]
_SCENE_RULES_BY_PROJECT_TYPE: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "维修改造": [
        ("医院", ("医院", "门诊", "病房", "康复", "骨科", "医疗")),
        ("学校", ("学校", "校园", "幼儿园", "教学楼")),
        ("既有建筑", ("既有建筑", "既有", "原建筑", "存量建筑")),
        ("机电更新", ("机电更新", "设备更换", "更新改造", "管线改造")),
        ("养老机构", ("养老机构", "养老院", "敬老院", "养护院", "护理院", "福利院", "特困供养")),
        ("适老化", ("适老化", "适老", "适老改造", "适老装修", "扶手", "防滑", "无障碍")),
        ("失能照护", ("失能", "照护", "集中照护", "护理区", "护理室", "失能老人", "特困人员")),
        ("电梯增设", ("电梯增设", "新增电梯", "外挂电梯", "无障碍电梯", "电梯井道")),
        ("护理呼叫", ("护理呼叫", "呼叫系统", "护理呼叫系统", "智慧养老", "养老呼叫", "紧急呼叫")),
    ],
    "房建": [
        ("住宅", ("住宅", "住宅楼", "小区", "安置房")),
        ("医院", ("医院", "医疗中心", "门诊楼")),
        ("学校", ("学校", "校园", "教学楼", "体育馆")),
        ("装配式", ("装配式", "预制构件", "pc构件")),
    ],
    "市政道路": [
        ("交通导改", ("交通导改", "保通", "交通疏解")),
        ("道路翻修", ("翻修", "白改黑", "罩面", "病害处治")),
        ("桥梁", ("桥梁", "桥面", "箱梁")),
    ],
    "市政排水": [
        ("管网", ("管网", "雨污", "污水管", "雨水管", "顶管")),
        ("泵站", ("泵站", "泵房", "提升泵站")),
    ],
}
for _cache_subdir in ("digest", "chapter_context"):
    (TEMPLATE_LEARNING_CACHE_DIR / _cache_subdir).mkdir(parents=True, exist_ok=True)


def _resolve_audit_path(audit_path: str | Path | None = None) -> Path:
    if audit_path is None:
        return DEFAULT_AUDIT_PATH
    return Path(audit_path)


def infer_template_page_bucket(page_count: Any) -> str | None:
    try:
        pages = int(float(page_count))
    except Exception:
        return None
    if pages <= 0:
        return None
    if pages <= 50:
        return "50_pages"
    if pages <= 200:
        return "le_200_pages"
    return "gt_200_pages"


def normalize_template_page_bucket(raw: Any, *, page_count: Any | None = None) -> str | None:
    key = str(raw or "").strip().lower()
    aliases = {
        "50_pages": "50_pages",
        "50页施组": "50_pages",
        "50页": "50_pages",
        "<=200_pages": "le_200_pages",
        "le_200_pages": "le_200_pages",
        "<=200页施组": "le_200_pages",
        "小于等于200页施组": "le_200_pages",
        "200页内施组": "le_200_pages",
        ">200_pages": "gt_200_pages",
        "gt_200_pages": "gt_200_pages",
        ">200页施组": "gt_200_pages",
        "大于200页施组": "gt_200_pages",
        "200页以上施组": "gt_200_pages",
    }
    if key in aliases:
        return aliases[key]
    return infer_template_page_bucket(page_count)


def template_page_bucket_label(bucket: Any) -> str:
    normalized = normalize_template_page_bucket(bucket)
    if not normalized:
        return ""
    return TEMPLATE_PAGE_BUCKET_LABELS.get(normalized, normalized)


def _compact_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_compact_text(v) for v in value if _compact_text(v).strip())
    if isinstance(value, dict):
        return "\n".join(_compact_text(v) for v in value.values() if _compact_text(v).strip())
    return str(value or "")


def normalize_template_scene_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = re.split(r"[，,、;；/\s]+", str(raw or "").strip())
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def infer_template_scene_tags(*parts: Any, project_type: str | None = None, max_tags: int = 6) -> list[str]:
    text = _compact_text(parts)
    if not text.strip():
        return []
    normalized_type = normalize_project_type(project_type)
    rules = list(_SCENE_RULES_COMMON)
    if normalized_type and normalized_type in _SCENE_RULES_BY_PROJECT_TYPE:
        rules = list(_SCENE_RULES_BY_PROJECT_TYPE[normalized_type]) + rules
    out: list[str] = []
    seen: set[str] = set()
    for tag, keywords in rules:
        if tag in seen:
            continue
        if any(kw and kw in text for kw in keywords):
            seen.add(tag)
            out.append(tag)
        if len(out) >= max(1, int(max_tags or 6)):
            break
    return out


def _scene_overlap_score(query_scene_tags: list[str], record_scene_tags: list[str]) -> float:
    if not query_scene_tags or not record_scene_tags:
        return 0.0
    overlap = [tag for tag in query_scene_tags if tag in set(record_scene_tags)]
    if not overlap:
        return 0.0
    return min(6.0, 2.2 * len(overlap))


def _template_learning_cache_key(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def _load_template_learning_disk_cache(namespace: str, payload: dict[str, Any], *, max_age_sec: int = 7 * 24 * 3600) -> dict[str, Any] | None:
    cache_file = TEMPLATE_LEARNING_CACHE_DIR / str(namespace) / f"{_template_learning_cache_key(payload)}.json"
    if not cache_file.exists():
        return None
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(cached, dict):
        return None
    try:
        cached_at = float(cached.get("_cached_at") or 0.0)
    except Exception:
        cached_at = 0.0
    if cached_at and (time.time() - cached_at) > max(60, int(max_age_sec or 0)):
        return None
    value = cached.get("value")
    return value if isinstance(value, dict) else None


def _save_template_learning_disk_cache(namespace: str, payload: dict[str, Any], value: dict[str, Any]) -> None:
    cache_dir = TEMPLATE_LEARNING_CACHE_DIR / str(namespace)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{_template_learning_cache_key(payload)}.json"
    try:
        cache_file.write_text(
            json.dumps({"_cached_at": time.time(), "value": value}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _template_profile_count(rec: dict[str, Any] | None) -> int:
    if not isinstance(rec, dict):
        return 0
    raw = rec.get("template_chapter_profile_count")
    try:
        count = int(raw or 0)
    except Exception:
        count = 0
    if count > 0:
        return count
    stored = rec.get("template_chapter_profiles") if isinstance(rec.get("template_chapter_profiles"), list) else []
    if stored:
        return len(stored)
    return len(_template_sections_from_record(rec))


def _template_note_priority_score(note: Any) -> float:
    text = str(note or "").strip()
    if not text:
        return 0.0
    score = 0.0
    for weight, keywords in _NOTE_PRIORITY_RULES:
        if any(kw and kw in text for kw in keywords):
            score += float(weight)
    return score


def template_learning_priority_score(rec: dict[str, Any] | None) -> float:
    if not isinstance(rec, dict):
        return 0.0
    profile_count = _template_profile_count(rec)
    score = 1.0
    if profile_count > 0:
        score += min(profile_count, 18) * 0.35
    if str(rec.get("extract_saved_as") or "").strip() or profile_count > 0:
        score += 0.8
    if str(rec.get("library_note") or "").strip():
        score += 0.6
    try:
        pages = int(float(rec.get("pages") or 0))
    except Exception:
        pages = 0
    if pages >= 15:
        score += min(pages, 200) / 200.0
    feedback_score = 0.0
    try:
        feedback_score = float(rec.get("template_feedback_score") or 0.0)
    except Exception:
        feedback_score = 0.0
    score += min(max(feedback_score, 0.0), 100.0) / 20.0
    feedback_origin = str(rec.get("template_feedback_origin") or "").strip().lower()
    if feedback_origin == "generated_accepted":
        score += 1.5
    elif feedback_origin:
        score += 0.6
    score += _template_note_priority_score(rec.get("library_note"))
    return round(score, 2)


def template_learning_priority_label(score: Any) -> str:
    try:
        value = float(score or 0.0)
    except Exception:
        value = 0.0
    if value >= 8.0:
        return "高优先"
    if value >= 5.0:
        return "中优先"
    return "基础"


def _tokenize_text(text: str) -> list[str]:
    out: list[str] = []
    seen = set()
    for token in _TEXT_TOKEN_RE.findall(text or ""):
        txt = str(token or "").strip()
        if len(txt) < 2 or txt in seen:
            continue
        seen.add(txt)
        out.append(txt)
    return out


def normalize_template_chapter_title(title: Any) -> str:
    s = str(title or "").strip()
    if not s:
        return ""
    s = re.sub(r"[·\.…．]{2,}", " ", s)
    s = re.sub(r"\s+\d{1,4}\s*$", "", s)
    s = re.sub(r"\s*第?\s*\d+\s*页\s*$", "", s)
    s = re.sub(r"错误!?未定义书签[。.]?", "", s)
    s = re.sub(r"^第[一二三四五六七八九十百0-9]+章\s*[、\.．]?\s*", "", s)
    s = re.sub(r"^(?!\d{1,2}\.\d)\d{1,2}\s+", "", s)
    s = re.sub(r"^\d{1,2}\s*[\.、\)）]\s*", "", s)
    s = re.sub(r"^[一二三四五六七八九十]{1,3}\s*[\.、\)）]\s*", "", s)
    s = re.sub(r"^\(?[一二三四五六七八九十]{1,3}[\)）]\s*", "", s)
    return s.strip()


def match_template_chapter_theme(title: Any) -> str:
    norm = normalize_template_chapter_title(title)
    if not norm:
        return ""
    best_theme = ""
    best_score = 0
    for theme, keywords in _CHAPTER_THEME_RULES:
        score = 0
        for kw in keywords:
            if kw and kw in norm:
                score += max(2, len(kw))
        if theme in norm:
            score += max(4, len(theme))
        if score > best_score:
            best_theme = theme
            best_score = score
    return best_theme if best_score >= 2 else ""


@lru_cache(maxsize=128)
def _load_template_extract_text(extract_path: str, mtime_ns: int) -> str:
    path = Path(extract_path)
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_level1_heading(line: str) -> bool:
    txt = str(line or "").strip()
    if not txt or len(txt) < 2 or len(txt) > 64:
        return False
    if any(x in txt for x in ("附录", "附件", "参考文献", "目录")):
        return False
    if _TOC_HEADING_RE.search(txt):
        return False
    plain_numeric = re.match(r"^(?!\d{1,2}\.\d)(\d{1,2})\s+(.+)$", txt)
    if plain_numeric:
        body = str(plain_numeric.group(2) or "").strip()
        if any(body.startswith(prefix) for prefix in _NON_CHAPTER_FIELD_PREFIXES):
            return False
        if body and len(body) <= 28 and body.count(" ") <= 2 and not re.search(r"[：:；;]{1,}", body):
            return True
    return any(rx.match(txt) for rx in _CHAPTER_HEADING_PATTERNS)


def _build_template_section_entry(text: str, title: str, content: str, start_offset: int) -> dict[str, Any] | None:
    cleaned_title = normalize_template_chapter_title(title)
    cleaned_content = str(content or "").strip()
    if not cleaned_title or len(cleaned_content) < 20:
        return None
    snippet = re.sub(r"\s+", " ", cleaned_content.replace("\f", " ")).strip()[:220]
    page = None
    try:
        if "\f" in text:
            page = text[: max(0, int(start_offset))].count("\f") + 1
    except Exception:
        page = None
    return {
        "section_title": cleaned_title,
        "theme": match_template_chapter_theme(cleaned_title),
        "content": cleaned_content,
        "snippet": snippet,
        "offset": max(0, int(start_offset)),
        "page": page,
    }


def _split_template_sections_from_text(text: str) -> list[dict[str, Any]]:
    if not str(text or "").strip():
        return []
    sections: list[dict[str, Any]] = []
    current_title = ""
    current_lines: list[str] = []
    current_start = 0
    offset = 0
    for raw_line in str(text).splitlines(keepends=True):
        line = raw_line.replace("\f", " ").strip()
        if _is_level1_heading(line):
            if current_title and current_lines:
                entry = _build_template_section_entry(str(text), current_title, "".join(current_lines), current_start)
                if entry:
                    sections.append(entry)
            current_title = line
            current_lines = [raw_line]
            current_start = offset
        elif current_title:
            current_lines.append(raw_line)
        offset += len(raw_line)
    if current_title and current_lines:
        entry = _build_template_section_entry(str(text), current_title, "".join(current_lines), current_start)
        if entry:
            sections.append(entry)
    return sections


def build_template_chapter_profiles(text: str, *, max_sections: int = 30) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for section in _split_template_sections_from_text(text)[: max(1, int(max_sections or 18))]:
        profiles.append(
            {
                "section_title": str(section.get("section_title") or "").strip(),
                "theme": str(section.get("theme") or "").strip(),
                "snippet": str(section.get("snippet") or "").strip(),
                "offset": int(section.get("offset") or 0),
                "page": section.get("page"),
                "content_chars": len(str(section.get("content") or "").strip()),
                "anchor_headings": _template_learning_anchors([section]),
            }
        )
    return profiles


@lru_cache(maxsize=128)
def _load_template_extract_sections(extract_path: str, mtime_ns: int) -> list[dict[str, Any]]:
    text = _load_template_extract_text(extract_path, mtime_ns)
    return _split_template_sections_from_text(text)


def _score_template_section(section: dict[str, Any], *, query: str, chapter_title: str, chapter_theme: str) -> float:
    title = normalize_template_chapter_title(section.get("section_title"))
    snippet = str(section.get("snippet") or "").strip()
    content = str(section.get("content") or "").strip()
    anchors = " ".join([str(x).strip() for x in (section.get("anchor_headings") or []) if str(x).strip()])
    if not title:
        return 0.0
    query_tokens = _tokenize_text(f"{query} {chapter_title}")[:10]
    chapter_norm = normalize_template_chapter_title(chapter_title)
    score = 0.0
    if chapter_theme and str(section.get("theme") or "").strip() == chapter_theme:
        score += 18.0
    if chapter_norm and title == chapter_norm:
        score += 12.0
    elif chapter_norm and (chapter_norm in title or title in chapter_norm):
        score += 6.0
    search_area = f"{title}\n{snippet}\n{anchors}\n{content[:800]}"
    for token in query_tokens:
        if token and token in title:
            score += 2.8
        elif token and token in search_area:
            score += 1.2
    content_chars = int(section.get("content_chars") or len(content))
    if 100 <= content_chars <= 5000:
        score += 1.0
    return score


def _record_similarity_text(rec: dict[str, Any], section: dict[str, Any]) -> str:
    parts = [
        str(rec.get("filename") or "").strip(),
        str(rec.get("library_note") or "").strip(),
        " ".join(normalize_template_scene_tags(rec.get("template_scene_tags"))),
        normalize_template_chapter_title(section.get("section_title")),
        str(section.get("snippet") or "").strip(),
    ]
    return "\n".join(part for part in parts if part)


def _query_focus_tokens(query: str, *, chapter_title: str, chapter_theme: str) -> list[str]:
    chapter_norm = normalize_template_chapter_title(chapter_title)
    out: list[str] = []
    seen: set[str] = set()
    for token in _tokenize_text(query):
        txt = str(token or "").strip()
        if not txt or txt in seen:
            continue
        if txt in _GENERIC_TEMPLATE_QUERY_TOKENS:
            continue
        if chapter_norm and (txt == chapter_norm or txt in chapter_norm or chapter_norm in txt):
            continue
        if chapter_theme and txt == chapter_theme:
            continue
        seen.add(txt)
        out.append(txt)
    return out[:8]


def _project_reference_score(query: str, rec: dict[str, Any], section: dict[str, Any], *, chapter_title: str, chapter_theme: str) -> float:
    metadata = _record_similarity_text(rec, section)
    if not metadata.strip():
        return 0.0
    score = 0.0
    matched_focus = 0
    for token in _query_focus_tokens(query, chapter_title=chapter_title, chapter_theme=chapter_theme):
        if token not in metadata:
            continue
        matched_focus += 1
        if _PROJECT_CODE_RE.fullmatch(token):
            score += 8.0
        elif len(token) >= 10:
            score += 5.2
        elif len(token) >= 6:
            score += 3.2
        else:
            score += 1.2
    if matched_focus >= 2:
        score += 2.0
    return min(18.0, score)


def _rank_template_sections(
    query: str,
    *,
    chapter_title: str,
    project_type: str | None,
    template_page_bucket: str | None = None,
    scene_tags: list[str] | None = None,
    audit_path: str | Path | None = None,
    max_docs: int = 12,
) -> list[dict[str, Any]]:
    path = _resolve_audit_path(audit_path)
    if not path.exists():
        return []
    try:
        mtime_ns = int(os.stat(path).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    normalized_type = normalize_project_type(project_type)
    if not normalized_type:
        return []
    normalized_bucket = normalize_template_page_bucket(template_page_bucket)
    chapter_theme = match_template_chapter_theme(chapter_title)
    query_scene_tags = normalize_template_scene_tags(scene_tags)
    ranked: list[dict[str, Any]] = []
    seen_docs: set[str] = set()
    for rec in _load_template_library_records(str(path), mtime_ns):
        rec_type = normalize_project_type(rec.get("project_type"))
        if rec_type != normalized_type:
            continue
        rec_bucket = normalize_template_page_bucket(rec.get("template_page_bucket"), page_count=rec.get("pages"))
        if normalized_bucket and rec_bucket != normalized_bucket:
            continue
        record_scene_tags = normalize_template_scene_tags(rec.get("template_scene_tags"))
        extract_path = Path(str(rec.get("extract_saved_as") or "").strip())
        doc_key = str(rec.get("sha256") or extract_path or rec.get("filename") or "")
        if doc_key in seen_docs:
            continue
        seen_docs.add(doc_key)
        learning_priority_score = template_learning_priority_score(rec)
        learning_priority_label = template_learning_priority_label(learning_priority_score)
        for section in _template_sections_from_record(rec):
            score = _score_template_section(section, query=query, chapter_title=chapter_title, chapter_theme=chapter_theme)
            if score <= 0:
                continue
            scene_match_score = _scene_overlap_score(query_scene_tags, record_scene_tags)
            project_reference_score = _project_reference_score(
                query,
                rec,
                section,
                chapter_title=chapter_title,
                chapter_theme=chapter_theme,
            )
            score += learning_priority_score * 0.9
            score += scene_match_score
            score += project_reference_score
            ranked.append(
                {
                    "filename": rec.get("filename"),
                    "sha256": rec.get("sha256"),
                    "extract_saved_as": str(extract_path) if extract_path else "",
                    "section_title": section.get("section_title"),
                    "template_theme": section.get("theme"),
                    "snippet": section.get("snippet"),
                    "content": section.get("content"),
                    "offset": section.get("offset"),
                    "page": section.get("page"),
                    "anchor_headings": section.get("anchor_headings"),
                    "content_chars": section.get("content_chars"),
                    "template_scene_tags": record_scene_tags,
                    "scene_match_score": scene_match_score,
                    "project_reference_score": project_reference_score,
                    "template_chapter_profile_count": _template_profile_count(rec),
                    "learning_priority_score": learning_priority_score,
                    "learning_priority_label": learning_priority_label,
                    "score": float(score),
                }
            )
        if len(seen_docs) >= max_docs and ranked:
            break
    ranked.sort(
        key=lambda item: (
            -float(item.get("score") or 0.0),
            -float(item.get("learning_priority_score") or 0.0),
            str(item.get("filename") or ""),
            int(item.get("offset") or 0),
        )
    )
    deduped: list[dict[str, Any]] = []
    seen_sections: set[tuple[str, str]] = set()
    for item in ranked:
        key = (str(item.get("sha256") or ""), str(item.get("section_title") or ""))
        if key in seen_sections:
            continue
        seen_sections.add(key)
        deduped.append(item)
    return deduped


def _template_sections_from_record(rec: dict[str, Any]) -> list[dict[str, Any]]:
    stored = rec.get("template_chapter_profiles") if isinstance(rec.get("template_chapter_profiles"), list) else []
    normalized_stored = []
    for item in stored:
        normalized = _normalized_stored_template_section(item)
        if normalized:
            normalized_stored.append(normalized)
    if normalized_stored:
        return normalized_stored
    extract_path = Path(str(rec.get("extract_saved_as") or "").strip())
    if not extract_path.exists() or not extract_path.is_file():
        return []
    try:
        extract_mtime_ns = int(os.stat(extract_path).st_mtime_ns)
    except Exception:
        extract_mtime_ns = 0
    return _load_template_extract_sections(str(extract_path), extract_mtime_ns)


@lru_cache(maxsize=64)
def _template_learning_digest_cached(
    audit_path: str,
    mtime_ns: int,
    project_type: str,
    template_page_bucket: str,
    scene_tags_json: str,
) -> dict[str, Any]:
    normalized_type = normalize_project_type(project_type)
    normalized_bucket = normalize_template_page_bucket(template_page_bucket)
    normalized_scene_tags = normalize_template_scene_tags(scene_tags_json)
    if not normalized_type:
        return {
            "project_type": "",
            "template_page_bucket": normalized_bucket,
            "scene_tags": normalized_scene_tags,
            "matched_template_count": 0,
            "matched_profile_count": 0,
            "theme_coverage": [],
            "anchor_coverage": [],
            "scene_coverage": [],
        }
    theme_counter: Counter[str] = Counter()
    anchor_counter: Counter[str] = Counter()
    scene_counter: Counter[str] = Counter()
    matched_template_count = 0
    matched_profile_count = 0
    for rec in _load_template_library_records(audit_path, mtime_ns):
        rec_type = normalize_project_type(rec.get("project_type"))
        if rec_type != normalized_type:
            continue
        rec_bucket = normalize_template_page_bucket(rec.get("template_page_bucket"), page_count=rec.get("pages"))
        if normalized_bucket and rec_bucket != normalized_bucket:
            continue
        rec_scene_tags = normalize_template_scene_tags(rec.get("template_scene_tags"))
        if normalized_scene_tags and not set(normalized_scene_tags).intersection(rec_scene_tags):
            continue
        sections = _template_sections_from_record(rec)
        if not sections:
            continue
        matched_template_count += 1
        matched_profile_count += len(sections)
        for scene_tag in rec_scene_tags:
            scene_counter[scene_tag] += 1
        for section in sections:
            theme = str(section.get("theme") or "").strip()
            if theme:
                theme_counter[theme] += 1
            anchors = section.get("anchor_headings") if isinstance(section.get("anchor_headings"), list) else []
            if not anchors:
                anchors = _template_learning_anchors([section])
            for anchor in anchors:
                text = str(anchor or "").strip()
                if text:
                    anchor_counter[text] += 1
    return {
        "project_type": normalized_type,
        "template_page_bucket": normalized_bucket,
        "scene_tags": normalized_scene_tags,
        "matched_template_count": matched_template_count,
        "matched_profile_count": matched_profile_count,
        "theme_coverage": [{"theme": theme, "count": count} for theme, count in theme_counter.most_common(6)],
        "anchor_coverage": [{"anchor": anchor, "count": count} for anchor, count in anchor_counter.most_common(6)],
        "scene_coverage": [{"scene_tag": tag, "count": count} for tag, count in scene_counter.most_common(6)],
    }


def summarize_template_learning_digest(
    *,
    project_type: str | None,
    template_page_bucket: str | None = None,
    scene_tags: list[str] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    path = _resolve_audit_path(audit_path)
    normalized_type = normalize_project_type(project_type)
    normalized_bucket = normalize_template_page_bucket(template_page_bucket)
    normalized_scene_tags = normalize_template_scene_tags(scene_tags)
    if not path.exists():
        return {
            "project_type": normalized_type,
            "template_page_bucket": normalized_bucket,
            "scene_tags": normalized_scene_tags,
            "matched_template_count": 0,
            "matched_profile_count": 0,
            "theme_coverage": [],
            "anchor_coverage": [],
            "scene_coverage": [],
            "coverage_hint": "",
        }
    try:
        mtime_ns = int(os.stat(path).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    cache_payload = {
        "audit_path": str(path.resolve()),
        "mtime_ns": mtime_ns,
        "project_type": normalized_type or "",
        "template_page_bucket": normalized_bucket or "",
        "scene_tags": normalized_scene_tags,
    }
    digest = _load_template_learning_disk_cache("digest", cache_payload)
    if not digest:
        digest = _template_learning_digest_cached(
            str(path),
            mtime_ns,
            normalized_type or "",
            normalized_bucket or "",
            ",".join(normalized_scene_tags),
        )
        _save_template_learning_disk_cache("digest", cache_payload, digest)
    top_themes = [str(item.get("theme") or "").strip() for item in digest.get("theme_coverage") or [] if str(item.get("theme") or "").strip()]
    top_scenes = [str(item.get("scene_tag") or "").strip() for item in digest.get("scene_coverage") or [] if str(item.get("scene_tag") or "").strip()]
    coverage_hint = ""
    if digest.get("matched_profile_count"):
        theme_preview = "、".join(top_themes[:4])
        scene_preview = "、".join(top_scenes[:3])
        coverage_hint = (
            f"当前组合已沉淀 {int(digest.get('matched_profile_count') or 0)} 个章节画像"
            + (f"，高频章节包括 {theme_preview}" if theme_preview else "")
            + (f"，高频场景包括 {scene_preview}" if scene_preview else "")
            + "。"
        )
    return dict(digest, coverage_hint=coverage_hint)


def _template_learning_anchors(sections: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for section in sections:
        stored_anchors = section.get("anchor_headings") if isinstance(section.get("anchor_headings"), list) else []
        if stored_anchors:
            for anchor in stored_anchors:
                txt = str(anchor or "").strip()
                if txt:
                    counter[txt] += 1
            continue
        search_area = f"{section.get('section_title')}\n{section.get('content')}"
        for label, keywords in _LEARNING_ANCHOR_RULES:
            if any(kw and kw in search_area for kw in keywords):
                counter[label] += 1
    return [label for label, _ in counter.most_common(4)]


def _normalized_stored_template_section(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = normalize_template_chapter_title(raw.get("section_title"))
    if not title:
        return None
    snippet = re.sub(r"\s+", " ", str(raw.get("snippet") or "").replace("\f", " ")).strip()
    anchors = [str(x).strip() for x in (raw.get("anchor_headings") or []) if str(x).strip()]
    return {
        "section_title": title,
        "theme": str(raw.get("theme") or match_template_chapter_theme(title)).strip(),
        "snippet": snippet,
        "content": "",
        "offset": int(raw.get("offset") or 0),
        "page": raw.get("page"),
        "content_chars": int(raw.get("content_chars") or 0),
        "anchor_headings": anchors[:4],
    }


def _as_public_template_hit(item: dict[str, Any], *, match_mode: str) -> dict[str, Any]:
    return {
        "filename": item.get("filename"),
        "sha256": item.get("sha256"),
        "extract_saved_as": item.get("extract_saved_as"),
        "offset": item.get("offset"),
        "page": item.get("page"),
        "snippet": item.get("snippet"),
        "section_title": item.get("section_title"),
        "template_theme": item.get("template_theme"),
        "template_scene_tags": item.get("template_scene_tags"),
        "scene_match_score": item.get("scene_match_score"),
        "project_reference_score": item.get("project_reference_score"),
        "template_chapter_profile_count": item.get("template_chapter_profile_count"),
        "learning_priority_score": item.get("learning_priority_score"),
        "learning_priority_label": item.get("learning_priority_label"),
        "match_mode": match_mode,
    }


def template_library_record_id(rec: dict[str, Any] | None) -> str:
    if not isinstance(rec, dict):
        return ""
    raw = "|".join(
        [
            str(rec.get("ts") or "").strip(),
            str(rec.get("sha256") or "").strip(),
            str(rec.get("filename") or "").strip(),
            str(rec.get("saved_as") or "").strip(),
            str(rec.get("extract_saved_as") or "").strip(),
            str(rec.get("preview_saved_as") or "").strip(),
        ]
    )
    if not raw.replace("|", "").strip():
        return ""
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


@lru_cache(maxsize=8)
def _load_template_library_records(audit_path: str, mtime_ns: int) -> list[dict[str, Any]]:
    path = Path(audit_path)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]:
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        if is_template_library_record(rec):
            out.append(rec)
    return out


def is_template_library_record(rec: dict[str, Any] | None) -> bool:
    if not isinstance(rec, dict):
        return False
    tags = rec.get("tags") if isinstance(rec.get("tags"), list) else []
    tags_set = {str(tag).strip() for tag in tags if str(tag).strip()}
    scope = str(rec.get("library_scope") or rec.get("source_hint") or "").strip().lower()
    return TEMPLATE_LIBRARY_TAG in tags_set or scope == TEMPLATE_LIBRARY_SCOPE


def _record_file_paths(rec: dict[str, Any] | None) -> list[str]:
    if not isinstance(rec, dict):
        return []
    out: list[str] = []
    for key in ("saved_as", "extract_saved_as", "preview_saved_as"):
        value = str(rec.get(key) or "").strip()
        if value:
            out.append(value)
    return out


def _record_matches_scene_tags(rec: dict[str, Any] | None, scene_tags: list[str] | None) -> bool:
    wanted = normalize_template_scene_tags(scene_tags)
    if not wanted:
        return True
    record_tags = normalize_template_scene_tags((rec or {}).get("template_scene_tags"))
    if not record_tags:
        return False
    return bool(set(wanted).intersection(record_tags))


def list_template_library_items(
    *,
    project_type: str | None = None,
    template_page_bucket: str | None = None,
    scene_tags: list[str] | None = None,
    sort_by: str | None = None,
    limit: int = 20,
    audit_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    path = _resolve_audit_path(audit_path)
    if not path.exists():
        return []
    try:
        mtime_ns = int(os.stat(path).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    normalized_type = normalize_project_type(project_type)
    normalized_bucket = normalize_template_page_bucket(template_page_bucket)
    normalized_sort = str(sort_by or "recent").strip().lower()
    if normalized_sort not in {"recent", "priority"}:
        normalized_sort = "recent"
    out: list[dict[str, Any]] = []
    for rec in _load_template_library_records(str(path), mtime_ns):
        rec_type = normalize_project_type(rec.get("project_type"))
        if normalized_type and rec_type != normalized_type:
            continue
        rec_bucket = normalize_template_page_bucket(rec.get("template_page_bucket"), page_count=rec.get("pages"))
        if normalized_bucket and rec_bucket != normalized_bucket:
            continue
        if not _record_matches_scene_tags(rec, scene_tags):
            continue
        profile_count = _template_profile_count(rec)
        priority_score = template_learning_priority_score(rec)
        out.append(
            {
                "record_id": template_library_record_id(rec),
                "ts": rec.get("ts"),
                "title": rec.get("library_title") or rec.get("filename"),
                "filename": rec.get("filename"),
                "project_type": rec_type or rec.get("project_type"),
                "template_page_bucket": rec_bucket,
                "template_page_bucket_label": template_page_bucket_label(rec_bucket),
                "library_note": rec.get("library_note"),
                "library_tags": normalize_template_scene_tags(rec.get("library_tags")),
                "chapter_scope": normalize_template_scene_tags(rec.get("chapter_scope")),
                "library_summary": rec.get("library_summary"),
                "library_style_profile": rec.get("library_style_profile"),
                "enabled": bool(rec.get("enabled", True)),
                "usable": bool(rec.get("usable", True)),
                "pages": rec.get("pages"),
                "bytes": rec.get("bytes"),
                "source_file": rec.get("saved_as"),
                "storage_path": rec.get("saved_as"),
                "preview_saved_as": rec.get("preview_saved_as"),
                "extract_saved_as": rec.get("extract_saved_as"),
                "sha256": rec.get("sha256"),
                "template_scene_tags": normalize_template_scene_tags(rec.get("template_scene_tags")),
                "template_feedback_score": rec.get("template_feedback_score"),
                "template_feedback_origin": rec.get("template_feedback_origin"),
                "template_chapter_profile_count": profile_count,
                "learning_priority_score": priority_score,
                "learning_priority_label": template_learning_priority_label(priority_score),
            }
        )
    if normalized_sort == "priority":
        out.sort(
            key=lambda item: (
                float(item.get("learning_priority_score") or 0.0),
                int(item.get("template_chapter_profile_count") or 0),
                str(item.get("ts") or ""),
                str(item.get("filename") or ""),
            ),
            reverse=True,
        )
    else:
        out.sort(
            key=lambda item: (
                str(item.get("ts") or ""),
                str(item.get("filename") or ""),
            ),
            reverse=True,
        )
    return out[: max(1, int(limit or 20))]


def delete_template_library_item(
    record_id: str,
    *,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    rid = str(record_id or "").strip()
    if not rid:
        raise ValueError("record_id is required")
    path = _resolve_audit_path(audit_path)
    if not path.exists():
        raise KeyError(rid)

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        lines = []

    parsed_records: list[dict[str, Any] | None] = []
    target_index = -1
    deleted_record: dict[str, Any] | None = None
    for idx, raw in enumerate(lines):
        try:
            rec = json.loads(raw)
        except Exception:
            rec = None
        parsed_records.append(rec if isinstance(rec, dict) else None)
        if target_index >= 0 or not is_template_library_record(rec):
            continue
        if template_library_record_id(rec) == rid:
            target_index = idx
            deleted_record = rec

    if target_index < 0 or not isinstance(deleted_record, dict):
        raise KeyError(rid)

    remaining_lines = [raw for idx, raw in enumerate(lines) if idx != target_index]
    remaining_records = [rec for idx, rec in enumerate(parsed_records) if idx != target_index and isinstance(rec, dict)]

    payload = "\n".join(remaining_lines)
    if remaining_lines:
        payload += "\n"
    path.write_text(payload, encoding="utf-8")
    _load_template_library_records.cache_clear()
    _load_template_extract_text.cache_clear()
    _load_template_extract_sections.cache_clear()
    _template_learning_digest_cached.cache_clear()

    remaining_paths = {item for rec in remaining_records for item in _record_file_paths(rec)}
    removed_paths: list[str] = []
    kept_paths: list[str] = []
    for raw_path in _record_file_paths(deleted_record):
        if raw_path in remaining_paths:
            kept_paths.append(raw_path)
            continue
        file_path = Path(raw_path)
        try:
            if file_path.exists():
                file_path.unlink()
                removed_paths.append(raw_path)
        except Exception:
            kept_paths.append(raw_path)

    rec_bucket = normalize_template_page_bucket(deleted_record.get("template_page_bucket"), page_count=deleted_record.get("pages"))
    return {
        "record_id": rid,
        "filename": deleted_record.get("filename"),
        "project_type": normalize_project_type(deleted_record.get("project_type")) or deleted_record.get("project_type"),
        "template_page_bucket": rec_bucket,
        "template_page_bucket_label": template_page_bucket_label(rec_bucket),
        "removed_paths": removed_paths,
        "kept_paths": kept_paths,
    }


def summarize_template_library(
    *,
    project_types: list[str] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    path = _resolve_audit_path(audit_path)
    ordered_types = [str(x) for x in (project_types or ordered_project_types()) if str(x).strip()]
    by_project_type = {tp: 0 for tp in ordered_types}
    by_template_page_bucket = {bucket: 0 for bucket in TEMPLATE_PAGE_BUCKETS}
    by_project_type_profile_count = {tp: 0 for tp in ordered_types}
    by_project_type_bucket = {
        tp: {bucket: 0 for bucket in TEMPLATE_PAGE_BUCKETS}
        for tp in ordered_types
    }
    by_project_type_bucket_profile_count = {
        tp: {bucket: 0 for bucket in TEMPLATE_PAGE_BUCKETS}
        for tp in ordered_types
    }
    total_count = 0
    total_profile_count = 0
    high_priority_count = 0
    accepted_feedback_count = 0
    system_feedback_count = 0
    latest_ts = ""
    latest_item: dict[str, Any] | None = None
    if not path.exists():
        return {
            "total_count": 0,
            "total_profile_count": 0,
            "high_priority_count": 0,
            "accepted_feedback_count": 0,
            "system_feedback_count": 0,
            "by_project_type": by_project_type,
            "by_project_type_profile_count": by_project_type_profile_count,
            "by_template_page_bucket": by_template_page_bucket,
            "by_project_type_bucket": by_project_type_bucket,
            "by_project_type_bucket_profile_count": by_project_type_bucket_profile_count,
            "latest_ts": "",
            "latest_item": None,
            "project_types_with_items": [],
        }
    try:
        mtime_ns = int(os.stat(path).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    for rec in _load_template_library_records(str(path), mtime_ns):
        total_count += 1
        profile_count = _template_profile_count(rec)
        total_profile_count += profile_count
        priority_score = template_learning_priority_score(rec)
        if template_learning_priority_label(priority_score) == "高优先":
            high_priority_count += 1
        feedback_origin = str(rec.get("template_feedback_origin") or "").strip().lower()
        if feedback_origin == "generated_accepted":
            accepted_feedback_count += 1
            system_feedback_count += 1
        elif feedback_origin:
            system_feedback_count += 1
        tp = normalize_project_type(rec.get("project_type")) or str(rec.get("project_type") or "").strip()
        bucket = normalize_template_page_bucket(rec.get("template_page_bucket"), page_count=rec.get("pages"))
        if tp:
            by_project_type[tp] = int(by_project_type.get(tp) or 0) + 1
            by_project_type_profile_count[tp] = int(by_project_type_profile_count.get(tp) or 0) + profile_count
            if tp not in by_project_type_bucket:
                by_project_type_bucket[tp] = {item: 0 for item in TEMPLATE_PAGE_BUCKETS}
            if tp not in by_project_type_bucket_profile_count:
                by_project_type_bucket_profile_count[tp] = {item: 0 for item in TEMPLATE_PAGE_BUCKETS}
        if bucket:
            by_template_page_bucket[bucket] = int(by_template_page_bucket.get(bucket) or 0) + 1
            if tp:
                by_project_type_bucket[tp][bucket] = int(by_project_type_bucket[tp].get(bucket) or 0) + 1
                by_project_type_bucket_profile_count[tp][bucket] = (
                    int(by_project_type_bucket_profile_count[tp].get(bucket) or 0) + profile_count
                )
        ts = str(rec.get("ts") or "").strip()
        if ts and (not latest_ts or ts > latest_ts):
            latest_ts = ts
            latest_item = {
                "record_id": template_library_record_id(rec),
                "ts": ts,
                "filename": rec.get("filename"),
                "project_type": tp,
                "template_page_bucket": bucket,
                "template_page_bucket_label": template_page_bucket_label(bucket),
                "library_note": rec.get("library_note"),
                "template_scene_tags": normalize_template_scene_tags(rec.get("template_scene_tags")),
                "template_feedback_score": rec.get("template_feedback_score"),
                "template_feedback_origin": rec.get("template_feedback_origin"),
                "template_chapter_profile_count": profile_count,
                "learning_priority_score": priority_score,
                "learning_priority_label": template_learning_priority_label(priority_score),
            }
    return {
        "total_count": total_count,
        "total_profile_count": total_profile_count,
        "high_priority_count": high_priority_count,
        "accepted_feedback_count": accepted_feedback_count,
        "system_feedback_count": system_feedback_count,
        "by_project_type": by_project_type,
        "by_project_type_profile_count": by_project_type_profile_count,
        "by_template_page_bucket": by_template_page_bucket,
        "by_project_type_bucket": by_project_type_bucket,
        "by_project_type_bucket_profile_count": by_project_type_bucket_profile_count,
        "latest_ts": latest_ts,
        "latest_item": latest_item,
        "project_types_with_items": [tp for tp, count in by_project_type.items() if int(count or 0) > 0],
    }


def build_template_chapter_learning_context(
    query: str,
    *,
    chapter_title: str,
    project_type: str | None,
    template_page_bucket: str | None = None,
    scene_tags: list[str] | None = None,
    limit: int = 3,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_type = normalize_project_type(project_type)
    chapter_theme = match_template_chapter_theme(chapter_title)
    normalized_scene_tags = normalize_template_scene_tags(scene_tags or infer_template_scene_tags(query, chapter_title, project_type=normalized_type))
    path = _resolve_audit_path(audit_path)
    try:
        mtime_ns = int(os.stat(path).st_mtime_ns) if path.exists() else 0
    except Exception:
        mtime_ns = 0
    cache_payload = {
        "audit_path": str(path.resolve()) if path.exists() else str(path),
        "mtime_ns": mtime_ns,
        "project_type": normalized_type or "",
        "template_page_bucket": normalize_template_page_bucket(template_page_bucket) or "",
        "chapter_title": normalize_template_chapter_title(chapter_title),
        "scene_tags": normalized_scene_tags,
        "query": str(query or "").strip()[:240],
        "limit": int(limit or 3),
    }
    cached_context = _load_template_learning_disk_cache("chapter_context", cache_payload, max_age_sec=3 * 24 * 3600)
    if cached_context:
        return cached_context
    learning_digest = summarize_template_learning_digest(
        project_type=normalized_type,
        template_page_bucket=template_page_bucket,
        scene_tags=normalized_scene_tags,
        audit_path=audit_path,
    )
    ranked = _rank_template_sections(
        query,
        chapter_title=chapter_title,
        project_type=normalized_type,
        template_page_bucket=template_page_bucket,
        scene_tags=normalized_scene_tags,
        audit_path=audit_path,
        max_docs=max(8, min(16, int(limit or 3) * 4)),
    )
    top_ranked = ranked[: max(1, int(limit or 3))]
    hits = [_as_public_template_hit(item, match_mode="chapter_theme") for item in top_ranked]
    requirement_lines: list[str] = []
    sample_titles: list[str] = []
    for item in top_ranked:
        title = str(item.get("section_title") or "").strip()
        if title and title not in sample_titles:
            sample_titles.append(title)
    anchors = _template_learning_anchors(top_ranked)
    theme_coverage = learning_digest.get("theme_coverage") if isinstance(learning_digest, dict) else []
    if not isinstance(theme_coverage, list):
        theme_coverage = []
    theme_preview = [str(item.get("theme") or "").strip() for item in theme_coverage if str(item.get("theme") or "").strip()]
    current_theme_count = 0
    scene_preview = [str(item.get("scene_tag") or "").strip() for item in (learning_digest.get("scene_coverage") or []) if str(item.get("scene_tag") or "").strip()]
    if chapter_theme:
        for item in theme_coverage:
            if str(item.get("theme") or "").strip() == chapter_theme:
                try:
                    current_theme_count = int(item.get("count") or 0)
                except Exception:
                    current_theme_count = 0
                break
    if top_ranked:
        if chapter_theme:
            requirement_lines.append(
                f"样板学习画像：当前章节归类为“{chapter_theme}”，优先参考同类型优秀样板中的对应章节组织方式，不得改变本项目招标目录。"
            )
        else:
            requirement_lines.append("样板学习画像：当前章节已启用章节级样板匹配，仅可借鉴章内结构、展开颗粒度和短句表达。")
        if anchors:
            requirement_lines.append("样板高频锚点：" + "、".join(anchors[:4]) + "。")
        if current_theme_count > 0:
            requirement_lines.append(f"样板主题覆盖：当前类型在“{chapter_theme}”上已沉淀 {current_theme_count} 个章节画像。")
        elif theme_preview:
            requirement_lines.append("同类样板高频章节：" + "、".join(theme_preview[:4]) + "。")
        if normalized_scene_tags:
            requirement_lines.append("样板场景匹配：" + "、".join(normalized_scene_tags[:4]) + "。")
        elif scene_preview:
            requirement_lines.append("同类高频场景：" + "、".join(scene_preview[:3]) + "。")
        if sample_titles:
            requirement_lines.append("样板代表章节：" + "；".join(sample_titles[:3]) + "。")

    if len(hits) < max(1, int(limit or 3)):
        normalized_bucket = normalize_template_page_bucket(template_page_bucket)
        fallback_hits = search_ingested_docs(
            query,
            limit=max(1, int(limit or 3)),
            require_tags=[TEMPLATE_LIBRARY_TAG],
            record_project_type=normalized_type,
            record_filters={"template_page_bucket": normalized_bucket} if normalized_bucket else None,
            audit_path=audit_path,
        )
        seen_keys = {
            (
                str(hit.get("sha256") or "").strip(),
                int(hit.get("offset") or 0),
            )
            for hit in hits
        }
        for hit in fallback_hits:
            key = (
                str(hit.get("sha256") or "").strip(),
                int(hit.get("offset") or 0),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            hits.append(dict(hit, match_mode="fallback_search"))
            if len(hits) >= max(1, int(limit or 3)):
                break

    result = {
        "project_type": normalized_type,
        "template_page_bucket": normalize_template_page_bucket(template_page_bucket),
        "scene_tags": normalized_scene_tags,
        "chapter_title": normalize_template_chapter_title(chapter_title),
        "theme": chapter_theme,
        "hits": hits[: max(1, int(limit or 3))],
        "anchor_headings": anchors,
        "sample_titles": sample_titles[:3],
        "theme_coverage": theme_coverage[:4],
        "anchor_coverage": learning_digest.get("anchor_coverage") if isinstance(learning_digest, dict) else [],
        "scene_coverage": learning_digest.get("scene_coverage") if isinstance(learning_digest, dict) else [],
        "coverage_hint": str((learning_digest or {}).get("coverage_hint") or "").strip() if isinstance(learning_digest, dict) else "",
        "requirement_lines": requirement_lines[:4],
    }
    _save_template_learning_disk_cache("chapter_context", cache_payload, result)
    return result


def search_template_library_docs(
    query: str,
    *,
    project_type: str | None,
    template_page_bucket: str | None = None,
    chapter_title: str | None = None,
    scene_tags: list[str] | None = None,
    limit: int = 3,
    audit_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    normalized_type = normalize_project_type(project_type)
    if not normalized_type:
        return []
    ctx = build_template_chapter_learning_context(
        query,
        chapter_title=chapter_title or query,
        project_type=normalized_type,
        template_page_bucket=template_page_bucket,
        scene_tags=scene_tags,
        limit=limit,
        audit_path=audit_path,
    )
    return [dict(hit) for hit in (ctx.get("hits") or []) if isinstance(hit, dict)]
