import pytest
from sage.all import QQ, GF, NumberField, PolynomialRing

from conftest import roundtrip


class TestFinitePrimeField:
    def test_gf7_element(self):
        Fp = GF(7)
        e = Fp(5)
        e2 = roundtrip(e)
        assert e2 == e
        assert e2.parent().characteristic() == 7

    def test_gf2_element(self):
        Fp = GF(2)
        assert roundtrip(Fp(1)) == Fp(1)

    def test_zero(self):
        Fp = GF(11)
        assert roundtrip(Fp(0)) == Fp(0)

    def test_parent_preserved(self):
        Fp = GF(7)
        e = roundtrip(Fp(3))
        assert isinstance(e.parent(), type(Fp))
        assert e.parent().characteristic() == 7


class TestFiniteExtensionField:
    def test_gf4_element(self):
        Fq = GF(4, name="z")
        z = Fq.gen()
        e = z + 1
        e2 = roundtrip(e)
        assert e2 == e

    def test_gf8_element(self):
        Fq = GF(8, name="a")
        a = Fq.gen()
        e = a**2 + a
        e2 = roundtrip(e)
        assert e2 == e

    def test_zero(self):
        Fq = GF(4, name="z")
        assert roundtrip(Fq(0)) == Fq(0)


class TestNumberField:
    @pytest.fixture
    def K_sqrt2(self):
        Rx = PolynomialRing(QQ, "x")
        x = Rx.gen()
        return NumberField(x**2 - 2, "a")

    @pytest.fixture
    def K_cubic(self):
        Rx = PolynomialRing(QQ, "x")
        x = Rx.gen()
        return NumberField(x**3 - 2, "b")

    def test_generator(self, K_sqrt2):
        a = K_sqrt2.gen()
        a2 = roundtrip(a)
        assert a2 == a

    def test_general_element(self, K_sqrt2):
        a = K_sqrt2.gen()
        e = 3 * a + 2
        assert roundtrip(e) == e

    def test_rational_coefficients(self, K_sqrt2):
        a = K_sqrt2.gen()
        e = QQ(1) / 2 * a - QQ(3) / 4
        assert roundtrip(e) == e

    def test_cubic_element(self, K_cubic):
        b = K_cubic.gen()
        e = b**2 - b + 1
        assert roundtrip(e) == e

    def test_parent_preserved(self, K_sqrt2):
        a = K_sqrt2.gen()
        assert roundtrip(a).parent() == K_sqrt2
