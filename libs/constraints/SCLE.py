class LadderAMK:
    """SCL ladder encoding for sliding-window At-Most-K constraints.

    Uses libs/core through EncodingContext:
        ctx.var(...)
        ctx.add_clause(...)
    """

    def __init__(self, variables, w, K, name="ladder_amk"):
        self.variables = list(variables)
        self.w = w
        self.K = K
        self.name = name
        self.ctx = None
        self.subsets = None
        self._R = None

    def encode(self, ctx):
        if not 1 < self.w <= len(self.variables):
            raise ValueError("w must be in the range [2, len(variables)]")
        if not 1 <= self.K < self.w:
            raise ValueError("K must be in the range [1, w - 1]")

        self.ctx = ctx
        self.subsets = self.create_subsets()
        self._R = self.create_blocks()
        self.connect_blocks()
        return self

    def add_clause(self, clause):
        self.ctx.add_clause(*clause)

    def new_register(self, block_id, row, col):
        return self.ctx.var("ladder", self.name, block_id, row, col)

    def R(self, block_id, row, col):
        """Return the SAT literal for R_{block_id,row,col}."""
        if self._R is None:
            raise RuntimeError("encode(ctx) must be called before accessing R")

        if not 1 <= block_id < len(self._R):
            raise ValueError(f"block_id must be in the range [1, {len(self._R) - 1}]")

        block = self._R[block_id]
        if not 1 <= row < len(block):
            raise ValueError(f"row must be in the range [1, {len(block) - 1}]")

        if not 1 <= col < len(block[row]):
            raise ValueError(f"col must be in the range [1, {len(block[row]) - 1}]")

        return block[row][col]

    @property
    def registers(self):
        if self._R is None:
            raise RuntimeError("encode(ctx) must be called before accessing registers")
        return self._R

    def create_subsets(self):
        subsets = [[0]]
        variables = [0] + self.variables
        n = len(variables) - 1

        for i in range(1, n + 1, self.w):
            if i + self.w > n:
                subset = variables[i:]
            else:
                subset = variables[i : i + self.w]
            subsets.append(subset)

        return subsets

    def create_block(self, block_id, subset, is_AMK=True):
        registers = [[0 for _ in range(self.K + 1)]]
        variables = [0] + subset
        w_i = len(variables) - 1
        limit = w_i + 1 if w_i < self.w else self.w

        for row in range(1, limit):
            register = [0]
            for col in range(1, min(row, self.K) + 1):
                register.append(self.new_register(block_id, row, col))
            registers.append(register)

        # Formula 1
        for row in range(1, limit):
            self.add_clause([-variables[row], registers[row][1]])

        # Formula 2
        for row in range(2, limit):
            for col in range(1, min(row - 1, self.K) + 1):
                self.add_clause([-registers[row - 1][col], registers[row][col]])

        # Formula 3
        for row in range(2, limit):
            for col in range(2, min(row, self.K) + 1):
                self.add_clause(
                    [-variables[row], -registers[row - 1][col - 1], registers[row][col]]
                )

        # Formula 4
        for row in range(1, min(self.K, w_i) + 1):
            self.add_clause([variables[row], -registers[row][row]])

        # Formula 5
        for row in range(2, limit):
            for col in range(2, min(row, self.K) + 1):
                self.add_clause([registers[row - 1][col - 1], -registers[row][col]])

        # Formula 6
        for row in range(2, limit):
            for col in range(1, min(row - 1, self.K) + 1):
                self.add_clause([variables[row], registers[row - 1][col], -registers[row][col]])

        # Formula 7
        if is_AMK:
            for row in range(self.K + 1, w_i + 1):
                self.add_clause([-variables[row], -registers[row - 1][self.K]])

        return registers

    def create_blocks(self):
        blocks = [None]

        if len(self.subsets) == 2:
            blocks.append(
                self.create_block(1, list(reversed(self.subsets[1])), is_AMK=True)
            )
            return blocks

        blocks.append(self.create_block(1, list(reversed(self.subsets[1])), is_AMK=True))

        for i in range(2, len(self.subsets) - 1):
            lr_subset = self.subsets[i].copy()
            blocks.append(self.create_block(len(blocks), lr_subset, is_AMK=True))

            rl_subset = list(reversed(lr_subset))
            blocks.append(self.create_block(len(blocks), rl_subset, is_AMK=False))

        blocks.append(self.create_block(len(blocks), self.subsets[-1], is_AMK=True))
        return blocks

    def block_to_subset_index(self, block_index):
        return (block_index + 2) // 2

    def connect_blocks(self):
        m = len(self.subsets) - 1

        for block in range(1, 2 * (m - 1) + 1, 2):
            rl_subset_index = self.block_to_subset_index(block)
            lr_subset_index = self.block_to_subset_index(block + 1)

            w_i_lr = len(self.subsets[lr_subset_index])
            w_i_rl = len(self.subsets[rl_subset_index])
            w_i = min(w_i_lr + 1, w_i_rl)

            for row in range(2, w_i + 1):
                for p in range(1, self.K + 1):
                    left_len = self.w - row + 1
                    right_len = row - 1
                    left_threshold = self.K - p + 1
                    right_threshold = p

                    if left_threshold > left_len or right_threshold > right_len:
                        continue

                    self.add_clause(
                        [
                            -self.R(block, left_len, left_threshold),
                            -self.R(block + 1, right_len, right_threshold),
                        ]
                    )


def ladder_at_most_k(ctx, variables, w, K, name="ladder_amk"):
    return LadderAMK(variables, w, K, name=name).encode(ctx)
