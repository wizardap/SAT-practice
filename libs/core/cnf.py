class CNF:
    def __init__(self):
        self._clauses = []

    def add_clause(self, *lits):
        self._clauses.append(list(lits))

    def add(self, clause):
        self._clauses.append(list(clause))

    def extend(self, clauses):
        self._clauses.extend(clauses)

    def __iter__(self):
        return iter(self._clauses)

    def __len__(self):
        return len(self._clauses)

    @property
    def clauses(self):
        return self._clauses

    def clear(self):
        self._clauses.clear()