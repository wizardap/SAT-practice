class SATManager:
    def __init__(self, solver):
        self.solver = solver
        self.clauses = []
        self.vars = {}
        self.vars_count = 0
    
    def add_variable(self, name):
        self.vars_count += 1
        self.vars[name] = self.vars_count
        return self.vars_count
    
    def add_clause(self, clause):
        self.clauses.append(clause)
        self.solver.add_clause(clause)
    
    def solve(self):
        return self.solver.solve()