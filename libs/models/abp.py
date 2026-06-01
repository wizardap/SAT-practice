from libs.constraints.SCE import SCE
from libs.constraints.SCLE import ladder_at_most_k
from libs.core.context import EncodingContext


class Graph:
    def __init__(self, n, edges):
        if n <= 0:
            raise ValueError("n must be positive")

        self.n = n
        self.V = list(range(1, n + 1))
        self.E = []

        seen = set()
        for u, v in edges:
            if u == v:
                raise ValueError("self-loops are not supported")
            if not 1 <= u <= n or not 1 <= v <= n:
                raise ValueError("edge endpoint is outside the vertex range")

            edge = (u, v) if u < v else (v, u)
            if edge not in seen:
                seen.add(edge)
                self.E.append(edge)

    @classmethod
    def from_rnd(cls, path):
        with open(path, "r", encoding="utf-8") as file:
            lines = [
                line.strip()
                for line in file
                if line.strip() and not line.startswith("Nombre del problema")
            ]

        n, _, edge_count = map(int, lines[0].split()[:3])
        edges = [tuple(map(int, line.split()[:2])) for line in lines[1:]]
        if len(edges) != edge_count:
            raise ValueError(f"expected {edge_count} edges, got {len(edges)}")

        return cls(n, edges)


class AntiBandwidthProblem:
    def __init__(self, graph, bandwidth, ctx=None, symmetry_break=True, anchor=None):
        if bandwidth <= 0:
            raise ValueError("bandwidth must be positive")

        self.graph = graph
        self.b = bandwidth
        self.ctx = ctx or EncodingContext()
        self.sce = SCE(self.ctx, name="abp_sce")
        self.symmetry_break = symmetry_break
        self.anchor = anchor if anchor is not None else graph.V[0]
        if self.anchor not in graph.V:
            raise ValueError("anchor must be a graph vertex")
        # x_i^l: vertex i is assigned label l.
        self.x = {
            (i, l): self.ctx.var("abp_x", i, l)
            for i in graph.V
            for l in range(1, graph.n + 1)
        }
        self.ladders = {}

    def add_clause(self, *clause):
        self.ctx.add_clause(*clause)

    def X(self, i, l):
        return self.x[(i, l)]

    def labels_of(self, i):
        return [self.X(i, l) for l in range(1, self.graph.n + 1)]

    def vertices_at(self, l):
        return [self.X(i, l) for i in self.graph.V]

    def add_permutation(self):
        # Labels form a permutation: each vertex gets one label,
        # and each label is used by one vertex.
        for i in self.graph.V:
            self.sce.exk(self.labels_of(i), 1)
        for l in range(1, self.graph.n + 1):
            self.sce.exk(self.vertices_at(l), 1)

    def add_symmetry_breaking(self):
        # Label reversal is always symmetric: l -> n + 1 - l.
        # Keep only the half where the anchor vertex is in the left half.
        max_anchor_label = (self.graph.n + 1) // 2
        for label in range(max_anchor_label + 1, self.graph.n + 1):
            self.add_clause(-self.X(self.anchor, label))

    def add_ladders(self):
        if self.b > self.graph.n:
            self.add_clause()
            return

        # Each vertex has one ladder over x_i^1, ..., x_i^n.
        # Registers are later reused to express interval <= 0.
        for i in self.graph.V:
            self.ladders[i] = ladder_at_most_k(
                self.ctx,
                self.labels_of(i),
                self.b,
                1,
                name=f"abp_{i}",
            )

    def subset_count(self):
        return (self.graph.n + self.b - 1) // self.b

    def subset_bounds(self, subset):
        start = (subset - 1) * self.b + 1
        return start, min(start + self.b - 1, self.graph.n)

    def prefix_block(self, subset):
        # Prefix block of subset s connects to the boundary on its left.
        return None if subset == 1 else 2 * subset - 2

    def suffix_block(self, subset):
        # Suffix block of subset s connects to the boundary on its right.
        return None if subset == self.subset_count() else 2 * subset - 1

    def zero_atom(self, i, block, length):
        if block is None:
            return None

        try:
            return -self.ladders[i].R(block, length, 1)
        except ValueError:
            return None

    def zero_atoms(self, i, start, length):
        """Conjunction of returned literals means x_i^start + ... <= 0."""
        end = start + length - 1
        if not 1 <= start <= end <= self.graph.n:
            raise ValueError("interval is outside the label range")

        atoms = []
        label = start

        while label <= end:
            # Split the interval by ladder subsets. A segment can use a prefix
            # block, a suffix block, or fall back to individual x literals.
            subset = (label - 1) // self.b + 1
            subset_start, subset_end = self.subset_bounds(subset)
            seg_end = min(end, subset_end)
            seg_len = seg_end - label + 1

            atom = None
            if label == subset_start:
                atom = self.zero_atom(i, self.prefix_block(subset), seg_len)
            if atom is None and seg_end == subset_end:
                atom = self.zero_atom(i, self.suffix_block(subset), seg_len)

            if atom is None:
                atoms.extend(-self.X(i, l) for l in range(label, seg_end + 1))
            else:
                atoms.append(atom)

            label = seg_end + 1

        return atoms

    def add_edges(self):
        if self.b <= 1:
            return
        if self.b > self.graph.n:
            if self.graph.E:
                self.add_clause()
            return

        for u, v in self.graph.E:
            for start in range(1, self.graph.n - self.b + 2):
                # For each forbidden window, edge (u, v) requires:
                # (u has no label in window) OR (v has no label in window).
                u_zero = self.zero_atoms(u, start, self.b)
                v_zero = self.zero_atoms(v, start, self.b)
                for a in u_zero:
                    for c in v_zero:
                        self.add_clause(a, c)

    def encode(self):
        self.add_permutation()
        if self.symmetry_break:
            self.add_symmetry_breaking()
        if self.b > 1:
            self.add_ladders()
            self.add_edges()
        return self

    def solve(self, solver_cls=None):
        if solver_cls is None:
            try:
                from pysat.solvers import Glucose4
            except ImportError as exc:
                raise ImportError("Solving requires python-sat.") from exc
            solver_cls = Glucose4

        with solver_cls(bootstrap_with=self.ctx.clauses) as solver:
            if not solver.solve():
                return None

            model = {literal for literal in solver.get_model() if literal > 0}
            return {
                i: next(l for l in range(1, self.graph.n + 1) if self.X(i, l) in model)
                for i in self.graph.V
            }

    def write_dimacs(self, path):
        with open(path, "w", encoding="utf-8") as file:
            file.write(f"p cnf {self.ctx.num_vars} {len(self.ctx.clauses)}\n")
            for clause in self.ctx.clauses:
                file.write(" ".join(map(str, clause)) + " 0\n")


