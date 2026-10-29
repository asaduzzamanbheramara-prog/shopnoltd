import asyncio
from unittest.mock import patch

# The controller normally runs in Kubernetes. Unit tests must import it without
# requiring an in-cluster service account or a developer kubeconfig.
with patch("kubernetes.config.load_incluster_config", side_effect=RuntimeError("unit test")), patch(
    "kubernetes.config.load_kube_config"
):
    import main


def make_session(*, last_seen: float, ttl_seconds: int = 300) -> main.Session:
    return main.Session(
        session_id="session-test",
        user_id="user-test",
        emulator_name="aemu-test",
        gateway_name="agw-test",
        created_at=0,
        last_seen=last_seen,
        ttl_seconds=ttl_seconds,
    )


def setup_function() -> None:
    main.sessions.clear()


def teardown_function() -> None:
    main.sessions.clear()


def test_cleanup_keeps_sessions_inside_their_ttl(monkeypatch) -> None:
    session = make_session(last_seen=800)
    main.sessions[session.session_id] = session
    deleted = []
    monkeypatch.setattr(main.time, "time", lambda: 1000)
    monkeypatch.setattr(main, "delete_resources", lambda item: deleted.append(item))

    main.cleanup_expired()

    assert main.sessions[session.session_id] is session
    assert deleted == []


def test_cleanup_deletes_expired_sessions(monkeypatch) -> None:
    session = make_session(last_seen=600)
    main.sessions[session.session_id] = session
    deleted = []
    monkeypatch.setattr(main.time, "time", lambda: 1000)
    monkeypatch.setattr(main, "delete_resources", lambda item: deleted.append(item))

    main.cleanup_expired()

    assert session.session_id not in main.sessions
    assert deleted == [session]


def test_cleanup_retains_session_when_resource_deletion_fails(monkeypatch) -> None:
    session = make_session(last_seen=600)
    main.sessions[session.session_id] = session
    monkeypatch.setattr(main.time, "time", lambda: 1000)
    attempts = []

    def fail_once(item):
        attempts.append(item)
        if len(attempts) == 1:
            raise RuntimeError("temporary Kubernetes API failure")

    monkeypatch.setattr(main, "delete_resources", fail_once)

    main.cleanup_expired()
    assert main.sessions[session.session_id] is session

    main.cleanup_expired()
    assert session.session_id not in main.sessions
    assert attempts == [session, session]


def test_create_session_honors_requested_ttl(monkeypatch) -> None:
    monkeypatch.setattr(main.time, "time", lambda: 1000)
    monkeypatch.setattr(main, "cleanup_expired", lambda: None)
    monkeypatch.setattr(main, "create_resources", lambda _session: None)
    monkeypatch.setattr(main, "MAX_SESSIONS", 1)

    result = asyncio.run(
        main.create_session(main.CreateSessionIn(ttl_seconds=600), user_id="user-test")
    )

    session = main.sessions[result["session_id"]]
    assert session.ttl_seconds == 600
    assert result["expires_at"] == 1600

def test_recover_sessions_restores_unexpired_session(monkeypatch) -> None:
    session_id = "session-recovery-123456789"
    now = 1000
    pod = type("Pod", (), {})()
    pod.metadata = type("Metadata", (), {})()
    pod.metadata.name = main.name_for("aemu", session_id)
    pod.metadata.labels = {
        "app.kubernetes.io/name": "android-emulator",
        "shopnoltd.dev/session": session_id,
    }
    pod.metadata.annotations = {
        "shopnoltd.dev/user-id": "user-recovered",
        "shopnoltd.dev/created-at": "700",
        "shopnoltd.dev/last-seen": "900",
        "shopnoltd.dev/ttl-seconds": "300",
    }
    monkeypatch.setattr(main.core, "list_namespaced_pod", lambda *a, **k: type("Pods", (), {"items": [pod]})())
    monkeypatch.setattr(main.core, "read_namespaced_pod", lambda *a, **k: object())
    monkeypatch.setattr(main.core, "read_namespaced_service", lambda *a, **k: object())
    monkeypatch.setattr(main.networking, "read_namespaced_ingress", lambda *a, **k: object())
    monkeypatch.setattr(main, "cleanup_expired", lambda: None)
    monkeypatch.setattr(main.time, "time", lambda: now)

    main.recover_sessions()

    recovered = main.sessions[session_id]
    assert recovered.user_id == "user-recovered"
    assert recovered.created_at == 700
    assert recovered.last_seen == 900
    assert recovered.ttl_seconds == 300
    assert recovered.gateway_name == main.name_for("agw", session_id)


def test_recover_sessions_queues_old_pods_without_metadata_for_cleanup(monkeypatch) -> None:
    session_id = "session-legacy-123456789"
    pod = type("Pod", (), {})()
    pod.metadata = type("Metadata", (), {})()
    pod.metadata.name = main.name_for("aemu", session_id)
    pod.metadata.labels = {"shopnoltd.dev/session": session_id}
    pod.metadata.annotations = {}
    monkeypatch.setattr(main.core, "list_namespaced_pod", lambda *a, **k: type("Pods", (), {"items": [pod]})())
    deleted = []
    monkeypatch.setattr(main, "delete_resources", lambda item: deleted.append(item))
    monkeypatch.setattr(main.time, "time", lambda: 1000)

    main.recover_sessions()

    assert session_id not in main.sessions
    assert len(deleted) == 1
    assert deleted[0].session_id == session_id

def test_session_access_persists_heartbeat(monkeypatch) -> None:
    session = make_session(last_seen=800)
    main.sessions[session.session_id] = session
    monkeypatch.setattr(main.time, "time", lambda: 1000)
    persisted = []
    monkeypatch.setattr(main, "persist_session_heartbeat", lambda item: persisted.append((item.session_id, item.last_seen)))

    found = main.get_session_for_user(session.session_id, "user-test")

    assert found is session
    assert session.last_seen == 1000
    assert persisted == [(session.session_id, 1000)]


def test_session_access_rejects_other_user_without_touching_session(monkeypatch) -> None:
    session = make_session(last_seen=800)
    main.sessions[session.session_id] = session
    persisted = []
    monkeypatch.setattr(main, "persist_session_heartbeat", lambda item: persisted.append(item))

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        main.get_session_for_user(session.session_id, "different-user")

    assert exc.value.status_code == 404
    assert session.last_seen == 800
    assert persisted == []

