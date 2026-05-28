from .sat_manager import SATManager
class SCE:
    def __init__(self, sat_manager:SATManager):
        self.sat_manager = sat_manager
    
    def add_clause(self, clause:list):
        self.sat_manager.add_clause(clause)
    
    def new_counter_states(self, variables:list, K:int)->dict:
        registers = {}

        for i in range(len(variables)-1):
            for j in range(min(i+1,K)):
                var_name = f"sce_r_{i}_{j+1}"
                registers[(i,j)] = self.sat_manager.add_variable(var_name)

        return registers

    def amk(self, variables:list, K:int)->dict:
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

        registers = self.new_counter_states(variables,K)

        # Formula 1
        for i in range(n-1):
            self.add_clause([-variables[i],registers[(i,0)]])

        # Formula 2
        for i in range(1,n-1):
            for j in range(min(i,K)):
                self.add_clause([-registers[(i-1,j)],registers[(i,j)]])

        # Formula 3
        for i in range(1,n-1):
            for j in range(1,min(i+1,K)):
                self.add_clause([-variables[i],-registers[(i-1,j-1)],registers[(i,j)]])

        # Formula 8
        for i in range(K,n):
            self.add_clause([-variables[i],-registers[(i-1,K-1)]])

        return registers

    def alk(self, variables:list, K:int)->dict:
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

        registers = self.new_counter_states(variables,K)

        # Formula 1
        for i in range(n-1):
            self.add_clause([-variables[i],registers[(i,0)]])

        # Formula 2
        for i in range(1,n-1):
            for j in range(min(i,K)):
                self.add_clause([-registers[(i-1,j)],registers[(i,j)]])

        # Formula 3
        for i in range(1,n-1):
            for j in range(1,min(i+1,K)):
                self.add_clause([-variables[i],-registers[(i-1,j-1)],registers[(i,j)]])

        # Formula 4
        for i in range(1,n-1):
            for j in range(min(i,K)):
                self.add_clause([variables[i],registers[(i-1,j)],-registers[(i,j)]])

        # Formula 5
        for i in range(min(K,n-1)):
            self.add_clause([variables[i],-registers[(i,i)]])

        # Formula 6
        for i in range(1,n-1):
            for j in range(1,min(i+1,K)):
                self.add_clause([registers[(i-1,j-1)],-registers[(i,j)]])

        # Formula 7
        last_x = variables[-1]
        last_prefix = n-2
        if K == 1:
            self.add_clause([registers[(last_prefix,0)],last_x])
        else:
            self.add_clause([registers[(last_prefix,K-1)],last_x])
            self.add_clause([registers[(last_prefix,K-1)],registers[(last_prefix,K-2)]])

        return registers

    def exk(self, variables:list, K:int)->dict:
        return {
            "at_least": self.alk(variables,K),
            "at_most": self.amk(variables,K),
        }

    def range(self, variables:list, u:int, v:int)->dict:
        return {
            "lower": self.alk(variables,u),
            "upper": self.amk(variables,v),
        }
