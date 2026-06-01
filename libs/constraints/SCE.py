class SCE:
    """Sequential counter encoding for cardinality constraints.

    Uses libs/core through EncodingContext:
        ctx.var(...)
        ctx.add_clause(...)
    """

    def __init__(self, ctx, name="sce"):
        self.ctx = ctx
        self.name = name
        self._encoding_id = 0

    def add_clause(self, clause):
        self.ctx.add_clause(*clause)

    def _next_encoding_id(self):
        self._encoding_id += 1
        return self._encoding_id

    def new_counter_states(self, variables, K, encoding_id=None):
        registers = {}
        if encoding_id is None:
            encoding_id = self._next_encoding_id()

        for i in range(len(variables) - 1):
            for j in range(min(i + 1, K)):
                registers[(i, j)] = self.ctx.var(
                    "sce_r", self.name, encoding_id, i, j + 1
                )

        return registers

    def amk(self, variables, K):
        variables = list(variables)
        n = len(variables)

        if K < 0:
            self.add_clause([])
            return {}

        if K >= n:
            return {}

        if K == 0:
            for x in variables:
                self.add_clause([-x])
            return {}

        registers = self.new_counter_states(variables, K)

        # Formula 1
        for i in range(n - 1):
            self.add_clause([-variables[i], registers[(i, 0)]])

        # Formula 2
        for i in range(1, n - 1):
            for j in range(min(i, K)):
                self.add_clause([-registers[(i - 1, j)], registers[(i, j)]])

        # Formula 3
        for i in range(1, n - 1):
            for j in range(1, min(i + 1, K)):
                self.add_clause(
                    [-variables[i], -registers[(i - 1, j - 1)], registers[(i, j)]]
                )

        # Formula 8
        for i in range(K, n):
            self.add_clause([-variables[i], -registers[(i - 1, K - 1)]])

        return registers

    def alk(self, variables, K):
        variables = list(variables)
        n = len(variables)

        if K <= 0:
            return {}

        if K > n:
            self.add_clause([])
            return {}

        if K == n:
            for x in variables:
                self.add_clause([x])
            return {}

        registers = self.new_counter_states(variables, K)

        # Formula 1
        for i in range(n - 1):
            self.add_clause([-variables[i], registers[(i, 0)]])

        # Formula 2
        for i in range(1, n - 1):
            for j in range(min(i, K)):
                self.add_clause([-registers[(i - 1, j)], registers[(i, j)]])

        # Formula 3
        for i in range(1, n - 1):
            for j in range(1, min(i + 1, K)):
                self.add_clause(
                    [-variables[i], -registers[(i - 1, j - 1)], registers[(i, j)]]
                )

        # Formula 4
        for i in range(1, n - 1):
            for j in range(min(i, K)):
                self.add_clause([variables[i], registers[(i - 1, j)], -registers[(i, j)]])

        # Formula 5
        for i in range(min(K, n - 1)):
            self.add_clause([variables[i], -registers[(i, i)]])

        # Formula 6
        for i in range(1, n - 1):
            for j in range(1, min(i + 1, K)):
                self.add_clause([registers[(i - 1, j - 1)], -registers[(i, j)]])

        # Formula 7
        last_x = variables[-1]
        last_prefix = n - 2
        if K == 1:
            self.add_clause([registers[(last_prefix, 0)], last_x])
        else:
            self.add_clause([registers[(last_prefix, K - 1)], last_x])
            self.add_clause([registers[(last_prefix, K - 1)], registers[(last_prefix, K - 2)]])

        return registers

    def exk(self, variables, K):
        return {
            "at_least": self.alk(variables, K),
            "at_most": self.amk(variables, K),
        }

    def range(self, variables, u, v):
        return {
            "lower": self.alk(variables, u),
            "upper": self.amk(variables, v),
        }


def at_most_k(ctx, variables, K, name="sce"):
    return SCE(ctx, name=name).amk(variables, K)


def at_least_k(ctx, variables, K, name="sce"):
    return SCE(ctx, name=name).alk(variables, K)


def exactly_k(ctx, variables, K, name="sce"):
    return SCE(ctx, name=name).exk(variables, K)


def range_k(ctx, variables, u, v, name="sce"):
    return SCE(ctx, name=name).range(variables, u, v)