def encode_abp(n, edges, bandwidth, ctx=None, symmetry_break=True, anchor=None):
    return AntiBandwidthProblem(
        Graph(n, edges),
        bandwidth,
        ctx=ctx,
        symmetry_break=symmetry_break,
        anchor=anchor,
    ).encode()


def load_rnd_graph(path):
    return Graph.from_rnd(path)


def validate_labeling(graph, bandwidth, labeling):
    if labeling is None:
        return False

    labels = [labeling.get(i) for i in graph.V]
    if sorted(labels) != list(range(1, graph.n + 1)):
        return False

    return all(abs(labeling[u] - labeling[v]) >= bandwidth for u, v in graph.E)


def find_max_bandwidth(
    graph,
    lower_bound=1,
    upper_bound=None,
    solver_cls=None,
    symmetry_break=True,
    anchor=None,
):
    if upper_bound is None:
        upper_bound = graph.n
    if not 1 <= lower_bound <= upper_bound <= graph.n:
        raise ValueError("bounds must satisfy 1 <= lower_bound <= upper_bound <= n")

    best_bandwidth = lower_bound - 1
    best_labeling = None
    low, high = lower_bound, upper_bound

    while low <= high:
        mid = (low + high) // 2
        abp = AntiBandwidthProblem(
            graph,
            mid,
            symmetry_break=symmetry_break,
            anchor=anchor,
        ).encode()
        labeling = abp.solve(solver_cls=solver_cls)

        if labeling is None:
            high = mid - 1
        else:
            best_bandwidth = mid
            best_labeling = labeling
            low = mid + 1

    return best_bandwidth, best_labeling
