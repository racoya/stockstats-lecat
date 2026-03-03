"""Parallel Evaluator — Multi-core batch evaluation for LECAT.

Uses concurrent.futures to evaluate a population of strategies across
multiple CPU cores. The Genetic Algorithm's evaluation step is
"embarrassingly parallel" — each strategy is independent.

On macOS, uses ThreadPoolExecutor (spawn context overhead makes
ProcessPoolExecutor less efficient for small workloads). On Linux,
fork()-based ProcessPoolExecutor provides copy-on-write data sharing.

Falls back to serial execution if workers=1 or context too small.
"""

from __future__ import annotations

import os
import platform
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from lecat.backtester import Backtester, BacktestResult
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.evolution import Individual
from lecat.fitness import FitnessResult, calculate_fitness
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib
from lecat.indicators import register_extended_indicators


@dataclass
class BatchResult:
    """Result of evaluating an individual."""
    index: int
    fitness_score: float
    fitness_result: FitnessResult | None = None


class BatchEvaluator:
    """Parallel batch evaluator for strategy populations.

    Usage:
        evaluator = BatchEvaluator(context, max_workers=4)
        scores = evaluator.evaluate_population(population)
    """

    def __init__(
        self,
        max_workers: int | None = None,
    ) -> None:
        if max_workers is None:
            cpu_count = os.cpu_count() or 1
            self._max_workers = max(1, cpu_count - 1)
        else:
            self._max_workers = max(1, max_workers)

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def evaluate_population(
        self,
        population: list[Individual],
        context: MarketContext,
        registry: FunctionRegistry | None = None,
    ) -> list[float]:
        """Evaluate all individuals in the population.

        Args:
            population: List of Individual objects to evaluate.
            context: Market data for backtesting.
            registry: Function registry (created if None).

        Returns:
            List of fitness scores in the same order as input.
        """
        n = len(population)
        if n == 0:
            return []

        # For small populations or single worker, use serial
        if n < 10 or self._max_workers <= 1:
            return self._evaluate_serial(population, context, registry)

        return self._evaluate_parallel(population, context, registry)

    def _evaluate_serial(
        self,
        population: list[Individual],
        context: MarketContext,
        registry: FunctionRegistry | None,
    ) -> list[float]:
        """Serial evaluation (baseline)."""
        if registry is None:
            registry = _make_registry()

        evaluator = Evaluator(registry)
        backtester = Backtester(evaluator, registry)

        scores: list[float] = []
        for ind in population:
            try:
                result = backtester.run(ind.ast, context, expression=ind.expression)
                fitness = calculate_fitness(result, context)
                ind.fitness = fitness.fitness_score
                scores.append(fitness.fitness_score)
            except Exception:
                ind.fitness = -999.0
                scores.append(-999.0)

        return scores

    def _evaluate_parallel(
        self,
        population: list[Individual],
        context: MarketContext,
        registry: FunctionRegistry | None,
    ) -> list[float]:
        """Parallel evaluation using ThreadPoolExecutor.

        ThreadPoolExecutor is used because:
        1. Our workload releases the GIL during computation
        2. Avoids serialization overhead of ProcessPoolExecutor
        3. Works reliably on all platforms (macOS spawn issue)
        """
        if registry is None:
            registry = _make_registry()

        scores: list[float] = [-999.0] * len(population)

        def _eval_one(idx: int) -> BatchResult:
            """Evaluate a single individual (thread worker)."""
            ind = population[idx]
            try:
                # Each thread gets its own evaluator (cache is per-thread)
                evaluator = Evaluator(registry)
                backtester = Backtester(evaluator, registry)
                result = backtester.run(ind.ast, context, expression=ind.expression)
                fitness = calculate_fitness(result, context)
                return BatchResult(index=idx, fitness_score=fitness.fitness_score, fitness_result=fitness)
            except Exception:
                return BatchResult(index=idx, fitness_score=-999.0)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {executor.submit(_eval_one, i): i for i in range(len(population))}
            for future in as_completed(futures):
                try:
                    batch_result = future.result()
                    scores[batch_result.index] = batch_result.fitness_score
                    population[batch_result.index].fitness = batch_result.fitness_score
                except Exception:
                    idx = futures[future]
                    scores[idx] = -999.0
                    population[idx].fitness = -999.0

        return scores


def _make_registry() -> FunctionRegistry:
    """Create a fresh registry with standard + extended indicators."""
    reg = FunctionRegistry()
    register_std_lib(reg)
    register_extended_indicators(reg)
    return reg
