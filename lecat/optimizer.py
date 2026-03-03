"""Optimizer — Genetic Algorithm loop for LECAT strategy evolution.

Coordinates the full evolutionary pipeline:
  1. Initialize population (random strategies)
  2. Evaluate fitness (backtest + scoring)
  3. Select + Breed (tournament selection, crossover, mutation)
  4. Elitism (preserve top performers)
  5. Repeat for N generations

See docs/05_Integration_Strategy.md for design.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from lecat.ast_nodes import ASTNode, ast_to_string
from lecat.backtester import Backtester
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.evolution import Individual, crossover, mutate, tournament_selection
from lecat.fitness import FitnessResult, calculate_fitness
from lecat.generator import ExpressionGenerator
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib


@dataclass
class GenerationReport:
    """Statistics for a single generation."""

    generation: int
    best_fitness: float
    avg_fitness: float
    best_expression: str
    best_result: FitnessResult | None
    population_size: int
    elapsed_ms: float


@dataclass
class OptimizationResult:
    """Final result of the optimization run."""

    best_individual: Individual
    best_fitness_result: FitnessResult
    generations: list[GenerationReport]
    total_elapsed_ms: float


# Default configuration
DEFAULT_POPULATION_SIZE = 100
DEFAULT_GENERATIONS = 10
DEFAULT_ELITE_COUNT = 5
DEFAULT_MUTATION_RATE = 0.3
DEFAULT_CROSSOVER_RATE = 0.7
DEFAULT_TOURNAMENT_K = 3
DEFAULT_MAX_DEPTH = 3


class Optimizer:
    """Genetic Algorithm optimizer for LECAT strategy evolution.

    Usage:
        optimizer = Optimizer(context, seed=42)
        result = optimizer.run(generations=10)
        print(result.best_individual.expression)
    """

    def __init__(
        self,
        context: MarketContext,
        population_size: int = DEFAULT_POPULATION_SIZE,
        elite_count: int = DEFAULT_ELITE_COUNT,
        mutation_rate: float = DEFAULT_MUTATION_RATE,
        crossover_rate: float = DEFAULT_CROSSOVER_RATE,
        tournament_k: int = DEFAULT_TOURNAMENT_K,
        max_depth: int = DEFAULT_MAX_DEPTH,
        seed: int | None = None,
        verbose: bool = True,
    ) -> None:
        self._context = context
        self._population_size = population_size
        self._elite_count = elite_count
        self._mutation_rate = mutation_rate
        self._crossover_rate = crossover_rate
        self._tournament_k = tournament_k
        self._max_depth = max_depth
        self._verbose = verbose
        self._rng = random.Random(seed)

        # Initialize components
        self._registry = FunctionRegistry()
        register_std_lib(self._registry)
        self._evaluator = Evaluator(self._registry)
        self._backtester = Backtester(self._evaluator, self._registry)
        self._generator = ExpressionGenerator(
            self._registry, max_depth=max_depth, seed=seed
        )

    def run(self, generations: int = DEFAULT_GENERATIONS) -> OptimizationResult:
        """Run the full evolutionary optimization.

        Args:
            generations: Number of generations to evolve.

        Returns:
            OptimizationResult with the best strategy found.
        """
        total_start = time.perf_counter()
        reports: list[GenerationReport] = []

        if self._verbose:
            print(f"\n{'═' * 70}")
            print(f"  LECAT Evolutionary Optimizer")
            print(f"{'═' * 70}")
            print(f"  Population: {self._population_size}  |  Generations: {generations}")
            print(f"  Elite: {self._elite_count}  |  Mutation: {self._mutation_rate:.0%}")
            print(f"  Bars: {self._context.total_bars:,}")
            print(f"{'═' * 70}\n")

        # Step 1: Initialize population
        population = self._init_population()

        # Step 2: Evaluate initial population
        self._evaluate_population(population)

        for gen in range(generations):
            gen_start = time.perf_counter()

            # Sort by fitness (descending)
            population.sort(key=lambda ind: ind.fitness, reverse=True)

            # Report
            report = self._make_report(gen, population, gen_start)
            reports.append(report)

            if self._verbose:
                self._print_generation(report)

            # Step 3: Build next generation
            next_gen: list[Individual] = []

            # Elitism: keep top performers
            next_gen.extend(population[:self._elite_count])

            # Fill rest with offspring
            while len(next_gen) < self._population_size:
                child = self._breed(population)
                if child is not None:
                    next_gen.append(child)

            population = next_gen

            # Step 4: Evaluate new population (skip elites)
            self._evaluate_population(population[self._elite_count:])

        # Final sort and report
        population.sort(key=lambda ind: ind.fitness, reverse=True)
        gen_start = time.perf_counter()
        final_report = self._make_report(generations, population, gen_start)
        reports.append(final_report)

        if self._verbose:
            self._print_generation(final_report)

        # Get best individual's full fitness
        best = population[0]
        best_backtest = self._backtester.run(best.ast, self._context, expression=best.expression)
        best_fitness = calculate_fitness(best_backtest, self._context)

        total_elapsed = (time.perf_counter() - total_start) * 1000

        if self._verbose:
            print(f"\n{'─' * 70}")
            print(f"  Best Strategy: {best.expression}")
            print(f"  {best_fitness}")
            print(f"  Total time: {total_elapsed:.0f}ms")
            print(f"{'─' * 70}\n")

        return OptimizationResult(
            best_individual=best,
            best_fitness_result=best_fitness,
            generations=reports,
            total_elapsed_ms=total_elapsed,
        )

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _init_population(self) -> list[Individual]:
        """Generate initial random population."""
        population: list[Individual] = []
        for _ in range(self._population_size):
            try:
                expr = self._generator.generate(self._max_depth)
                tokens = Lexer(expr).tokenize()
                ast = Parser(tokens).parse()
                population.append(Individual(ast=ast, expression=expr))
            except Exception:
                continue

        # Fill any gaps
        while len(population) < self._population_size:
            try:
                expr = self._generator.generate(max_depth=1)
                tokens = Lexer(expr).tokenize()
                ast = Parser(tokens).parse()
                population.append(Individual(ast=ast, expression=expr))
            except Exception:
                continue

        return population

    def _evaluate_population(self, population: list[Individual]) -> None:
        """Run backtest and fitness scoring for each individual."""
        for ind in population:
            try:
                result = self._backtester.run(
                    ind.ast, self._context, expression=ind.expression
                )
                fitness = calculate_fitness(result, self._context)
                ind.fitness = fitness.fitness_score
            except Exception:
                ind.fitness = -999.0

    def _breed(self, population: list[Individual]) -> Individual | None:
        """Create a child via selection, crossover, and mutation."""
        try:
            # Select parents
            parent_a = tournament_selection(population, self._tournament_k, self._rng)
            parent_b = tournament_selection(population, self._tournament_k, self._rng)

            # Crossover
            if self._rng.random() < self._crossover_rate:
                child_ast = crossover(parent_a.ast, parent_b.ast, self._rng)
            else:
                child_ast = parent_a.ast

            # Mutation
            if self._rng.random() < self._mutation_rate:
                child_ast = mutate(child_ast, self._registry, self._rng, self._generator)

            # Serialize back to string and validate
            expr = ast_to_string(child_ast)
            tokens = Lexer(expr).tokenize()
            validated_ast = Parser(tokens).parse()

            return Individual(ast=validated_ast, expression=expr)
        except Exception:
            # If breeding fails, generate a fresh random individual
            try:
                expr = self._generator.generate(max_depth=1)
                tokens = Lexer(expr).tokenize()
                ast = Parser(tokens).parse()
                return Individual(ast=ast, expression=expr)
            except Exception:
                return None

    def _make_report(
        self, gen: int, population: list[Individual], start_time: float
    ) -> GenerationReport:
        """Create a generation statistics report."""
        fitnesses = [ind.fitness for ind in population if ind.fitness > -999]
        best = population[0] if population else None
        avg = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0

        best_result = None
        if best:
            try:
                bt = self._backtester.run(best.ast, self._context)
                best_result = calculate_fitness(bt, self._context)
            except Exception:
                pass

        return GenerationReport(
            generation=gen,
            best_fitness=best.fitness if best else 0.0,
            avg_fitness=avg,
            best_expression=best.expression if best else "",
            best_result=best_result,
            population_size=len(population),
            elapsed_ms=(time.perf_counter() - start_time) * 1000,
        )

    def _print_generation(self, report: GenerationReport) -> None:
        """Print generation summary."""
        display_expr = report.best_expression
        if len(display_expr) > 45:
            display_expr = display_expr[:42] + "..."

        fitness_detail = ""
        if report.best_result:
            r = report.best_result
            fitness_detail = f"ret={r.total_return_pct:+.1f}% trades={r.num_trades}"

        print(
            f"  Gen {report.generation:>3}  |  "
            f"best={report.best_fitness:>7.4f}  "
            f"avg={report.avg_fitness:>7.4f}  |  "
            f"{fitness_detail:<25}  {display_expr}"
        )
