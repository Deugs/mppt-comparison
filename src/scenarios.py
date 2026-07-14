"""Unified test-scenario runner (CLAUDE.md "Test Scenarios" section).

Every scenario is just a time-varying irradiance/temperature profile (plus
an optional sensor-noise level); `run_scenario` drives any MPPTAlgorithm
through one via the same loop, without special-casing per algorithm --
CLAUDE.md's "Unified Interface" requirement.

Partial-shading scenarios (6, 7 in CLAUDE.md) need a multi-module PVString
operating-point solve instead of the single-module one used here; see
scenarios_partial_shading.py.
"""

import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

from . import config, metrics
from .simulate import pv_operating_point


@dataclass
class Scenario:
    name: str
    duration_s: float
    irradiance_fn: Callable[[float], float]
    temperature_fn: Callable[[float], float] = field(default=lambda t: config.STC_TEMPERATURE_C)
    sensor_noise_std_frac: float = 0.0


@dataclass
class RunResult:
    times: np.ndarray
    voltages: np.ndarray
    currents: np.ndarray
    powers: np.ndarray
    theoretical_max_powers: np.ndarray
    duty_cycles: np.ndarray


def piecewise_constant(breakpoints: List[tuple]):
    """breakpoints: [(t_start, value), ...] sorted ascending; holds each
    value until the next breakpoint's t_start is reached."""

    def fn(t: float) -> float:
        value = breakpoints[0][1]
        for t_start, v in breakpoints:
            if t >= t_start:
                value = v
        return value

    return fn


def piecewise_linear(points: List[tuple]):
    """points: [(t, value), ...] sorted ascending; linearly interpolated
    between consecutive points, clamped at the ends."""
    times = [p[0] for p in points]
    values = [p[1] for p in points]

    def fn(t: float) -> float:
        return float(np.interp(t, times, values))

    return fn


def reference_mpp_curve(pv_model, times: np.ndarray, irradiance_fn, temperature_fn) -> np.ndarray:
    """True MPP power at each time sample.

    Caches by (irradiance, temperature) pair -- most scenarios are piecewise
    constant, so this collapses thousands of samples into a handful of
    find_mpp() calls. Independent of any algorithm's run, so callers driving
    many algorithms/Monte Carlo runs through the same scenario should compute
    this once and pass it into run_scenario() rather than letting each call
    recompute it.
    """
    cache = {}
    powers = np.empty(len(times))
    for idx, t in enumerate(times):
        irradiance = irradiance_fn(t)
        temperature_c = temperature_fn(t)
        key = (round(irradiance, 6), round(temperature_c, 6))
        if key not in cache:
            _, p_mpp = pv_model.find_mpp(irradiance, temperature_c)
            cache[key] = p_mpp
        powers[idx] = cache[key]
    return powers


