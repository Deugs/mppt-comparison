#!/usr/bin/env python3
"""Master experiment runner for MPPT algorithm comparison.

This script orchestrates the complete experimental pipeline:
1. Baseline algorithm comparison (P&O, IncCond, Fuzzy, Q-learning, Sliding Mode)
2. SOTA baseline comparison (PSO, Neural Network)
3. Scenario testing (steady-state, step changes, partial shading)
4. Monte Carlo analysis with statistical validation
5. Results aggregation and export

Usage:
    python scripts/run_all_experiments.py [--n-runs N] [--output-dir DIR]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.algorithms.fuzzy_logic import FuzzyLogicController
from src.algorithms.inc_cond import IncrementalConductance
from src.algorithms.p_and_o import PerturbObserve
from src.algorithms.q_learning import QLearning
from src.algorithms.sliding_mode import SlidingModeControl
from src.baselines.neural_mppt import NeuralMPPT, MLPTracker
from src.baselines.pso_mppt import PSOMPPT
from src.config import (
    CONVERTER_LOAD_RESISTANCE,
    PANEL_IMP_STC,
    PANEL_ISC_STC,
    PANEL_PMAX_STC as MPP_POWER_STC,
    PANEL_VMP_STC,
    PANEL_VOC_STC,
    STC_IRRADIANCE,
    STC_TEMPERATURE_C,
)
from src.converter import BoostConverter, BoostConverterDesign, design_boost_converter
from src.metrics import MetricsCalculator
from src.simulate import pv_operating_point as simulate_pv_operating_point
from src.pv_model import PVModule, TwoDiodeParameters, extract_two_diode_parameters
from src import scenarios as scenarios_module
from src import config
from src.stats.bootstrap import bootstrap_confidence_interval, BootstrapCI
from src.stats.hypothesis_tests import wilcoxon_signed_rank


class BootstrapAnalyzer:
    """Simple wrapper for bootstrap analysis."""
    
    def __init__(self, n_bootstrap=1000):
        self.n_bootstrap = n_bootstrap
        self.bootstrap_ci = BootstrapCI(n_bootstrap=n_bootstrap, confidence_level=0.95)
    
    def compute_ci(self, data, confidence=0.95):
        """Compute bootstrap confidence interval."""
        return self.bootstrap_ci.compute_ci(data)


class HypothesisTester:
    """Simple wrapper for hypothesis tests."""
    
    def wilcoxon_test(self, data1, data2):
        """Perform Wilcoxon signed-rank test."""
        result = wilcoxon_signed_rank(data1, data2)
        return result.statistic, result.p_value


def get_all_algorithms():
    """Initialize all MPPT algorithms for comparison."""
    return {
        "perturb_observe": PerturbObserve(),
        "incremental_conductance": IncrementalConductance(),
        "fuzzy_3x3": FuzzyLogicController(labels=["N", "Z", "P"]),
        "fuzzy_5x5": FuzzyLogicController(labels=["VN", "N", "Z", "P", "VP"]),
        "fuzzy_7x7": FuzzyLogicController(),
        "q_learning": QLearning(),
        "sliding_mode": SlidingModeControl(),
        "pso": PSOMPPT(),
        "neural_net": MLPTracker(),
    }


def get_all_scenarios():
    """Initialize all test scenarios."""
    # Create standard scenarios using helper functions
    return {
        "steady_state_stc": scenarios_module.Scenario(
            name="Steady State STC",
            duration_s=1.0,
            irradiance_fn=lambda t: config.STC_IRRADIANCE,
            temperature_fn=lambda t: config.STC_TEMPERATURE_C,
        ),
        "multi_level_irradiance": scenarios_module.Scenario(
            name="Multi-Level Irradiance Step",
            duration_s=2.0,
            irradiance_fn=scenarios_module.piecewise_constant([
                (0.0, 200),
                (0.5, 600),
                (1.0, 1000),
                (1.5, 400),
            ]),
            temperature_fn=lambda t: config.STC_TEMPERATURE_C,
        ),
        "temperature_variation": scenarios_module.Scenario(
            name="Temperature Variation",
            duration_s=2.0,
            irradiance_fn=lambda t: config.STC_IRRADIANCE,
            temperature_fn=scenarios_module.piecewise_constant([
                (0.0, 25),
                (0.5, 35),
                (1.0, 45),
                (1.5, 30),
            ]),
        ),
        "partial_shading_pattern_a": scenarios_module.Scenario(
            name="Partial Shading Pattern A",
            duration_s=2.0,
            irradiance_fn=scenarios_module.piecewise_constant([
                (0.0, 1000),
                (0.5, 500),
                (1.0, 800),
                (1.5, 300),
            ]),
            temperature_fn=lambda t: config.STC_TEMPERATURE_C,
        ),
        "partial_shading_pattern_b": scenarios_module.Scenario(
            name="Partial Shading Pattern B",
            duration_s=2.0,
            irradiance_fn=scenarios_module.piecewise_constant([
                (0.0, 900),
                (0.5, 700),
                (1.0, 400),
                (1.5, 600),
            ]),
            temperature_fn=lambda t: config.STC_TEMPERATURE_C,
        ),
    }


def run_single_experiment(algorithm, scenario, pv_module, converter, dt=0.001):
    """Run a single experiment and return metrics.
    
    Args:
        algorithm: MPPT algorithm instance
        scenario: Test scenario instance
        pv_module: PV module model
        converter: Boost converter model
        dt: Time step in seconds
    
    Returns:
        Dictionary containing performance metrics
    """
    # Initialize simulation
    n_steps = int(scenario.duration_s / dt)
    time_array = np.linspace(0, scenario.duration_s, n_steps)
    
    # Storage arrays
    power_history = []
    voltage_history = []
    current_history = []
    duty_cycle_history = []
    irradiance_history = []
    temperature_history = []
    reference_power_history = []
    
    # Reset algorithm state
    algorithm.reset()
    
    # Run simulation - generate profiles on the fly
    for t in time_array:
        irr = scenario.irradiance_fn(t)
        temp = scenario.temperature_fn(t)
        
        # Get reference MPP using find_mpp from TwoDiodeModel
        v_mpp_ref, p_mpp_ref = pv_module.groups[0].model.find_mpp(irradiance=irr, temperature_c=temp)
        
        # Get current PV measurements using simulate.pv_operating_point
        v_pv, i_pv = simulate_pv_operating_point(
            pv_module.groups[0].model,
            duty_cycle=converter.duty_cycle,
            irradiance=irr,
            temperature_c=temp
        )
        p_pv = v_pv * i_pv
        
        # Algorithm update - use step() method for standard algorithms, update() for baselines
        if hasattr(algorithm, 'step'):
            new_duty = algorithm.step(v_pv, i_pv, converter.duty_cycle)
        elif hasattr(algorithm, 'update'):
            new_duty = algorithm.update(v_pv, i_pv, converter.duty_cycle)
        else:
            raise AttributeError(f"Algorithm {type(algorithm).__name__} has neither 'step' nor 'update' method")
        converter.duty_cycle = np.clip(new_duty, 0.01, 0.95)
        
        # Record data
        power_history.append(p_pv)
        voltage_history.append(v_pv)
        current_history.append(i_pv)
        duty_cycle_history.append(converter.duty_cycle)
        irradiance_history.append(irr)
        temperature_history.append(temp)
        reference_power_history.append(p_mpp_ref)
    
    # Calculate metrics
    calculator = MetricsCalculator()
    metrics = calculator.compute_all_metrics(
        power=np.array(power_history),
        reference_power=np.array(reference_power_history),
        duty_cycle=np.array(duty_cycle_history),
        time=time_array,
        settling_threshold=0.02,
    )
    
    return {
        "metrics": metrics,
        "time": time_array,
        "power": power_history,
        "voltage": voltage_history,
        "current": current_history,
        "duty_cycle": duty_cycle_history,
        "irradiance": irradiance_history,
        "temperature": temperature_history,
        "reference_power": reference_power_history,
    }


def run_monte_carlo_analysis(algorithms, scenarios, pv_module, converter, n_runs=50, dt=0.001):
    """Run Monte Carlo analysis with parameter variations.
    
    Args:
        algorithms: Dict of algorithm instances
        scenarios: Dict of scenario instances
        pv_module: PV module model
        converter: Boost converter model
        n_runs: Number of Monte Carlo runs
        dt: Time step
    
    Returns:
        DataFrame with all results and statistics
    """
    print(f"Running Monte Carlo analysis ({n_runs} runs per configuration)...")
    
    all_results = []
    total_configs = len(algorithms) * len(scenarios)
    current_config = 0
    
    for algo_name, algorithm in algorithms.items():
        for scenario_name, scenario in scenarios.items():
            current_config += 1
            print(f"  [{current_config}/{total_configs}] {algo_name} x {scenario_name}")
            
            for run_idx in range(n_runs):
                # Add random variations to simulate uncertainty
                np.random.seed(run_idx)
                
                # Vary parameters slightly
                base_params = pv_module.groups[0].model.params
                varied_params = TwoDiodeParameters(
                    iph=base_params.iph * (1 + 0.01 * np.random.randn()),
                    is1=base_params.is1 * (1 + 0.05 * np.random.randn()),
                    is2=base_params.is2 * (1 + 0.05 * np.random.randn()),
                    rs=base_params.rs * (1 + 0.05 * np.random.randn()),
                    rsh=base_params.rsh * (1 + 0.05 * np.random.randn()),
                    a1=base_params.a1 * (1 + 0.02 * np.random.randn()),
                    a2=base_params.a2 * (1 + 0.02 * np.random.randn()),
                )
                varied_pv = PVModule(varied_params)
                
                try:
                    result = run_single_experiment(
                        algorithm=algorithm,
                        scenario=scenario,
                        pv_module=varied_pv,
                        converter=BoostConverter(),
                        dt=dt
                    )
                    
                    # Store individual run results
                    for metric_name, metric_value in result["metrics"].items():
                        all_results.append({
                            "algorithm": algo_name,
                            "scenario": scenario_name,
                            "run": run_idx,
                            "metric": metric_name,
                            "value": metric_value if not np.isnan(metric_value) else None,
                            "ql_condition": "not_applicable",
                        })
                        
                except Exception as e:
                    print(f"    Warning: Run {run_idx} failed for {algo_name}/{scenario_name}: {e}")
                    continue
    
    return pd.DataFrame(all_results)


def compute_statistics(monte_carlo_df):
    """Compute aggregate statistics from Monte Carlo results.
    
    Args:
        monte_carlo_df: DataFrame with individual run results
    
    Returns:
        DataFrame with aggregated statistics
    """
    print("Computing statistics...")
    
    stats_results = []
    
    # Group by algorithm, scenario, and metric
    grouped = monte_carlo_df.groupby(["algorithm", "scenario", "metric"])
    
    for (algo, scenario, metric), group in grouped:
        values = group["value"].dropna()
        n = len(values)
        
        if n == 0:
            continue
        
        # Compute statistics
        mean_val = values.mean()
        std_val = values.std() if n > 1 else 0.0
        median_val = values.median()
        
        # Compute IQR
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        
        # Bootstrap confidence intervals
        if n >= 10:
            bootstrap_analyzer = BootstrapAnalyzer(n_bootstrap=1000)
            result = bootstrap_analyzer.compute_ci(values.values)
            ci_low, ci_high = result.ci_lower, result.ci_upper
        else:
            ci_low, ci_high = mean_val - 1.96 * std_val / np.sqrt(n), mean_val + 1.96 * std_val / np.sqrt(n)
        
        stats_results.append({
            "algorithm": algo,
            "scenario": scenario,
            "metric": metric,
            "n": n,
            "n_valid": n,
            "mean": mean_val,
            "std": std_val,
            "ci95_low": ci_low,
            "ci95_high": ci_high,
            "median": median_val,
            "iqr": iqr,
            "ql_condition": "not_applicable",
        })
    
    return pd.DataFrame(stats_results)


def run_hypothesis_tests(stats_df):
    """Perform statistical hypothesis tests between algorithms.
    
    Args:
        stats_df: DataFrame with aggregated statistics
    
    Returns:
        DataFrame with hypothesis test results
    """
    print("Running hypothesis tests...")
    
    test_results = []
    tester = HypothesisTester()
    
    # For each scenario and metric, compare algorithms
    scenarios = stats_df["scenario"].unique()
    metrics = stats_df["metric"].unique()
    
    for scenario in scenarios:
        for metric in metrics:
            scenario_data = stats_df[
                (stats_df["scenario"] == scenario) & 
                (stats_df["metric"] == metric)
            ]
            
            algorithms = scenario_data["algorithm"].unique()
            
            # Pairwise comparisons
            for i, algo1 in enumerate(algorithms):
                for algo2 in algorithms[i+1:]:
                    data1 = scenario_data[scenario_data["algorithm"] == algo1]["mean"].values
                    data2 = scenario_data[scenario_data["algorithm"] == algo2]["mean"].values
                    
                    if len(data1) >= 6 and len(data2) >= 6:
                        # Wilcoxon signed-rank test
                        try:
                            stat, pvalue = tester.wilcoxon_test(data1, data2)
                            
                            test_results.append({
                                "scenario": scenario,
                                "metric": metric,
                                "algorithm_1": algo1,
                                "algorithm_2": algo2,
                                "test_statistic": stat,
                                "p_value": pvalue,
                                "significant_at_0.05": pvalue < 0.05,
                                "significant_at_0.01": pvalue < 0.01,
                            })
                        except ValueError:
                            # Skip if test fails (e.g., all differences are zero)
                            pass
    
    return pd.DataFrame(test_results)


def main():
    """Main entry point for experiment runner."""
    parser = argparse.ArgumentParser(description="Run MPPT algorithm comparison experiments")
    parser.add_argument("--n-runs", type=int, default=10, help="Number of Monte Carlo runs (default: 10 for faster execution)")
    parser.add_argument("--output-dir", type=str, default="results", help="Output directory")
    parser.add_argument("--dt", type=float, default=0.01, help="Simulation time step (default: 0.01s for faster execution)")
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)
    (output_dir / "monte_carlo").mkdir(exist_ok=True)
    
    print("=" * 60)
    print("MPPT Algorithm Comparison - Experiment Runner")
    print("=" * 60)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Monte Carlo runs: {args.n_runs}")
    print(f"Time step: {args.dt}s")
    print()
    
    # Initialize components
    print("Initializing components...")
    # Extract two-diode parameters from datasheet values
    params = extract_two_diode_parameters(
        voc=PANEL_VOC_STC,
        isc=PANEL_ISC_STC,
        vmp=PANEL_VMP_STC,
        imp=PANEL_IMP_STC,
    )
    pv_module = PVModule(params)
    converter = BoostConverter()
    algorithms = get_all_algorithms()
    scenarios = get_all_scenarios()
    
    print(f"  Algorithms: {list(algorithms.keys())}")
    print(f"  Scenarios: {list(scenarios.keys())}")
    print()
    
    # Run Monte Carlo analysis
    start_time = time.time()
    monte_carlo_df = run_monte_carlo_analysis(
        algorithms=algorithms,
        scenarios=scenarios,
        pv_module=pv_module,
        converter=converter,
        n_runs=args.n_runs,
        dt=args.dt
    )
    
    # Save raw Monte Carlo data
    monte_carlo_file = output_dir / "monte_carlo" / f"raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    monte_carlo_df.to_csv(monte_carlo_file, index=False)
    print(f"\nRaw Monte Carlo data saved to: {monte_carlo_file}")
    
    # Compute statistics
    stats_df = compute_statistics(monte_carlo_df)
    stats_file = output_dir / "summary_table.csv"
    stats_df.to_csv(stats_file, index=False)
    print(f"Summary statistics saved to: {stats_file}")
    
    # Run hypothesis tests
    test_df = run_hypothesis_tests(stats_df)
    test_file = output_dir / "statistical_tests.csv"
    test_df.to_csv(test_file, index=False)
    print(f"Hypothesis test results saved to: {test_file}")
    
    # Create comparison table
    comparison_data = []
    for scenario in scenarios.keys():
        scenario_stats = stats_df[stats_df["scenario"] == scenario]
        for algo in algorithms.keys():
            algo_stats = scenario_stats[scenario_stats["algorithm"] == algo]
            if len(algo_stats) > 0:
                tracking_eff = algo_stats[algo_stats["metric"] == "tracking_efficiency_pct"]["mean"].values
                conv_time = algo_stats[algo_stats["metric"] == "convergence_time_s"]["mean"].values
                energy_yield = algo_stats[algo_stats["metric"] == "energy_yield_j"]["mean"].values
                
                comparison_data.append({
                    "algorithm": algo,
                    "scenario": scenario,
                    "tracking_efficiency_pct": tracking_eff[0] if len(tracking_eff) > 0 else None,
                    "convergence_time_s": conv_time[0] if len(conv_time) > 0 else None,
                    "energy_yield_j": energy_yield[0] if len(energy_yield) > 0 else None,
                })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_file = output_dir / "comparison_table.csv"
    comparison_df.to_csv(comparison_file, index=False)
    print(f"Comparison table saved to: {comparison_file}")
    
    elapsed_time = time.time() - start_time
    print()
    print("=" * 60)
    print(f"Experiments completed in {elapsed_time:.2f}s")
    print(f"End time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Print summary
    print("\nTop performers by tracking efficiency (STC steady-state):")
    stc_data = comparison_df[comparison_df["scenario"] == "steady_state_stc"].sort_values(
        "tracking_efficiency_pct", ascending=False
    )
    for _, row in stc_data.head(5).iterrows():
        print(f"  {row['algorithm']:25s}: {row['tracking_efficiency_pct']:.2f}%")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
