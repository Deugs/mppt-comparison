"""Sensitivity analysis and robustness evaluation for MPPT algorithms.

This module provides tools for testing MPPT algorithm robustness under
various noise conditions and environmental perturbations.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum


class NoiseType(Enum):
    """Types of noise that can be injected into sensor measurements."""
    GAUSSIAN = "gaussian"
    IMPULSE = "impulse"
    DRIFT = "drift"
    BIAS = "bias"
    UNIFORM = "uniform"


@dataclass
class NoiseConfig:
    """Configuration for noise injection."""
    
    noise_type: NoiseType
    magnitude: float  # Standard deviation for Gaussian, amplitude for others
    probability: float = 1.0  # For impulse noise (probability of occurrence)
    drift_rate: float = 0.0  # For drift noise (rate per time step)
    bias_value: float = 0.0  # For constant bias
    seed: Optional[int] = None


@dataclass
class RobustnessMetrics:
    """Metrics quantifying algorithm robustness to perturbations."""
    
    nominal_performance: float
    noisy_performance: float
    performance_degradation: float  # (nominal - noisy) / nominal
    variance_ratio: float  # variance_noisy / variance_nominal
    recovery_time: Optional[float] = None  # Time to return to nominal after disturbance
    failure_count: int = 0  # Number of catastrophic failures
    mean_absolute_error: float = 0.0
    
    @property
    def robustness_score(self) -> float:
        """Calculate overall robustness score (0-1, higher is better)."""
        # Weighted combination of metrics
        degradation_penalty = max(0, self.performance_degradation)
        variance_penalty = min(1, max(0, self.variance_ratio - 1))
        failure_penalty = min(1, self.failure_count * 0.1)
        
        score = 1.0 - (0.5 * degradation_penalty + 
                       0.3 * variance_penalty + 
                       0.2 * failure_penalty)
        return max(0, min(1, score))


class NoiseInjector:
    """Inject various types of noise into sensor measurements.
    
    Parameters
    ----------
    config : NoiseConfig
        Configuration specifying noise type and parameters.
    
    Examples
    --------
    >>> config = NoiseConfig(NoiseType.GAUSSIAN, magnitude=0.05)
    >>> injector = NoiseInjector(config)
    >>> noisy_irradiance = injector.inject(clean_irradiance)
    """
    
    def __init__(self, config: NoiseConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
    
    def inject(self, signal: np.ndarray) -> np.ndarray:
        """Inject noise into a signal.
        
        Parameters
        ----------
        signal : np.ndarray
            Clean input signal.
            
        Returns
        -------
        np.ndarray
            Noisy signal.
        """
        if self.config.noise_type == NoiseType.GAUSSIAN:
            return self._inject_gaussian(signal)
        elif self.config.noise_type == NoiseType.IMPULSE:
            return self._inject_impulse(signal)
        elif self.config.noise_type == NoiseType.DRIFT:
            return self._inject_drift(signal)
        elif self.config.noise_type == NoiseType.BIAS:
            return self._inject_bias(signal)
        elif self.config.noise_type == NoiseType.UNIFORM:
            return self._inject_uniform(signal)
        else:
            raise ValueError(f"Unknown noise type: {self.config.noise_type}")
    
    def _inject_gaussian(self, signal: np.ndarray) -> np.ndarray:
        """Add Gaussian noise."""
        noise = self.rng.normal(0, self.config.magnitude, size=signal.shape)
        return signal + noise
    
    def _inject_impulse(self, signal: np.ndarray) -> np.ndarray:
        """Add impulse (salt-and-pepper) noise."""
        noisy = signal.copy()
        mask = self.rng.random(size=signal.shape) < self.config.probability
        polarity = self.rng.choice([-1, 1], size=np.sum(mask))
        noisy[mask] += polarity * self.config.magnitude
        return noisy
    
    def _inject_drift(self, signal: np.ndarray) -> np.ndarray:
        """Add linear drift over time."""
        drift = self.config.drift_rate * np.arange(len(signal))
        return signal + drift
    
    def _inject_bias(self, signal: np.ndarray) -> np.ndarray:
        """Add constant bias."""
        return signal + self.config.bias_value
    
    def _inject_uniform(self, signal: np.ndarray) -> np.ndarray:
        """Add uniform noise."""
        half_range = self.config.magnitude / 2
        noise = self.rng.uniform(-half_range, half_range, size=signal.shape)
        return signal + noise


class SensitivityAnalyzer:
    """Analyze algorithm sensitivity to parameter variations and noise.
    
    This class runs Monte Carlo simulations with varying noise levels
    to quantify algorithm robustness.
    
    Parameters
    ----------
    algorithm_func : callable
        Function that runs the MPPT algorithm simulation.
        Should accept (irradiance, temperature, noise_config) and return performance metric.
    baseline_irradiance : np.ndarray
        Baseline irradiance profile for testing.
    baseline_temperature : float
        Baseline temperature (default: 25°C).
    
    Examples
    --------
    >>> analyzer = SensitivityAnalyzer(simulate_mppt, irradiance_profile)
    >>> results = analyzer.sweep_noise_levels(noise_levels=[0.01, 0.05, 0.10])
    >>> analyzer.plot_robustness_curve(results)
    """
    
    def __init__(
        self,
        algorithm_func: Callable,
        baseline_irradiance: np.ndarray,
        baseline_temperature: float = 25.0
    ):
        self.algorithm_func = algorithm_func
        self.baseline_irradiance = baseline_irradiance
        self.baseline_temperature = baseline_temperature
        self.results_cache: Dict[str, RobustnessMetrics] = {}
    
    def sweep_noise_levels(
        self,
        noise_levels: List[float],
        noise_type: NoiseType = NoiseType.GAUSSIAN,
        n_trials: int = 30,
        seed: Optional[int] = None
    ) -> Dict[float, List[RobustnessMetrics]]:
        """Evaluate algorithm performance across multiple noise levels.
        
        Parameters
        ----------
        noise_levels : list of float
            List of noise magnitudes to test.
        noise_type : NoiseType
            Type of noise to inject.
        n_trials : int
            Number of Monte Carlo trials per noise level.
        seed : int, optional
            Random seed for reproducibility.
            
        Returns
        -------
        dict
            Mapping from noise level to list of RobustnessMetrics.
        """
        rng = np.random.default_rng(seed)
        results: Dict[float, List[RobustnessMetrics]] = {}
        
        # Run baseline (no noise)
        baseline_performances = []
        for _ in range(n_trials):
            perf = self.algorithm_func(
                self.baseline_irradiance,
                self.baseline_temperature,
                noise_config=None
            )
            baseline_performances.append(perf)
        
        nominal_perf = np.mean(baseline_performances)
        nominal_var = np.var(baseline_performances)
        
        # Test each noise level
        for level in noise_levels:
            config = NoiseConfig(
                noise_type=noise_type,
                magnitude=level,
                seed=rng.integers(0, 2**31)
            )
            
            trial_metrics = []
            for _ in range(n_trials):
                # Run with noise
                noisy_perf = self.algorithm_func(
                    self.baseline_irradiance,
                    self.baseline_temperature,
                    noise_config=config
                )
                
                metrics = RobustnessMetrics(
                    nominal_performance=nominal_perf,
                    noisy_performance=noisy_perf,
                    performance_degradation=(nominal_perf - noisy_perf) / nominal_perf if nominal_perf > 0 else 0,
                    variance_ratio=np.var([noisy_perf]) / nominal_var if nominal_var > 0 else 1.0,
                    mean_absolute_error=abs(nominal_perf - noisy_perf)
                )
                trial_metrics.append(metrics)
            
            results[level] = trial_metrics
        
        return results
    
    def generate_heatmap_data(
        self,
        noise_types: List[NoiseType],
        noise_levels: List[float],
        n_trials: int = 20
    ) -> np.ndarray:
        """Generate data for robustness heatmap visualization.
        
        Parameters
        ----------
        noise_types : list of NoiseType
            Types of noise to include in heatmap.
        noise_levels : list of float
            Noise magnitudes to test.
        n_trials : int
            Trials per condition.
            
        Returns
        -------
        np.ndarray
            2D array [noise_type_idx, noise_level_idx] of robustness scores.
        """
        heatmap = np.zeros((len(noise_types), len(noise_levels)))
        
        for i, noise_type in enumerate(noise_types):
            results = self.sweep_noise_levels(
                noise_levels=noise_levels,
                noise_type=noise_type,
                n_trials=n_trials
            )
            
            for j, level in enumerate(noise_levels):
                avg_robustness = np.mean([
                    m.robustness_score for m in results[level]
                ])
                heatmap[i, j] = avg_robustness
        
        return heatmap


class RobustnessEvaluator:
    """Comprehensive robustness evaluation framework.
    
    Orchestrates sensitivity analyses and generates summary reports
    suitable for publication.
    
    Parameters
    ----------
    analyzers : dict
        Dictionary mapping algorithm names to SensitivityAnalyzer instances.
    
    Examples
    --------
    >>> evaluator = RobustnessEvaluator(analyzers)
    >>> report = evaluator.generate_comparison_report()
    >>> print(report)
    """
    
    def __init__(self, analyzers: Dict[str, SensitivityAnalyzer]):
        self.analyzers = analyzers
        self.all_results: Dict[str, Dict] = {}
    
    def evaluate_all_algorithms(
        self,
        noise_levels: List[float] = None,
        noise_types: List[NoiseType] = None,
        n_trials: int = 30,
        seed: int = 42
    ) -> Dict[str, Dict]:
        """Run comprehensive robustness evaluation for all algorithms.
        
        Parameters
        ----------
        noise_levels : list, optional
            Noise levels to test (default: [0.01, 0.02, 0.05, 0.10]).
        noise_types : list, optional
            Noise types to test (default: all types).
        n_trials : int
            Number of Monte Carlo trials.
        seed : int
            Random seed.
            
        Returns
        -------
        dict
            Nested dictionary: algorithm → noise_type → noise_level → metrics.
        """
        if noise_levels is None:
            noise_levels = [0.01, 0.02, 0.05, 0.10, 0.20]
        
        if noise_types is None:
            noise_types = list(NoiseType)
        
        results = {}
        
        for alg_name, analyzer in self.analyzers.items():
            alg_results = {}
            
            for noise_type in noise_types:
                type_results = analyzer.sweep_noise_levels(
                    noise_levels=noise_levels,
                    noise_type=noise_type,
                    n_trials=n_trials,
                    seed=seed
                )
                alg_results[noise_type.value] = type_results
            
            results[alg_name] = alg_results
        
        self.all_results = results
        return results
    
    def rank_algorithms_by_robustness(
        self,
        noise_level: float = 0.05,
        noise_type: NoiseType = NoiseType.GAUSSIAN
    ) -> List[Tuple[str, float]]:
        """Rank algorithms by robustness score at specified condition.
        
        Parameters
        ----------
        noise_level : float
            Noise magnitude to evaluate at.
        noise_type : NoiseType
            Type of noise to evaluate.
            
        Returns
        -------
        list of tuples
            Sorted list of (algorithm_name, robustness_score).
        """
        rankings = []
        
        for alg_name, alg_results in self.all_results.items():
            if noise_type.value in alg_results:
                type_results = alg_results[noise_type.value]
                if noise_level in type_results:
                    metrics_list = type_results[noise_level]
                    avg_robustness = np.mean([
                        m.robustness_score for m in metrics_list
                    ])
                    rankings.append((alg_name, avg_robustness))
        
        # Sort by robustness (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def generate_summary_table(self) -> str:
        """Generate LaTeX-ready summary table of robustness results.
        
        Returns
        -------
        str
            LaTeX tabular environment with robustness comparison.
        """
        lines = [
            "\\begin{table}[h]",
            "\\centering",
            "\\caption{Algorithm Robustness Comparison Under Sensor Noise}",
            "\\begin{tabular}{lccccc}",
            "\\toprule",
            "\\textbf{Algorithm} & \\textbf{Gaussian} & \\textbf{Impulse} & ",
            "\\textbf{Drift} & \\textbf{Bias} & \\textbf{Mean} \\\\",
            "\\midrule"
        ]
        
        noise_types = [NoiseType.GAUSSIAN, NoiseType.IMPULSE, 
                      NoiseType.DRIFT, NoiseType.BIAS]
        
        for alg_name, alg_results in self.all_results.items():
            row_scores = []
            
            for noise_type in noise_types:
                if noise_type.value in alg_results:
                    # Average across all noise levels
                    type_results = alg_results[noise_type.value]
                    all_scores = []
                    for metrics_list in type_results.values():
                        scores = [m.robustness_score for m in metrics_list]
                        all_scores.extend(scores)
                    
                    avg_score = np.mean(all_scores) if all_scores else 0
                    row_scores.append(avg_score)
                else:
                    row_scores.append(0)
            
            mean_score = np.mean(row_scores)
            
            # Format with best value bolded
            formatted_scores = [f"{s:.3f}" for s in row_scores]
            max_idx = np.argmax(row_scores)
            formatted_scores[max_idx] = f"\\textbf{{{row_scores[max_idx]:.3f}}}"
            
            row = f"{alg_name} & " + " & ".join(formatted_scores) + \
                  f" & \\textbf{{{mean_score:.3f}}} \\\\"
            lines.append(row)
        
        lines.extend([
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}"
        ])
        
        return "\n".join(lines)
    
    def identify_failure_modes(
        self,
        threshold: float = 0.5
    ) -> Dict[str, List[Tuple[NoiseType, float]]]:
        """Identify conditions where algorithms fail (robustness < threshold).
        
        Parameters
        ----------
        threshold : float
            Robustness score below which performance is considered failure.
            
        Returns
        -------
        dict
            Mapping algorithm → list of (noise_type, noise_level) failure conditions.
        """
        failures = {}
        
        for alg_name, alg_results in self.all_results.items():
            alg_failures = []
            
            for noise_type_str, type_results in alg_results.items():
                noise_type = NoiseType(noise_type_str)
                
                for noise_level, metrics_list in type_results.items():
                    avg_robustness = np.mean([
                        m.robustness_score for m in metrics_list
                    ])
                    
                    if avg_robustness < threshold:
                        alg_failures.append((noise_type, noise_level))
            
            failures[alg_name] = alg_failures
        
        return failures
