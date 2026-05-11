import io
import pytest
from sage.all import ZZ, QQ

from mrdi import save, load


def roundtrip(obj):
    buf = io.StringIO()
    save(buf, obj)
    buf.seek(0)
    return load(buf)


class TestZZRingElem:
    def test_positive(self):
        assert roundtrip(ZZ(42)) == ZZ(42)

    def test_negative(self):
        assert roundtrip(ZZ(-17)) == ZZ(-17)

    def test_zero(self):
        assert roundtrip(ZZ(0)) == ZZ(0)

    def test_large(self):
        n = ZZ(2)**100
        assert roundtrip(n) == n

    def test_type_preserved(self):
        n = roundtrip(ZZ(5))
        assert n.parent() is ZZ


class TestQQFieldElem:
    def test_integer(self):
        assert roundtrip(QQ(3)) == QQ(3)

    def test_fraction(self):
        assert roundtrip(QQ(1) / 3) == QQ(1) / 3

    def test_negative_fraction(self):
        assert roundtrip(QQ(-5) / 7) == QQ(-5) / 7

    def test_zero(self):
        assert roundtrip(QQ(0)) == QQ(0)

    def test_type_preserved(self):
        r = roundtrip(QQ(1) / 2)
        assert r.parent() is QQ