def run_scenario(
    scenario: Scenario,
    algorithm,
    pv_model,
    initial_duty: float = 0.3,
    sample_period_s: float = config.MPPT_SAMPLE_PERIOD_S,
    rng: Optional[random.Random] = None,
    theoretical_max_powers: Optional[np.ndarray] = None,
) -> RunResult:
    """Drive `algorithm` through `scenario` against `pv_model`, one sample
    per `sample_period_s` of simulated time.

    Sensor noise (if `scenario.sensor_noise_std_frac > 0`) perturbs only the
    (v, i) measurements passed to `algorithm.step()`; the physical voltage,
    current, and power recorded in the result are the true, noise-free
    values -- noise models a flawed sensor, not a different physical system.
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
        irradiance = scenario.irradiance_fn(t)
        temperature_c = scenario.temperature_fn(t)
        v, i = pv_operating_point(pv_model, duty, irradiance=irradiance, temperature_c=temperature_c)

        v_measured, i_measured = v, i
        if scenario.sensor_noise_std_frac > 0 and rng is not None:
            v_measured = v * (1.0 + rng.gauss(0.0, scenario.sensor_noise_std_frac))
            i_measured = i * (1.0 + rng.gauss(0.0, scenario.sensor_noise_std_frac))

        voltages[idx] = v
        currents[idx] = i
        powers[idx] = v * i
        duty_cycles[idx] = duty

        duty = algorithm.step(v_measured, i_measured, duty)

    if theoretical_max_powers is None:
        theoretical_max_powers = reference_mpp_curve(pv_model, times, scenario.irradiance_fn, scenario.temperature_fn)

    return RunResult(times, voltages, currents, powers, theoretical_max_powers, duty_cycles)


def run_monte_carlo(
    scenario: Scenario,
    algorithm,
    pv_model,
    num_runs: int = config.MONTE_CARLO_RUNS,
    base_seed: int = 0,
    sample_period_s: float = config.MPPT_SAMPLE_PERIOD_S,
) -> List[RunResult]:
    """Run `num_runs` independent trials of `algorithm` against `scenario`.

    Run k always uses seed `base_seed + k` regardless of which algorithm is
    passed in, so the same sequence of randomized initial duty cycles (and
    sensor-noise draws) is used across algorithms at each run index --
    CLAUDE.md's "use identical random seeds for fair comparison."

    `algorithm` is reused across runs (its `reset()` is called at the start
    of each `run_scenario` call) rather than reconstructed, since a trained
    Q-learning agent's Q-table must survive across runs -- only its small
    per-episode (v_prev, p_prev) history needs clearing between runs.
    """
    n_samples = int(round(scenario.duration_s / sample_period_s)) + 1
    times = np.arange(n_samples) * sample_period_s
    theoretical_max_powers = reference_mpp_curve(pv_model, times, scenario.irradiance_fn, scenario.temperature_fn)

    results = []
    for run_id in range(num_runs):
        rng = random.Random(base_seed + run_id)
        initial_duty = rng.uniform(config.MPPT_DUTY_MIN + 0.05, config.MPPT_DUTY_MAX - 0.05)
        result = run_scenario(
            scenario,
            algorithm,
            pv_model,
            initial_duty=initial_duty,
            sample_period_s=sample_period_s,
            rng=rng,
            theoretical_max_powers=theoretical_max_powers,
        )
        results.append(result)
    return results


def compute_run_metrics(result: RunResult) -> dict:
    """All CLAUDE.md "Core Metrics" + "Energy-Based Metrics" for one run."""
    settle_time = metrics.settling_time(result.times, result.powers, result.theoretical_max_powers)
    oscillation_window_start = settle_time if settle_time is not None else result.times[-1]
    p2p, std = metrics.steady_state_oscillation(result.times, result.powers, oscillation_window_start)
    return {
        "tracking_efficiency_pct": metrics.tracking_efficiency(result.times, result.powers, result.theoretical_max_powers),
        "convergence_time_s": metrics.convergence_time(result.times, result.powers, result.theoretical_max_powers),
        "settling_time_s": settle_time,
        "oscillation_p2p_w": p2p,
        "oscillation_std_w": std,
        "energy_yield_j": metrics.energy_yield(result.times, result.powers),
        "energy_yield_ratio": metrics.energy_yield_ratio(result.times, result.powers, result.theoretical_max_powers),
    }


# --- Scenario definitions (CLAUDE.md "Test Scenarios", single-module ones) ---
# Timing for scenarios 4 and 8, where CLAUDE.md gives an example profile
# without exact breakpoints, was chosen to fit that example (a faster
# dwell time than scenario 3's, and 4 evenly spaced points over 5s
# respectively) -- flagged here in case the paper needs to justify it.


def scenario_steady_state() -> Scenario:
    return Scenario(
        name="steady_state",
        duration_s=2.0,
        irradiance_fn=piecewise_constant([(0.0, config.STC_IRRADIANCE)]),
        temperature_fn=piecewise_constant([(0.0, config.STC_TEMPERATURE_C)]),
    )


def scenario_multi_level_irradiance() -> Scenario:
    return Scenario(
        name="multi_level_irradiance",
        duration_s=5.0,
        irradiance_fn=piecewise_constant([(0.0, 200.0), (1.0, 400.0), (2.0, 600.0), (3.0, 800.0), (4.0, 1000.0)]),
        temperature_fn=piecewise_constant([(0.0, config.STC_TEMPERATURE_C)]),
    )


def scenario_step_change_irradiance() -> Scenario:
    return Scenario(
        name="step_change_irradiance",
        duration_s=5.0,
        irradiance_fn=piecewise_constant([(0.0, 1000.0), (1.0, 600.0), (3.0, 1000.0)]),
        temperature_fn=piecewise_constant([(0.0, config.STC_TEMPERATURE_C)]),
    )


def scenario_rapid_double_step() -> Scenario:
    return Scenario(
        name="rapid_double_step",
        duration_s=3.0,
        irradiance_fn=piecewise_constant([(0.0, 1000.0), (1.0, 200.0), (2.0, 1000.0)]),
        temperature_fn=piecewise_constant([(0.0, config.STC_TEMPERATURE_C)]),
    )


def scenario_temperature_step() -> Scenario:
    return Scenario(
        name="temperature_step",
        duration_s=5.0,
        irradiance_fn=piecewise_constant([(0.0, config.STC_IRRADIANCE)]),
        temperature_fn=piecewise_constant([(0.0, 25.0), (1.0, 50.0), (3.0, 25.0)]),
    )


def scenario_rapid_fluctuation_cloud_passage() -> Scenario:
    return Scenario(
        name="rapid_fluctuation_cloud_passage",
        duration_s=5.0,
        irradiance_fn=piecewise_linear([(0.0, 1000.0), (1.25, 600.0), (2.5, 800.0), (3.75, 400.0), (5.0, 1000.0)]),
        temperature_fn=piecewise_constant([(0.0, config.STC_TEMPERATURE_C)]),
    )


def scenario_sensor_noise_robustness() -> Scenario:
    return Scenario(
        name="sensor_noise_robustness",
        duration_s=2.0,
        irradiance_fn=piecewise_constant([(0.0, config.STC_IRRADIANCE)]),
        temperature_fn=piecewise_constant([(0.0, config.STC_TEMPERATURE_C)]),
        sensor_noise_std_frac=config.SENSOR_NOISE_STD_FRAC,
    )


SINGLE_MODULE_SCENARIOS = {
    "steady_state": scenario_steady_state,
    "multi_level_irradiance": scenario_multi_level_irradiance,
    "step_change_irradiance": scenario_step_change_irradiance,
    "rapid_double_step": scenario_rapid_double_step,
    "temperature_step": scenario_temperature_step,
    "rapid_fluctuation_cloud_passage": scenario_rapid_fluctuation_cloud_passage,
    "sensor_noise_robustness": scenario_sensor_noise_robustness,
}


# --- Long-format results table (CLAUDE.md "Results Format") ---
# Columns: algorithm, scenario, metric, value, run_id, seed, ql_condition.


def _matches_any(value: float, allowed: tuple, tol: float = 1e-6) -> bool:
    return any(abs(value - a) < tol for a in allowed)


def classify_ql_condition(
    irradiances,
    temperatures_c,
    has_sensor_noise: bool = False,
    is_partial_shading: bool = False,
) -> str:
    """Tag a scenario's physical conditions relative to Q-learning's training
    distribution -- CLAUDE.md's mandatory "report train-distribution and
    held-out results separately" requirement (Known Risks / Phase 3 TODO).

    `train_q_learning()` (algorithms/q_learning.py) only ever trains on a
    single flat-irradiance module, at STC_TEMPERATURE_C, with irradiance in
    config.QL_TRAINING_IRRADIANCES, and no sensor noise. A scenario counts as
    "train" only if every condition it exercises matches that regime; any
    single condition outside it (an untrained irradiance level, a non-STC
    temperature, sensor noise, or partial shading's multi-module topology)
    makes the whole scenario "held_out".

    This is a coarse, condition-level classification, not a claim that
    transient *dynamics* were trained -- train_q_learning() only ever sees
    static irradiance per episode, so e.g. step_change_irradiance (1000 -> 600
    -> 1000, both endpoints individually in QL_TRAINING_IRRADIANCES) is
    tagged "train" even though the mid-run step itself was never trained on.
    """
    if is_partial_shading:
        return "held_out"
    if has_sensor_noise:
        return "held_out"
    if any(not _matches_any(t, (config.STC_TEMPERATURE_C,)) for t in temperatures_c):
        return "held_out"
    if any(not _matches_any(irr, config.QL_TRAINING_IRRADIANCES) for irr in irradiances):
        return "held_out"
    return "train"


def scenario_ql_condition(scenario: Scenario, n_samples: int = 200) -> str:
    """classify_ql_condition() applied to a single-module Scenario, sampling
    its irradiance/temperature profiles over their full duration."""
    sample_times = np.linspace(0.0, scenario.duration_s, n_samples)
    irradiances = [scenario.irradiance_fn(t) for t in sample_times]
    temperatures_c = [scenario.temperature_fn(t) for t in sample_times]
    return classify_ql_condition(
        irradiances,
        temperatures_c,
        has_sensor_noise=scenario.sensor_noise_std_frac > 0,
        is_partial_shading=False,
    )


def results_to_rows(
    algorithm_name: str,
    scenario_name: str,
    results: List[RunResult],
    base_seed: int = 0,
    ql_condition: str = "not_applicable",
) -> List[dict]:
    """Flatten a list of per-run RunResults into long-format metric rows.

    `ql_condition` is only meaningful for algorithm_name == "q_learning"
    (see classify_ql_condition); it's forced to "not_applicable" for every other
    algorithm, since the train/held-out distinction doesn't apply to them.
    """
    tag = ql_condition if algorithm_name == "q_learning" else "not_applicable"
    rows = []
    for run_id, result in enumerate(results):
        seed = base_seed + run_id
        for metric_name, value in compute_run_metrics(result).items():
            rows.append(
                {
                    "algorithm": algorithm_name,
                    "scenario": scenario_name,
                    "metric": metric_name,
                    "value": value,
                    "run_id": run_id,
                    "seed": seed,
                    "ql_condition": tag,
                }
            )
    return rows


def computational_burden_rows(step_times: dict, baseline_key: str, base_seed: int = 0) -> List[dict]:
    """One row per algorithm for mean step time and burden relative to `baseline_key`.

    Not scenario-conditioned (it's a single fixed-operating-point measurement
    per algorithm, see metrics.mean_step_execution_time), so ql_condition is
    always "not_applicable" here, including for q_learning.
    """
    relative_burden = metrics.relative_computational_burden(step_times, baseline_key)
    rows = []
    for algorithm_name, step_time in step_times.items():
        rows.append(
            {
                "algorithm": algorithm_name,
                "scenario": "_computational_burden",
                "metric": "mean_step_time_s",
                "value": step_time,
                "run_id": 0,
                "seed": base_seed,
                "ql_condition": "not_applicable",
            }
        )
        rows.append(
            {
                "algorithm": algorithm_name,
                "scenario": "_computational_burden",
                "metric": "relative_burden",
                "value": relative_burden[algorithm_name],
                "run_id": 0,
                "seed": base_seed,
                "ql_condition": "not_applicable",
            }
        )
    return rows


def build_default_algorithms(pv_model_for_training) -> dict:
    """The 5 algorithms with default gains, keyed by name.

    Trains a fresh Q-learning agent against `pv_model_for_training` (its
    Q-table is then fixed for the rest of the sweep -- step() is greedy-only).
    """
    from .algorithms.fuzzy_logic import FuzzyLogicController
    from .algorithms.inc_cond import IncrementalConductance
    from .algorithms.p_and_o import PerturbObserve
    from .algorithms.q_learning import QLearning, train_q_learning
    from .algorithms.sliding_mode import SlidingModeControl

    q_agent = QLearning()
    train_q_learning(q_agent, pv_model_for_training)

    return {
        "p_and_o": PerturbObserve(),
        "inc_cond": IncrementalConductance(),
        "fuzzy_logic": FuzzyLogicController(),
        "q_learning": q_agent,
        "sliding_mode": SlidingModeControl(),
    }


def run_full_sweep(
    algorithms: dict,
    pv_model,
    panel_params,
    num_runs: int = config.MONTE_CARLO_RUNS,
    base_seed: int = 0,
    log=print,
) -> "pd.DataFrame":
    """Run every algorithm against every scenario (single-module and partial-
    shading) for `num_runs` Monte Carlo runs each, returning the long-format
    results table CLAUDE.md's Results Format section specifies.

    `algorithms`: dict[name -> MPPTAlgorithm], e.g. from build_default_algorithms().
    `panel_params`: TwoDiodeParameters, used to build fresh PVStrings for the
    partial-shading scenarios (kept separate per scenario so each gets its own
    Isc/Voc cache -- see scenarios_partial_shading.py).
    """
    import pandas as pd

    from .scenarios_partial_shading import PARTIAL_SHADING_SCENARIOS, build_pv_string, run_partial_shading_monte_carlo

    rows = []
    for algorithm_name, algorithm in algorithms.items():
        for scenario_name, factory in SINGLE_MODULE_SCENARIOS.items():
            log(f"{algorithm_name} x {scenario_name} ({num_runs} runs)")
            scenario = factory()
            results = run_monte_carlo(scenario, algorithm, pv_model, num_runs=num_runs, base_seed=base_seed)
            ql_condition = scenario_ql_condition(scenario)
            rows.extend(results_to_rows(algorithm_name, scenario_name, results, base_seed, ql_condition))

        for scenario_name, factory in PARTIAL_SHADING_SCENARIOS.items():
            log(f"{algorithm_name} x {scenario_name} ({num_runs} runs)")
            scenario = factory()
            pv_string = build_pv_string(panel_params, num_modules=len(scenario.irradiances))
            results = run_partial_shading_monte_carlo(
                scenario, algorithm, pv_string, num_runs=num_runs, base_seed=base_seed
            )
            rows.extend(results_to_rows(algorithm_name, scenario_name, results, base_seed, "held_out"))

    log("Measuring computational burden (mean step() time per algorithm)")
    step_times = {
        name: metrics.mean_step_execution_time(algorithm, config.PANEL_VMP_STC, config.PANEL_IMP_STC, 0.3)
        for name, algorithm in algorithms.items()
    }
    rows.extend(computational_burden_rows(step_times, baseline_key="p_and_o", base_seed=base_seed))

    return pd.DataFrame(rows)


def main():
    import argparse

    from .pv_model import TwoDiodeModel, extract_two_diode_parameters

    parser = argparse.ArgumentParser(description="Run the full MPPT algorithm comparison sweep.")
    parser.add_argument("--monte-carlo", type=int, default=config.MONTE_CARLO_RUNS, dest="num_runs")
    parser.add_argument("--output", type=str, default="results/")
    parser.add_argument("--base-seed", type=int, default=0)
    args = parser.parse_args()

    panel_params = extract_two_diode_parameters(
        voc=config.PANEL_VOC_STC,
        isc=config.PANEL_ISC_STC,
        vmp=config.PANEL_VMP_STC,
        imp=config.PANEL_IMP_STC,
    )
    pv_model = TwoDiodeModel(panel_params, num_cells=config.PANEL_NS)

    print("Training Q-learning agent...")
    algorithms = build_default_algorithms(pv_model)

    df = run_full_sweep(algorithms, pv_model, panel_params, num_runs=args.num_runs, base_seed=args.base_seed)

    import os

    os.makedirs(args.output, exist_ok=True)
    output_path = os.path.join(args.output, "comparison_table.csv")
    df.to_csv(output_path, index=False)
    print(f"Wrote {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
