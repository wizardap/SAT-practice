from libs.core.context import EncodingContext
from libs.constraints.SCE import SCE
from pysat.solvers import Glucose4


class NQueens:
    def __init__(self, n: int, ctx: EncodingContext = None):
        if n <= 0:
            raise ValueError("n must be positive")
        self.n = n
        self.ctx = ctx or EncodingContext()
        self.x = {
            (row, col): self.ctx.var("nqueens", row, col)
            for row in range(1, n + 1)
            for col in range(1, n + 1)
        }
        self.encoder = SCE(self.ctx, "sce-nqueens")

    def X(self, row, col):
        if not (1 <= row and row <= self.n and 1 <= col and col <= self.n):
            raise ValueError("(row,col) isn't in bound [1,n]")
        return self.x[(row, col)]

    def encoding(self):

        # Exactly one queen in each row
        for row in range(1, self.n + 1):
            self.encoder.exk([self.X(row, col) for col in range(1, self.n + 1)], 1)

        # Exactly one queen in each column
        for col in range(1, self.n + 1):
            self.encoder.exk([self.X(row, col) for row in range(1, self.n + 1)], 1)

        # At most one queen in each diagional

        # Diagonal from top-left to bottom-right
        for d in range(2, 2 * self.n + 1):
            self.encoder.amk(
                [
                    self.X(row, d - row)
                    for row in range(1, self.n + 1)
                    if 1 <= d - row <= self.n
                ],
                1,
            )

        # Diagonal from top-right to bottom-left
        for d in range(-self.n + 1, self.n):
            self.encoder.amk(
                [
                    self.X(row, row - d)
                    for row in range(1, self.n + 1)
                    if 1 <= row - d <= self.n
                ],
                1,
            )

    def print_solution(self, solution):
        if solution is None:
            print("No solution")
            return
        board = [
            ["Q" if (row, col) in solution else "." for col in range(1, self.n + 1)]
            for row in range(1, self.n + 1)
        ]
        for row in board:
            print(" ".join(row))

    def solve(self, solver=None):
        self.encoding()
        if solver is None:
            solver = Glucose4()

        for clause in self.ctx.clauses:
            solver.add_clause(clause)
        solution = None
        if solver.solve():
            model = solver.get_model()
            solution = [
                (row, col) for (row, col), var in self.x.items() if var in model
            ]

        self.print_solution(solution)


if __name__ == "__main__":
    model = NQueens(4)
    model.solve()
