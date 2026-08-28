from __future__ import annotations

from typing import Dict, Any, List

from backend.zhifei_autoplan.utils.llm_client import LLMClient


def _select_variant(data: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
        return data["variants"][0]
    return data


async def optimize_sections(data: Dict[str, Any], req: Dict[str, Any]) -> Dict[str, Any]:
    variant = _select_variant(data)
    titles: List[str] = req.get("titles") or []
    if not titles or not isinstance(variant, dict):
        return data

    instruction = req.get("instruction") or "请在保持证据引用的前提下优化本章表达。"

    # Public routes populate this private field only after a fresh server-side
    # provider admission.  It is intentionally distinct from provider_chain so
    # a client cannot inject a credential or endpoint into this path.
    admitted = req.get("_admitted_provider_chain")
    client_specs: List[Dict[str, Any]] = []
    if isinstance(admitted, list) and admitted:
        for row in admitted:
            if not isinstance(row, dict):
                continue
            provider = str(row.get("provider") or "").strip().lower()
            model = str(row.get("model") or "").strip()
            api_key = str(row.get("api_key") or "").strip()
            if provider and model and api_key:
                client_specs.append(
                    {
                        "provider": provider,
                        "model": model,
                        "api_key": api_key,
                    }
                )
    else:
        # Compatibility path for internal callers and unit tests.  Network API
        # routes must use _admitted_provider_chain instead.
        provider = req.get("provider")
        model = req.get("model")
        api_key = req.get("api_key")
        base_url = req.get("base_url")
        secret_key = req.get("secret_key")
        token_url = req.get("token_url")
        if not provider or not model:
            defaults = LLMClient.load_defaults()
            provider = provider or defaults.get("provider")
            model = model or defaults.get("model")
            api_key = api_key or defaults.get("api_key")
            base_url = base_url or defaults.get("base_url")
            secret_key = secret_key or defaults.get("secret_key")
            token_url = token_url or defaults.get("token_url")
        client_specs.append(
            {
                "provider": provider or "",
                "model": model or "",
                "api_key": api_key,
                "base_url": base_url,
                "secret_key": secret_key,
                "token_url": token_url,
            }
        )

    clients = [LLMClient(**spec) for spec in client_specs]

    try:
        sections = variant.get("sections") or []
        for sec in sections:
            title = sec.get("title") or ""
            if title not in titles:
                continue
            content = sec.get("content") or ""
            prompt = (
                f"{instruction}\n\n"
                f"章节标题：{title}\n"
                "要求：保留核心结构与事实，保留或补全证据标记“【证据:来源】”。\n\n"
                f"原文：\n{content}\n\n"
                "请输出优化后的正文："
            )
            for llm in clients:
                try:
                    resp = await llm.complete(prompt)
                except Exception:
                    continue
                if isinstance(resp, dict) and resp.get("text"):
                    sec["content"] = resp["text"]
                    sec["optimized"] = True
                    break
    finally:
        for llm in clients:
            close = getattr(llm, "close", None)
            if callable(close):
                close()
    return data
