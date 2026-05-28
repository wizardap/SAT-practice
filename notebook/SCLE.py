from .sat_manager import SATManager


class SCLE:
    def __init__(self, sat_manager: SATManager):
        self.sat_manager = sat_manager

    def add_clause(self, clause: list):
        self.sat_manager.add_clause(clause)

    def create_subsets(self, variables: list, w: int) -> list:
        subsets = [[0]]
        vars = [
            0
        ] + variables  # Add a dummy variable at the beginning of the list to make it 1-indexed
        n = len(vars) - 1
        for i in range(1, n + 1, w):
            if i + w > n:
                subset = vars[i:]
            else:
                subset = vars[i : i + w]
            subsets.append(subset)
        return subsets

    def create_block(
        self, block_id: int, subset: list, K: int, w: int, is_AMK: bool = True
    ) -> list:
        registers = [[0 for _ in range(K + 1)]]
        vars = [
            0
        ] + subset  # Add a dummy variable at the beginning of the list to make it 1-indexed
        w_i = len(vars) - 1
        limit = w_i + 1 if w_i < w else w
        for j in range(1, limit):  # Create the first w_i-1 rows of the block
            register = [
                0
            ]  # Add a dummy variable at the beginning of the row to make it 1-indexed
            for s in range(
                1, min(j, K) + 1
            ):  # Create the first min(j,K) columns of the block:
                var_name = f"r_{block_id}_{j}_{s}"
                var_id = self.sat_manager.add_variable(var_name)
                register.append(var_id)
            registers.append(register)

        # Formula 1
        for j in range(1, w_i):
            self.add_clause([-vars[j], registers[j][1]])

        # Formula 2
        for j in range(2, w_i):
            for s in range(1, min(j - 1, K) + 1):
                self.add_clause([-registers[j - 1][s], registers[j][s]])

        # Formula 3
        for j in range(2, w_i):
            for s in range(2, min(j, K) + 1):
                self.add_clause([-vars[j], -registers[j - 1][s - 1], registers[j][s]])

        # Formula 4
        for j in range(1, min(K, w_i) + 1):
            self.add_clause([vars[j], -registers[j][j]])

        # Formula 5
        for j in range(2, w_i):
            for s in range(2, min(j, K) + 1):
                self.add_clause([registers[j - 1][s - 1], -registers[j][s]])

        # Formula 6
        for j in range(2, w_i):
            for s in range(1, min(j - 1, K) + 1):
                self.add_clause([vars[j], registers[j - 1][s], -registers[j][s]])

        # Formula 7
        if is_AMK:
            for j in range(K + 1, w_i + 1):
                self.add_clause([-vars[j], -registers[j - 1][K]])

        return registers

    def create_blocks(self, subsets: list[list], w: int, K: int) -> list:
        blocks = [
            None
        ]  # Add a dummy block at the beginning of the list to make it 1-indexed

        if len(subsets) == 2:
            blocks.append(
                self.create_block(1, list(reversed(subsets[1])), K, w, is_AMK=True)
            )
            return blocks

        blocks.append(
            self.create_block(1, list(reversed(subsets[1])), K, w, is_AMK=True)
        )

        for i in range(2, len(subsets) - 1):
            LR_subset = subsets[i].copy()
            blocks.append(self.create_block(len(blocks), LR_subset, K, w, is_AMK=True))

            RL_subset = list(reversed(LR_subset))
            blocks.append(self.create_block(len(blocks), RL_subset, K, w, is_AMK=False))

        blocks.append(self.create_block(len(blocks), subsets[-1], K, w, is_AMK=True))

        return blocks

    def block_to_subset_index(self, block_index: int) -> int:
        return (block_index + 2) // 2

    def connect_blocks(self, blocks: list, subsets: list, w: int, K: int):
        M = len(subsets) - 1
        blocks_count = len(blocks) - 1  # iff 2*(M-1)+1 == blocks_count
        for i in range(1, 2 * (M - 1) + 1, 2):
            RL_subset_index = self.block_to_subset_index(i)
            LR_subset_index = self.block_to_subset_index(i + 1)

            w_i_LR = len(subsets[LR_subset_index])
            w_i_RL = len(subsets[RL_subset_index])
            w_i = min(w_i_LR + 1, w_i_RL)
            for j in range(2, w_i + 1):
                for p in range(1, K + 1):
                    left_len = w - j + 1
                    right_len = j - 1

                    left_threshold = K - p + 1
                    right_threshold = p

                    if left_threshold > left_len or right_threshold > right_len:
                        continue

                    self.add_clause(
                        [
                            -blocks[i][left_len][left_threshold],
                            -blocks[i + 1][right_len][right_threshold],
                        ]
                    )

    def amksc(self, variables, w, K):
        if not 1 < w <= len(variables):
            raise ValueError("w must be in the range [2,n]")

        if not (1 <= K < w):
            raise ValueError("K must be in the range [1,w-1]")
        subsets = self.create_subsets(variables, w)
        blocks = self.create_blocks(subsets, w, K)
        self.connect_blocks(blocks, subsets, w, K)

    def alksc(self, variables, w, K):
        if not 1 <= K <= w:
            raise ValueError("K must be in the range [1,w]")

        new_K = w - K
        neg_variables = [-v for v in variables]

        if new_K == 0:
            for x in neg_variables:
                self.add_clause([-x])  # tức add_clause([original x])
            return

        self.amksc(neg_variables, w, new_K)
