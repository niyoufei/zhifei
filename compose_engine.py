from typing import List, Dict

class Composer:
    def __init__(self):
        pass

    def compose(self, topic: str, outline: List[str], max_pages: int = 50) -> Dict:
        sections = []
        for idx, title in enumerate(outline):
            sections.append({
                "id": idx + 1,
                "title": title,
                "content": f"{title} —— 本章节内容由自动生成器生成（示例）。"
            })
        return {
            "topic": topic,
            "outline": outline,
            "sections": sections,
            "max_pages": max_pages
        }
