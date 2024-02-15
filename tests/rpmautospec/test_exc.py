from rpmautospec import exc


class TestRpmautospecException:
    def test___init__(self):
        e = exc.RpmautospecException("foo", "bar", code="code", detail="detail")
        assert e.args == ("foo", "bar")
        assert e.code == "code"
        assert e.detail == "detail"

    def test___str__(self):
        e = exc.RpmautospecException("foo", "bar", code="code", detail="detail")
        assert str(e) == "foo, bar:\ndetail"
