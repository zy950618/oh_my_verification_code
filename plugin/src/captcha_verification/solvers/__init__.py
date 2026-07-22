from __future__ import annotations

from .press import PressSolver
from .protocols import Solver
from .reference import ClickSolver, RotateSolver, SliderSolver, solve
from .text import TextSolver
from .tiles import TilesSolver

__all__ = ["ClickSolver", "PressSolver", "RotateSolver", "SliderSolver", "Solver", "TextSolver", "TilesSolver", "solve"]
