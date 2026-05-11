import pytest
from sage.all import SymmetricGroup, CyclicPermutationGroup, PermutationGroup

from conftest import roundtrip


class TestPermutationGroup:
    def test_order_preserved(self):
        G = SymmetricGroup(3)
        G2 = roundtrip(G.gens()[0].parent())
        assert G2.order() == G.order()

    def test_degree_preserved(self):
        G = SymmetricGroup(4)
        G2 = roundtrip(G.gens()[0].parent())
        assert G2.degree() == G.degree()


class TestPermutationGroupElement:
    def test_identity(self):
        G = SymmetricGroup(3)
        e = G.identity()
        e2 = roundtrip(e)
        assert e2 == e

    def test_transposition(self):
        G = SymmetricGroup(4)
        g = G([(1, 2)])
        assert roundtrip(g) == g

    def test_cycle(self):
        G = SymmetricGroup(5)
        g = G([(1, 2, 3, 4, 5)])
        assert roundtrip(g) == g

    def test_composition(self):
        G = SymmetricGroup(4)
        g = G([(1, 2, 3), (4,)])
        assert roundtrip(g) == g

    def test_parent_preserved(self):
        G = SymmetricGroup(3)
        g = G.gen(0)
        g2 = roundtrip(g)
        assert g2.parent().degree() == G.degree()
