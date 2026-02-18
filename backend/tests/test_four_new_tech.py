from __future__ import annotations


from backend.zhifei_autoplan.four_new_tech import recommend_four_new


def test_recommend_four_new_keyword_alias_match():
    # Library keyword is "塔吊", but BoQ/outlines only mention "塔式起重机".
    boq = {
        "items": [
            {"name": "塔式起重机防碰撞系统安装", "process": {"name": "起重设备安装"}},
            {"name": "塔式起重机力矩限制器", "process": {"name": "起重设备调试"}},
        ]
    }
    recs = recommend_four_new(boq, outline=["起重设备", "安全"], limit=10, topic="房建工程")
    names = {str(it.get("name") or "") for it in recs if isinstance(it, dict)}
    assert any("塔吊防碰撞" in n for n in names)


def test_recommend_four_new_infers_project_type_municipal():
    boq = {"items": [{"name": "道路沥青路面施工", "process": {"name": "沥青路面施工"}}]}
    recs = recommend_four_new(boq, outline=["道路工程"], limit=6, topic="市政道路工程")
    assert recs
    assert all(str(it.get("project_type") or "") == "市政" for it in recs if isinstance(it, dict))

