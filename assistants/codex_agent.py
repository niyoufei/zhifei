class CodexAgent:
    def __init__(self):
        self.online=False
        self.client=None

    def suggest_patch(self, code_snippet:str, goal:str, temperature:float=0.2):
        return "[OFFLINE MODE] 仅做占位建议\nGoal: {}\nPatchIdea: 检查print/拼写/异常/逻辑错误".format(goal)