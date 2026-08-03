from app.main import app


def test_chh_does_not_mount_direct_guardian_or_legacy_join_routes():
    paths = {route.path for route in app.routes}

    assert not any(path.startswith("/api/guardian") for path in paths)
    assert not any(path.startswith("/api/join/guardian") for path in paths)


def test_protected_fhh_school_connection_remains_mounted():
    paths = {route.path for route in app.routes}

    assert "/api/integrations/fhh/links/{link_id}/dashboard" in paths
    assert "/api/integrations/fhh/links/{link_id}/messaging/inbox" in paths
    assert "/api/integrations/fhh/links/{link_id}/surveys/query" in paths
