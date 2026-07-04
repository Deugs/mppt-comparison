"""Partial-shading test scenarios (CLAUDE.md scenarios 6 and 7).

Separate from scenarios.py because these drive a multi-module `PVString`
through `simulate.pv_string_operating_point` instead of a single
`TwoDiodeModel` through `simulate.pv_operating_point` -- and because the
reference "theoretical max power" needs `PVString.find_global_mpp`'s dense
sweep rather than `TwoDiodeModel.find_mpp`'s bounded unimodal search, since
bypass-diode partial shading is exactly what creates multiple local maxima
for that search to get stuck on.

Both scenarios here are steady-state (the shading pattern is fixed for the
whole run, matching CLAUDE.md's scenario definitions, which give a shading
configuration but no time-varying profile) -- so PVModuleGroup's per-
(irradiance, temperature) cache (see pv_model.py) turns almost all of the
per-sample cost into a single root-find per bypass group, not three.
"""

import random
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from . import config
from .pv_model import PVModule, PVString
from .scenarios import RunResult
from .simulate import pv_string_operating_point


@dataclass
class PartialShadingScenario:
    name: str
    duration_s: float
    irradiances: List[float]  # per module, static for the whole run
    temperature_c: float = config.STC_TEMPERATURE_C


def build_pv_string(params, num_modules: int) -> PVString:
    """A PVString of `num_modules` identical-parameter modules, differing
    only in the per-module irradiance passed at call time."""
    return PVString([PVModule(params) for _ in range(num_modules)])


def run_partial_shading_scenario(
    scenario: PartialShadingScenario,
    algorithm,
    pv_string: PVString,
    initial_duty: float = 0.3,
    sample_period_s: float = config.PARTIAL_SHADING_SAMPLE_PERIOD_S,
    theoretical_max_power: Optional[float] = None,
) -> RunResult:
    """Drive `algorithm` through a fixed partial-shading pattern.

    Reuse the *same* `pv_string` instance across repeated calls (e.g. across
    Monte Carlo runs) so PVModuleGroup's Isc/Voc cache actually hits --
    constructing a fresh PVString per run would defeat it.
    """
    n_samples = int(round(scenario.duration_s / sample_period_s)) + 1
    times = np.arange(n_samples) * sample_period_s

    algorithm.reset()
    duty = initial_duty
    voltages = np.empty(n_samples)
    currents = np.empty(n_samples)
    powers = np.empty(n_samples)
    duty_cycles = np.empty(n_samples)

    for idx, t in enumerate(times):
        v, i = pv_string_operating_point(
            pv_string, duty, scenario.irradiances, temperature_c=scenario.temperature_c
        )
        voltages[idx] = v
        currents[idx] = i
        powers[idx] = v * i
        duty_cycles[idx] = duty
        duty = algorithm.step(v, i, duty)

    if theoretical_max_power is None:
        _, theoretical_max_power = pv_string.find_global_mpp(scenario.irradiances, scenario.temperature_c)
    theoretical_max_powers = np.full(n_samples, theoretical_max_power)

    return RunResult(times, voltages, currents, powers, theoretical_max_powers, duty_cycles)


def run_partial_shading_monte_carlo(
    scenario: PartialShadingScenario,
    algorithm,
    pv_string: PVString,
    num_runs: int = config.MONTE_CARLO_RUNS,
    base_seed: int = 0,
    sample_period_s: float = config.PARTIAL_SHADING_SAMPLE_PERIOD_S,
) -> List[RunResult]:
    """Same seeding contract as scenarios.run_monte_carlo: run k always uses
    seed `base_seed + k`, so all algorithms see the same initial-duty sequence."""
    _, theoretical_max_power = pv_string.find_global_mpp(scenario.irradiances, scenario.temperature_c)

    results = []
    for run_id in range(num_runs):
        rng = random.Random(base_seed + run_id)
        initial_duty = rng.uniform(config.MPPT_DUTY_MIN + 0.05, config.MPPT_DUTY_MAX - 0.05)
        result = run_partial_shading_scenario(
            scenario,
            algorithm,
            pv_string,
            initial_duty=initial_duty,
            sample_period_s=sample_period_s,
            theoretical_max_power=theoretical_max_power,
        )
        results.append(result)
    return results


# --- Scenario definitions (CLAUDE.md scenarios 6 and 7) ---


def scenario_partial_shading_simple() -> PartialShadingScenario:
    return PartialShadingScenario(
        name="partial_shading_simple",
        duration_s=2.0,
        irradiances=[1000.0, 400.0],
    )


def scenario_partial_shading_complex_pattern_a() -> PartialShadingScenario:
    return PartialShadingScenario(
        name="partial_shading_complex_pattern_a",
        duration_s=2.0,
        irradiances=[1000.0, 800.0, 600.0],
    )


def scenario_partial_shading_complex_pattern_b() -> PartialShadingScenario:
    return PartialShadingScenario(
        name="partial_shading_complex_pattern_b",
        duration_s=2.0,
        irradiances=[1000.0, 500.0, 300.0],
    )


def scenario_partial_shading_complex_pattern_c() -> PartialShadingScenario:
    return PartialShadingScenario(
        name="partial_shading_complex_pattern_c",
        duration_s=2.0,
        irradiances=[1000.0, 1000.0, 400.0],
    )


PARTIAL_SHADING_SCENARIOS = {
    "partial_shading_simple": scenario_partial_shading_simple,
    "partial_shading_complex_pattern_a": scenario_partial_shading_complex_pattern_a,
    "partial_shading_complex_pattern_b": scenario_partial_shading_complex_pattern_b,
    "partial_shading_complex_pattern_c": scenario_partial_shading_complex_pattern_c,
}
