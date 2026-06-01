from libs.constraints.SCE import SCE
from libs.constraints.SCLE import ladder_at_most_k
from libs.core.context import EncodingContext


class NurseRosteringProblem:
    """Nurse rostering model encoded with libs/core and libs/constraints."""

    SHIFTS = ("D", "E", "N", "O")

    def __init__(self, nurse_count: int, day_count: int, ctx=None):
        if nurse_count <= 0:
            raise ValueError("nurse_count must be positive")
        if day_count <= 0:
            raise ValueError("day_count must be positive")

        self.nurse_count = nurse_count
        self.day_count = day_count
        self.ctx = ctx or EncodingContext()
        self.sce = SCE(self.ctx, name="nrp_sce")
        self.x = {}
        self._sliding_id = 0
        self._model = None

        self._create_decision_variables()

    @property
    def clauses(self):
        return self.ctx.clauses

    @property
    def num_vars(self):
        return self.ctx.num_vars

    @property
    def num_clauses(self):
        return self.ctx.num_clauses

    def _create_decision_variables(self):
        for nurse in range(1, self.nurse_count + 1):
            for day in range(1, self.day_count + 1):
                for shift in self.SHIFTS:
                    self.x[(nurse, day, shift)] = self.ctx.var("x", nurse, day, shift)

    def _add_clause(self, clause):
        self.ctx.add_clause(*clause)

    def _next_sliding_name(self, prefix):
        self._sliding_id += 1
        return f"nrp_{prefix}_{self._sliding_id}"

    def shift_var(self, nurse: int, day: int, shift: str) -> int:
        return self.x[(nurse, day, shift)]

    def day_vars(self, nurse: int, day: int) -> list[int]:
        return [self.shift_var(nurse, day, shift) for shift in self.SHIFTS]

    def shift_sequence(self, nurse: int, shift: str) -> list[int]:
        return [
            self.shift_var(nurse, day, shift)
            for day in range(1, self.day_count + 1)
        ]

    def evening_night_sequence(self, nurse: int) -> list[int]:
        literals = []
        for day in range(1, self.day_count + 1):
            literals.append(self.shift_var(nurse, day, "E"))
            literals.append(self.shift_var(nurse, day, "N"))
        return literals

    def shift_coverage(self, day: int, shift: str) -> list[int]:
        return [
            self.shift_var(nurse, day, shift)
            for nurse in range(1, self.nurse_count + 1)
        ]

    def add_at_least(self, literals: list[int], lower: int):
        if lower <= 0:
            return
        if lower > len(literals):
            self._add_clause([])
            return
        self.sce.alk(literals, lower)

    def add_at_most(self, literals: list[int], upper: int):
        if upper < 0:
            self._add_clause([])
            return
        if upper >= len(literals):
            return
        self.sce.amk(literals, upper)

    def add_exactly(self, literals: list[int], count: int):
        self.add_at_least(literals, count)
        self.add_at_most(literals, count)

    def add_sliding_at_most(self, literals: list[int], width: int, upper: int):
        if width <= 0:
            raise ValueError("width must be positive")
        if len(literals) < width or upper >= width:
            return
        if upper < 0:
            self._add_clause([])
            return
        if upper == 0:
            for literal in literals:
                self._add_clause([-literal])
            return
        name = self._next_sliding_name("amk")
        ladder_at_most_k(self.ctx, literals, width, upper, name=name)

    def add_sliding_at_least(self, literals: list[int], width: int, lower: int):
        if width <= 0:
            raise ValueError("width must be positive")
        if len(literals) < width or lower <= 0:
            return
        if lower > width:
            self._add_clause([])
            return
        if lower == width:
            for literal in literals:
                self._add_clause([literal])
            return
        self.add_sliding_at_most([-literal for literal in literals], width, width - lower)

    def add_daily_coverage(self, min_demand=None, max_demand=None):
        min_demand = min_demand or {}
        max_demand = max_demand or {}

        for day in range(1, self.day_count + 1):
            for shift, lower in min_demand.items():
                self.add_at_least(self.shift_coverage(day, shift), lower)
            for shift, upper in max_demand.items():
                self.add_at_most(self.shift_coverage(day, shift), upper)

    def add_constraints_for_nurse(self, nurse: int):
        off = self.shift_sequence(nurse, "O")
        evening = self.shift_sequence(nurse, "E")
        night = self.shift_sequence(nurse, "N")

        # (1) sum_{s in {D,E,N,O}} x_{i,t,s} = 1.
        for day in range(1, self.day_count + 1):
            self.add_exactly(self.day_vars(nurse, day), 1)

        # (2) sum_{t=j}^{j+6} not O <= 6 <=> sum O >= 1.
        self.add_sliding_at_least(off, 7, 1)

        # (3) sum_{t=j}^{j+13} O >= 4.
        self.add_sliding_at_least(off, 14, 4)

        # (4) sum_{t=j}^{j+13} E >= 4.
        self.add_sliding_at_least(evening, 14, 4)

        # (5) sum_{t=j}^{j+13} E <= 8.
        self.add_sliding_at_most(evening, 14, 8)

        # (6) sum working >= 20 <=> sum O <= 8 over every 28 days.
        self.add_sliding_at_most(off, 28, 8)

        # (7) sum_{t=j}^{j+13} N <= 4.
        self.add_sliding_at_most(night, 14, 4)

        # (8) sum_{t=j}^{j+13} N >= 1.
        self.add_sliding_at_least(night, 14, 1)

        evening_night = self.evening_night_sequence(nurse)
        # (9) sum_{t=j}^{j+6} E/N >= 2.
        self.add_sliding_at_least(evening_night, 14, 2)

        # (10) sum_{t=j}^{j+6} E/N <= 4.
        self.add_sliding_at_most(evening_night, 14, 4)

        # (11) sum_{t=j}^{j+1} N <= 1.
        self.add_sliding_at_most(night, 2, 1)

    def add_constraints(self, min_demand=None, max_demand=None):
        for nurse in range(1, self.nurse_count + 1):
            self.add_constraints_for_nurse(nurse)

        self.add_daily_coverage(min_demand=min_demand, max_demand=max_demand)
        return self

    def solve(self, solver_cls=None) -> bool:
        if solver_cls is None:
            try:
                from pysat.solvers import Glucose4
            except ImportError as exc:
                raise ImportError(
                    "Solving requires python-sat. Install it or pass a compatible "
                    "solver class to solve(solver_cls=...)."
                ) from exc
            solver_cls = Glucose4

        with solver_cls(bootstrap_with=self.clauses) as solver:
            is_sat = solver.solve()
            self._model = solver.get_model() if is_sat else None

        return is_sat

    def model(self) -> list[int] | None:
        if not self.solve():
            return None
        return self._model

    def schedule(self) -> list[list[str]] | None:
        model = self.model()
        if model is None:
            return None

        positive = {literal for literal in model if literal > 0}
        schedule = []
        for nurse in range(1, self.nurse_count + 1):
            row = []
            for day in range(1, self.day_count + 1):
                row.append(
                    next(
                        shift for shift in self.SHIFTS
                        if self.shift_var(nurse, day, shift) in positive
                    )
                )
            schedule.append(row)
        return schedule


