from types import SimpleNamespace

from services.auth_service import authenticate_user


class FakeCursor:
    def __init__(self, row=None):
        self._row = row

    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return self._row


class FakeConnection:
    def __init__(self, row=None):
        self._row = row
        self.closed = False

    def cursor(self):
        return FakeCursor(self._row)

    def close(self):
        self.closed = True


def test_authenticate_user_valida_usuario_do_banco(monkeypatch):
    fake_conn = FakeConnection({"senha": "123456"})

    monkeypatch.setattr("services.auth_service.get_connection", lambda: fake_conn)

    assert authenticate_user("gabriel", "123456") is True
    assert fake_conn.closed is True
