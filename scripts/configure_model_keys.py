#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.local"
KEY_FIELDS = {
    "google": ("GOOGLE_API_KEY", "Gemini API Key"),
    "openai": ("OPENAI_API_KEY", "OpenAI API Key"),
    "anthropic": ("ANTHROPIC_API_KEY", "Anthropic API Key"),
    "deepseek": ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
}
MODEL_PRIORITY = {
    "ZF_LLM_MAIN_PROVIDER": "anthropic",
    "ZF_LLM_MAIN_MODEL": "claude-opus-5",
    "ANTHROPIC_TEXT_MODEL_MAIN": "claude-opus-5",
    "ANTHROPIC_TEXT_MODEL_DRAFT": "claude-sonnet-5",
    "ANTHROPIC_TEXT_MODEL_REVIEW": "claude-opus-5",
    "ANTHROPIC_TEXT_MODEL_ESCALATION": "claude-fable-5",
    "ANTHROPIC_DOCUMENT_RENDER_MODEL": "claude-sonnet-5",
    "ZF_LLM_FALLBACK1_PROVIDER": "openai",
    "ZF_LLM_FALLBACK1_MODEL": "gpt-5.6-sol",
    "OPENAI_TEXT_MODEL_MAIN": "gpt-5.6-sol",
    "ZF_IMAGE_MAIN_PROVIDER": "openai",
    "ZF_IMAGE_MAIN_MODEL": "gpt-image-2",
    "OPENAI_IMAGE_MODEL": "gpt-image-2",
    "ZF_IMAGE_FALLBACK1_PROVIDER": "google",
    "ZF_IMAGE_FALLBACK1_MODEL": "gemini-3-pro-image",
    "GEMINI_IMAGE_MODEL_A": "gemini-3-pro-image",
}
_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _read_existing() -> tuple[list[str], dict[str, str]]:
    if not ENV_PATH.exists():
        return [], {}
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        match = _LINE_RE.match(line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return lines, values


def _write_secret(name: str, value: str) -> None:
    lines, _ = _read_existing()
    replacement = f"{name}={value}"
    replaced = False
    output: list[str] = []
    for line in lines:
        match = _LINE_RE.match(line.strip())
        if match and match.group(1) == name:
            if not replaced:
                output.append(replacement)
                replaced = True
            continue
        output.append(line)
    if not replaced:
        if output and output[-1].strip():
            output.append("")
        output.append(replacement)

    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".env.local.", dir=str(ENV_PATH.parent), text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(output).rstrip() + "\n")
        os.replace(tmp_name, ENV_PATH)
        os.chmod(ENV_PATH, 0o600)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def apply_model_priority() -> None:
    for name, value in MODEL_PRIORITY.items():
        _write_secret(name, value)


def main() -> int:
    parser = argparse.ArgumentParser(description="安全配置本机模型 API 密钥（隐藏输入，不写入命令历史）")
    parser.add_argument("--provider", choices=sorted(KEY_FIELDS))
    parser.add_argument("--apply-priority", action="store_true", help="写入 Anthropic→OpenAI 文本链和 OpenAI→Gemini 图片链")
    args = parser.parse_args()

    if args.apply_priority:
        apply_model_priority()
        print("已写入模型优先级（不包含任何密钥）。")
    if not args.provider:
        return 0 if args.apply_priority else parser.error("必须指定 --provider 或 --apply-priority")

    env_name, label = KEY_FIELDS[args.provider]
    value = getpass.getpass(f"请粘贴 {label}（输入不会显示），然后按回车：").strip()
    if len(value) < 20 or any(ch.isspace() for ch in value):
        print("配置失败：密钥格式不正确；未写入任何内容。")
        return 2
    _write_secret(env_name, value)
    print(f"已安全保存 {label}；文件权限为 600，且已被 Git 忽略。")
    print("请重启施组专家系统后生效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
