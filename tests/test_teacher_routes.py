from app.main import app


def test_teacher_achievement_routes_are_registered():
    registered = set()
    for route in app.routes:
        methods = route.methods or set()
        for method in methods:
            if method in {"GET", "POST", "PATCH", "DELETE"}:
                registered.add((method, route.path))

    assert ("POST", "/teacher/achievements") in registered
    assert ("PATCH", "/teacher/achievements/{achievement_id}") in registered
    assert ("DELETE", "/teacher/achievements/{achievement_id}") in registered
    assert ("POST", "/teacher/groups/{group_id}/quests/{quest_id}") in registered
    assert ("GET", "/teacher/groups/{group_id}/quests") in registered
    assert ("DELETE", "/teacher/groups/{group_id}/quests/{quest_id}") in registered
