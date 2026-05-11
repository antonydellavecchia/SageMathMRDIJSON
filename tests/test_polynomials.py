import pytest
from sage.all import QQ, PolynomialRing

from mrdi import save_file, load_file
from conftest import roundtrip


@pytest.fixture
def R():
    return PolynomialRing(QQ, "x,y")


@pytest.fixture
def xy(R):
    return R.gens()


class TestPolynomialRoundtrip:
    def test_zero(self, R):
        assert roundtrip(R.zero()) == R.zero()

    def test_constant(self, R):
        p = R(QQ(5) / 3)
        assert roundtrip(p) == p

    def test_monomial(self, R, xy):
        x, y = xy
        assert roundtrip(x**3) == x**3

    def test_integer_coefficients(self, R, xy):
        x, y = xy
        p = x**2 * y + 3 * x - 7
        assert roundtrip(p) == p

    def test_rational_coefficients(self, R, xy):
        x, y = xy
        p = QQ(1) / 2 * x**2 + QQ(3) / 4 * y - QQ(1) / 6
        assert roundtrip(p) == p

    def test_multivariate(self, R, xy):
        x, y = xy
        p = x**3 * y**2 - 2 * x * y + y**3 + 1
        assert roundtrip(p) == p

    def test_three_variables(self):
        R = PolynomialRing(QQ, "x,y,z")
        x, y, z = R.gens()
        p = x * y * z + x**2 - z
        assert roundtrip(p) == p

    def test_parent_preserved(self, R, xy):
        x, y = xy
        assert roundtrip(x + y).parent() == R

    def test_file_roundtrip(self, R, xy, tmp_path):
        x, y = xy
        p = x**2 - y
        path = str(tmp_path / "p.mrdi")
        save_file(path, p)
        assert load_file(path) == p


class TestUnivariatePoly:
    def test_zero(self):
        R = PolynomialRing(QQ, "x")
        assert roundtrip(R.zero()) == R.zero()

    def test_constant(self):
        R = PolynomialRing(QQ, "x")
        p = R(QQ(3) / 2)
        assert roundtrip(p) == p

    def test_dense(self):
        R = PolynomialRing(QQ, "x")
        x = R.gen()
        p = x**4 - QQ(1) / 2 * x + 7
        assert roundtrip(p) == p

    def test_parent_preserved(self):
        R = PolynomialRing(QQ, "x")
        x = R.gen()
        p = x**2 + 1
        assert roundtrip(p).parent() == R
