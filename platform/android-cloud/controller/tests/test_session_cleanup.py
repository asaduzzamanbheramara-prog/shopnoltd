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


def test_dynamic_session_pods_do_not_reference_namespace_pull_secret() -> None:
    session = make_session(last_seen=1000)

    emulator = main.make_emulator_pod(session)
    gateway = main.make_gateway_pod(session)

    assert emulator.spec.image_pull_secrets in (None, [])
    assert gateway.spec.image_pull_secrets in (None, [])
