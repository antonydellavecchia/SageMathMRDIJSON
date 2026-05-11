import io
import pytest
from sage.all import QQ, PolynomialRing

from mrdi import save, load, save_file, load_file, reset_global_serializer_state


def roundtrip(obj):
    reset_global_serializer_state()
    buf = io.StringIO()
    save(buf, obj)
    buf.seek(0)
    reset_global_serializer_state()
    return load(buf)


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
        p = QQ(1)/2 * x**2 + QQ(3)/4 * y - QQ(1)/6
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
        p = x + y
        assert roundtrip(p).parent() == R

    def test_file_roundtrip(self, R, xy, tmp_path):
        x, y = xy
        p = x**2 - y
        path = str(tmp_path / "p.mrdi")
        reset_global_serializer_state()
        save_file(path, p)
        reset_global_serializer_state()
        assert load_file(path) == p