def solve_nrp(nurse_count=10, day_count=28, min_demand=None, max_demand=None):
    nrp = NurseRosteringProblem(nurse_count, day_count).add_constraints(
        min_demand=min_demand,
        max_demand=max_demand,
    )
    return nrp, nrp.schedule()


def count_windows(row: list[str], width: int, predicate) -> list[int]:
    return [
        sum(1 for shift in row[start:start + width] if predicate(shift))
        for start in range(len(row) - width + 1)
    ]


def validate_nrp_schedule(schedule, day_count, min_demand=None, max_demand=None):
    checks = []
    min_demand = min_demand or {}
    max_demand = max_demand or {}

    for nurse_id, row in enumerate(schedule, start=1):
        checks.append((
            f"Nurse {nurse_id}: (1) exactly one status per day",
            len(row) == day_count
            and all(shift in NurseRosteringProblem.SHIFTS for shift in row),
        ))

        if day_count >= 7:
            checks.append((f"Nurse {nurse_id}: (2) >= 1 O / 7", all(v >= 1 for v in count_windows(row, 7, lambda s: s == "O"))))
            checks.append((f"Nurse {nurse_id}: (9) >= 2 E/N / 7", all(v >= 2 for v in count_windows(row, 7, lambda s: s in {"E", "N"}))))
            checks.append((f"Nurse {nurse_id}: (10) <= 4 E/N / 7", all(v <= 4 for v in count_windows(row, 7, lambda s: s in {"E", "N"}))))

        if day_count >= 14:
            checks.append((f"Nurse {nurse_id}: (3) >= 4 O / 14", all(v >= 4 for v in count_windows(row, 14, lambda s: s == "O"))))
            checks.append((f"Nurse {nurse_id}: (4) >= 4 E / 14", all(v >= 4 for v in count_windows(row, 14, lambda s: s == "E"))))
            checks.append((f"Nurse {nurse_id}: (5) <= 8 E / 14", all(v <= 8 for v in count_windows(row, 14, lambda s: s == "E"))))
            checks.append((f"Nurse {nurse_id}: (7) <= 4 N / 14", all(v <= 4 for v in count_windows(row, 14, lambda s: s == "N"))))
            checks.append((f"Nurse {nurse_id}: (8) >= 1 N / 14", all(v >= 1 for v in count_windows(row, 14, lambda s: s == "N"))))

        if day_count >= 28:
            checks.append((f"Nurse {nurse_id}: (6) >= 20 working / 28", all(v >= 20 for v in count_windows(row, 28, lambda s: s != "O"))))

        checks.append((
            f"Nurse {nurse_id}: (11) no consecutive N",
            all(not (row[d] == "N" and row[d + 1] == "N") for d in range(len(row) - 1)),
        ))

    for day in range(day_count):
        for shift, lower in min_demand.items():
            count = sum(row[day] == shift for row in schedule)
            checks.append((f"Day {day + 1}: >= {lower} {shift}", count >= lower))
        for shift, upper in max_demand.items():
            count = sum(row[day] == shift for row in schedule)
            checks.append((f"Day {day + 1}: <= {upper} {shift}", count <= upper))

    return checks
