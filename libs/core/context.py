from .var_pool import VarPool
from .cnf import CNF


class EncodingContext:
    def __init__(self):
        self.pool = VarPool()
        self.cnf = CNF()

    def var(self, *key):
        return self.pool.var(*key)

    def add_clause(self, *lits):
        self.cnf.add_clause(*lits)

    def add(self, clause):
        self.cnf.add(clause)

    def extend(self, clauses):
        self.cnf.extend(clauses)

    def explain(self, lit):
        return self.pool.explain(lit)

    @property
    def clauses(self):
        return self.cnf.clauses

    @property
    def num_vars(self):
        return self.pool.num_vars

    @property
    def num_clauses(self):
        return len(self.cnf)

    def clear(self):
        self.cnf.clear()