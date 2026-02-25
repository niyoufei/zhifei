from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import ezdxf

from modules.parser.drawing_topology import build_topology_from_entities

def parse_cad_from_dxf(dxf_path: str) -> Dict[str, Any]:
    """解析 DXF 文件并返回图层/实体统计 + 拓扑摘要（用于施工流水段判定）。"""
    p = Path(dxf_path)
    if not p.exists():
        return {"error": f"文件不存在：{dxf_path}"}

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        layers = [str(layer.dxf.name) for layer in doc.layers]
        entities = list(msp)

        # 统计 INSERT 块引用
        insert_blocks = {}
        entity_types = {}
        for e in entities:
            et = str(e.dxftype() or "").upper()
            entity_types[et] = entity_types.get(et, 0) + 1
            if et == "INSERT":
                blk = e.dxf.name
                insert_blocks[blk] = insert_blocks.get(blk, 0) + 1

        topology = build_topology_from_entities(entities, node_precision=2, max_segments=200000)

        return {
            "layers_count": len(layers),
            "layers": layers,
            "entities_count": len(entities),
            "insert_blocks": insert_blocks,
            "entity_types": entity_types,
            "topology": topology,
        }

    except Exception as e:
        return {"error": str(e)}
