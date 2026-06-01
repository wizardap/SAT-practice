class VarPool:
    def __init__(self):
        self.next_id = 1
        self.key_to_id = {}
        self.id_to_key = {}

    def var(self, *key):
        if key not in self.key_to_id:
            vid = self.next_id
            self.next_id += 1
            self.key_to_id[key] = vid
            self.id_to_key[vid] = key
        return self.key_to_id[key]

    def explain(self, lit):
        sign = "" if lit > 0 else "¬"
        key = self.id_to_key[abs(lit)]
        return f"{sign}{key}"
    
    @property
    def num_vars(self):
        return self.next_id - 1