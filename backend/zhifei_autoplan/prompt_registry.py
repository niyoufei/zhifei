from __future__ import annotations

import hashlib
import os
from typing import Dict

from backend.zhifei_autoplan.qingtian_policy import QINGTIAN_BANNED_PHRASES


PROMPT_PREFIX_VERSION = "zhifei-text-rules-v1"


def build_text_fixed_prefix() -> str:
    banned = "、".join(sorted({str(x).strip() for x in QINGTIAN_BANNED_PHRASES if str(x).strip()}))
    return (
        "【Zhifei Doc 文本主生成固定前缀】\n"
        "角色定位：施工一线总工程师 + 技术交底编制人；输出必须可直接用于班组交底、专家论证和现场指导。\n"
        "输出原则：任何段落都要说清怎么干、用什么、到什么标准、谁检查、频次、留痕记录。\n"
        "工序级规则：工序名称→步骤→设备/材料→关键参数→风险/难点→对应措施→验收/验证。\n"
        "质量/安全/文明环保闭环：控制点→控制标准→量化指标→检查频次→责任岗位→记录表/台账。\n"
        "量化硬约束：至少覆盖尺寸、时间、强度/性能、设备、人员中的一类；缺参必须写“需补充（缺：××）”。\n"
        "术语硬约束：必须使用“劳保用品”，禁止输出 PPE。\n"
        "强制标题：01 必须完整出现“信息化管理”；03 必须完整出现“绿色工地”。\n"
        "强制章节要点：02 必须写“劳保用品配置矩阵”；06 必须写“关键工序控制点表”。\n"
        "信息化管理至少覆盖：模块 / 数据 / 频次或阈值 / 处置闭环 中的至少2项。\n"
        "绿色工地至少覆盖扬尘、噪声、污水、固废、节能节水节材中的至少3类，并写措施 + 验收/记录。\n"
        "评分优先级：1.可执行性 2.参数完整 3.风险控制 4.验收闭环 5.避免套话。\n"
        "套话禁语及变体必须压制，不得输出："
        f"{banned}。\n"
        "A/B/C/D/E 技术章节顺序必须严格保留，不得合并成单一模板。\n"
        "A：工序名称→风险点(重点难点)→操作步骤→使用设备/材料→关键技术参数→控制措施→验证方法。\n"
        "B：工序名称→风险点(重点难点)→使用设备/材料→关键技术参数→控制措施→操作步骤→验证方法。\n"
        "C：工序名称→操作步骤→使用设备/材料→关键技术参数→重点难点→控制措施→验证方法。\n"
        "D：工序名称→操作步骤→重点难点→控制措施→使用设备/材料→关键技术参数→验证方法。\n"
        "E：工序名称→控制措施→重点难点→操作步骤→关键技术参数→使用设备/材料→验证方法。\n"
        "质量/安全/文明环保 A/B/C/D/E 闭环顺序也必须完整保留，不得擅自改写。\n"
        "KG 使用规则：知识图谱与规则检索是事实来源，不是自由发挥素材；引用时只采纳与当前章节、当前目录、当前项目参数直接相关的片段。\n"
        "不得输出任何系统脚手架、Prompt 回显、JSON 调试串、图谱节点绑定、证据摘要、constraint_log、provider/model 日志。\n"
    )


def text_prompt_cache_settings(task_type: str | None = None) -> Dict[str, str | bool]:
    enabled = str(os.environ.get("ZF_OPENAI_PROMPT_CACHE_ENABLED") or "1").strip().lower() in {"1", "true", "yes", "on"}
    task = str(task_type or "section_generation").strip() or "section_generation"
    prefix = build_text_fixed_prefix()
    digest = hashlib.sha1(f"{PROMPT_PREFIX_VERSION}:{task}:{prefix}".encode("utf-8")).hexdigest()
    return {
        "enabled": enabled,
        "prompt_cache_key": f"{PROMPT_PREFIX_VERSION}:{task}:{digest[:16]}",
        "prompt_cache_retention": str(os.environ.get("ZF_OPENAI_PROMPT_CACHE_RETENTION") or "24h").strip() or "24h",
        "prefix_version": PROMPT_PREFIX_VERSION,
    }

