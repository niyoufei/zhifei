from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

ENTITY_RE = re.compile(r"#\d+\s*=\s*(IFC[A-Z0-9_]+)\s*\(", flags=re.IGNORECASE)
PROJECT_RE = re.compile(r"IFCPROJECT\([^,]*,[^,]*,'([^']*)'", flags=re.IGNORECASE)
PROPERTY_RE = re.compile(r"IFCPROPERTYSINGLEVALUE\('([^']+)'[^,]*,[^,]*,([^)]*)\)", flags=re.IGNORECASE)
QUANTITY_RE = re.compile(r"IFCQUANTITY[A-Z]+\('([^']+)'[^,]*,[^,]*,[^,]*,([^)]*)\)", flags=re.IGNORECASE)
ENTITY_DOMAIN_MAP = {
    "IFCWALL": "building",
    "IFCSLAB": "building",
    "IFCCOLUMN": "building",
    "IFCBEAM": "building",
    "IFCFOOTING": "earthwork",
    "IFCPILE": "earthwork",
    "IFCPIPESEGMENT": "mep",
    "IFCDUCTSEGMENT": "mep",
    "IFCCABLECARRIERSEGMENT": "mep",
    "IFCROAD": "road",
    "IFCBRIDGE": "bridge",
}


def parse_ifc_payload(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    entity_counts: Dict[str, int] = {}
    for m in ENTITY_RE.finditer(text):
        key = str(m.group(1) or "").upper()
        entity_counts[key] = int(entity_counts.get(key) or 0) + 1

    project_names = [str(x).strip() for x in PROJECT_RE.findall(text) if str(x).strip()]
    project_name = project_names[0] if project_names else ""

    properties: List[Dict[str, Any]] = []
    for m in PROPERTY_RE.finditer(text):
        properties.append({"name": str(m.group(1) or "").strip(), "value": str(m.group(2) or "").strip()})
        if len(properties) >= 60:
            break

    quantities: List[Dict[str, Any]] = []
    for m in QUANTITY_RE.finditer(text):
        quantities.append({"name": str(m.group(1) or "").strip(), "value": str(m.group(2) or "").strip()})
        if len(quantities) >= 60:
            break

    top_entities = sorted(entity_counts.items(), key=lambda x: (-int(x[1]), x[0]))[:40]
    domain_distribution: Dict[str, int] = {}
    for entity, count in entity_counts.items():
        dom = str(ENTITY_DOMAIN_MAP.get(str(entity or "").upper()) or "general")
        domain_distribution[dom] = int(domain_distribution.get(dom) or 0) + int(count)
    sorted_domains = sorted(domain_distribution.items(), key=lambda x: (-int(x[1]), x[0]))
    system_layers = [x[0] for x in sorted_domains if int(x[1]) > 0]

    critical_components: List[Dict[str, Any]] = []
    for entity, count in top_entities[:12]:
        if int(count or 0) <= 0:
            continue
        dom = str(ENTITY_DOMAIN_MAP.get(str(entity or "").upper()) or "general")
        critical_components.append(
            {
                "entity": str(entity),
                "count": int(count),
                "professional_domain": dom,
                "priority": "high" if int(count) >= 3 else "medium",
            }
        )
    return {
        "file": path.name,
        "project_name": project_name,
        "entity_counts": entity_counts,
        "top_entities": [{"entity": k, "count": v} for k, v in top_entities],
        "domain_distribution": [{"professional_domain": k, "count": v} for k, v in sorted_domains],
        "system_layers": system_layers[:12],
        "critical_components": critical_components,
        "properties": properties,
        "quantities": quantities,
    }
