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


class TestIdealRoundtrip:
    def test_single_generator(self, R, xy):
        x, y = xy
        I = R.ideal([x**2 - y])
        assert roundtrip(I) == I

    def test_two_generators(self, R, xy):
        x, y = xy
        I = R.ideal([x**2 + y, x * y - 1])
        assert roundtrip(I) == I

    def test_rational_coefficients(self, R, xy):
        x, y = xy
        I = R.ideal([QQ(1) / 2 * x + QQ(1) / 3 * y - 1])
        assert roundtrip(I) == I

    def test_zero_ideal(self, R):
        assert roundtrip(R.ideal([R.zero()])) == R.ideal([R.zero()])

    def test_unit_ideal(self, R):
        assert roundtrip(R.ideal([R.one()])) == R.ideal([R.one()])

    def test_three_generators(self, R, xy):
        x, y = xy
        I = R.ideal([x**2, y**2, x * y])
        assert roundtrip(I) == I

    def test_ring_preserved(self, R, xy):
        x, y = xy
        assert roundtrip(R.ideal([x - y])).ring() == R

    def test_file_roundtrip(self, R, xy, tmp_path):
        x, y = xy
        I = R.ideal([x**2 - 1, y - x])
        path = str(tmp_path / "I.mrdi")
        save_file(path, I)
        assert load_file(path) == I
