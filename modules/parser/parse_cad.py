import ezdxf
from pathlib import Path
from typing import Dict, Any

def parse_cad_from_dxf(dxf_path: str) -> Dict[str, Any]:
    """解析 DXF 文件的内容，返回图层信息与实体信息"""
    p = Path(dxf_path)
    if not p.exists():
        return {"error": f"文件不存在：{dxf_path}"}

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        layers = [layer.dxf.name for layer in doc.layers]
        entities = list(msp)

        # 统计 INSERT 块引用
        insert_blocks = {}
        for e in entities:
            if e.dxftype() == "INSERT":
                blk = e.dxf.name
                insert_blocks[blk] = insert_blocks.get(blk, 0) + 1

        return {
            "layers_count": len(layers),
            "layers": layers,
            "entities_count": len(entities),
            "insert_blocks": insert_blocks,
        }

    except Exception as e:
        return {"error": str(e)}
