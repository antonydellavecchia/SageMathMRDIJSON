# Writes the reference files in this folder: julia --project=<Oscar.jl> generate.jl tests/oscar
using Oscar
d = ARGS[1]
R, (x, y) = polynomial_ring(QQ, [:x, :y])
U, t = polynomial_ring(QQ, :t)
K, a = number_field(t^2 - 2, :a)
F = GF(7); F4, b = finite_field(2, 2, :b)
Z5 = residue_ring(ZZ, 5)[1]
G = symmetric_group(3)
objs = Dict(
  "int" => ZZ(42), "rat" => QQ(-3, 2), "ZZ" => ZZ, "QQ" => QQ,
  "gfp" => F, "gfp_elem" => F(3), "fq" => F4, "fq_elem" => b + 1,
  "zmod" => Z5, "zmod_elem" => Z5(3), "nf" => K, "nf_elem" => a + 1,
  "upoly" => t^2 - 3//2*t + 5, "mpoly" => x^2*y - 3//2*y + 5,
  "ideal" => ideal(R, [x^2, y - 1]), "mat" => matrix(QQ, [1 2; 3 4]),
  "perm" => cperm(G, [1, 2, 3]), "permgroup" => G)
for (k, v) in objs
  save(joinpath(d, k * ".mrdi"), v)
end
