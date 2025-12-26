class Composer:
    def compose(self, topic, outline, max_pages=50):
        return {
            "topic": topic,
            "outline": outline,
            "sections": [
                {
                    "title": "示例章节",
                    "content": "这是自动生成的示例内容，用于验证系统流程正常。"
                }
            ],
            "style": {"font": "SimSun"},
            "saved_at": "build/compose.json"
        }
