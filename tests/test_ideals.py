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


class TestIdealRoundtrip:
    def test_single_generator(self, R, xy):
        x, y = xy
        I = R.ideal([x**2 - y])
        I2 = roundtrip(I)
        assert I2 == I

    def test_two_generators(self, R, xy):
        x, y = xy
        I = R.ideal([x**2 + y, x * y - 1])
        assert roundtrip(I) == I

    def test_rational_coefficients(self, R, xy):
        x, y = xy
        I = R.ideal([QQ(1)/2 * x + QQ(1)/3 * y - 1])
        assert roundtrip(I) == I

    def test_zero_ideal(self, R):
        I = R.ideal([R.zero()])
        assert roundtrip(I) == I

    def test_unit_ideal(self, R):
        I = R.ideal([R.one()])
        assert roundtrip(I) == I

    def test_three_generators(self, R, xy):
        x, y = xy
        I = R.ideal([x**2, y**2, x * y])
        assert roundtrip(I) == I

    def test_ring_preserved(self, R, xy):
        x, y = xy
        I = R.ideal([x - y])
        assert roundtrip(I).ring() == R

    def test_file_roundtrip(self, R, xy, tmp_path):
        x, y = xy
        I = R.ideal([x**2 - 1, y - x])
        path = str(tmp_path / "I.mrdi")
        reset_global_serializer_state()
        save_file(path, I)
        reset_global_serializer_state()
        assert load_file(path) == I
