"""Bootstrap confidence interval estimation for MPPT performance metrics.

This module implements bootstrapping methods to estimate confidence intervals
for MPPT algorithm performance metrics without assuming normal distributions.
"""

import numpy as np
from typing import Tuple, Optional, List, Union
from dataclasses import dataclass


@dataclass
class BootstrapResult:
    """Container for bootstrap analysis results."""
    
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstrap: int
    bootstrap_distribution: np.ndarray
    standard_error: float
    
    def summary(self) -> str:
        """Return a formatted summary string."""
        return (
            f"Estimate: {self.point_estimate:.4f} "
            f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}] "
            f"({self.confidence_level*100:.0f}% CI, SE={self.standard_error:.4f})"
        )


class BootstrapCI:
    """Bootstrap confidence interval calculator.
    
    Parameters
    ----------
    n_bootstrap : int, default=1000
        Number of bootstrap samples to generate.
    confidence_level : float, default=0.95
        Confidence level for the interval (e.g., 0.95 for 95% CI).
    method : str, default='percentile'
        Method for computing CI: 'percentile', 'bca', or 'normal'.
    random_state : int, optional
        Random seed for reproducibility.
    
    Examples
    --------
    >>> boot = BootstrapCI(n_bootstrap=1000, confidence_level=0.95)
    >>> result = boot.compute_ci(performance_scores)
    >>> print(result.summary())
    """
    
    def __init__(
        self,
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95,
        method: str = 'percentile',
        random_state: Optional[int] = None
    ):
        self.n_bootstrap = n_bootstrap
        self.confidence_level = confidence_level
        self.method = method
        self.rng = np.random.default_rng(random_state)
        
        if method not in ['percentile', 'bca', 'normal']:
            raise ValueError(f"Unknown method '{method}'. Use 'percentile', 'bca', or 'normal'.")
    
    def compute_ci(
        self,
        data: Union[np.ndarray, List[float]],
        statistic: callable = None
    ) -> BootstrapResult:
        """Compute bootstrap confidence interval for a statistic.
        
        Parameters
        ----------
        data : array-like
            Sample data to bootstrap from.
        statistic : callable, optional
            Function to compute the statistic of interest. 
            If None, uses the mean.
            
        Returns
        -------
        BootstrapResult
            Object containing point estimate, CI bounds, and bootstrap distribution.
        """
        data = np.asarray(data)
        n = len(data)
        
        if n < 2:
            raise ValueError("Need at least 2 observations for bootstrapping.")
        
        if statistic is None:
            statistic = np.mean
        
        # Compute point estimate on original data
        point_estimate = statistic(data)
        
        # Generate bootstrap samples and compute statistic
        bootstrap_stats = np.zeros(self.n_bootstrap)
        for i in range(self.n_bootstrap):
            indices = self.rng.choice(n, size=n, replace=True)
            bootstrap_sample = data[indices]
            bootstrap_stats[i] = statistic(bootstrap_sample)
        
        # Compute confidence interval based on method
        alpha = 1 - self.confidence_level
        
        if self.method == 'percentile':
            ci_lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
            ci_upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
        elif self.method == 'normal':
            se = np.std(bootstrap_stats, ddof=1)
            z_crit = abs(np.percentile(bootstrap_stats, 100 * alpha / 2) - point_estimate) / se
            ci_lower = point_estimate - z_crit * se
            ci_upper = point_estimate + z_crit * se
        elif self.method == 'bca':
            ci_lower, ci_upper = self._bca_interval(data, statistic, bootstrap_stats, alpha)
        
        standard_error = np.std(bootstrap_stats, ddof=1)
        
        return BootstrapResult(
            point_estimate=point_estimate,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=self.confidence_level,
            n_bootstrap=self.n_bootstrap,
            bootstrap_distribution=bootstrap_stats,
            standard_error=standard_error
        )
    
    def _bca_interval(
        self,
        data: np.ndarray,
        statistic: callable,
        bootstrap_stats: np.ndarray,
        alpha: float
    ) -> Tuple[float, float]:
        """Compute BCa (bias-corrected and accelerated) confidence interval."""
        n = len(data)
        theta_hat = statistic(data)
        
        # Bias correction
        n_below = np.sum(bootstrap_stats < theta_hat)
        z0 = scipy.stats.norm.ppf(n_below / self.n_bootstrap) if n_below > 0 else -np.inf
        
        # Acceleration (jackknife)
        jackknife_stats = np.zeros(n)
        for i in range(n):
            jackknife_sample = np.delete(data, i)
            jackknife_stats[i] = statistic(jackknife_sample)
        
        jackknife_mean = np.mean(jackknife_stats)
        numerator = np.sum((jackknife_mean - jackknife_stats) ** 3)
        denominator = 6 * (np.sum((jackknife_mean - jackknife_stats) ** 2) ** 1.5)
        
        if abs(denominator) < 1e-10:
            a = 0
        else:
            a = numerator / denominator
        
        # Adjusted percentiles
        z_alpha_lower = scipy.stats.norm.ppf(alpha / 2)
        z_alpha_upper = scipy.stats.norm.ppf(1 - alpha / 2)
        
        alpha_lower = scipy.stats.norm.cdf(z0 + (z0 + z_alpha_lower) / (1 - a * (z0 + z_alpha_lower)))
        alpha_upper = scipy.stats.norm.cdf(z0 + (z0 + z_alpha_upper) / (1 - a * (z0 + z_alpha_upper)))
        
        ci_lower = np.percentile(bootstrap_stats, alpha_lower * 100)
        ci_upper = np.percentile(bootstrap_stats, alpha_upper * 100)
        
        return ci_lower, ci_upper
    
    def compare_two_samples(
        self,
        sample1: Union[np.ndarray, List[float]],
        sample2: Union[np.ndarray, List[float]],
        statistic: callable = None
    ) -> Tuple[BootstrapResult, BootstrapResult, BootstrapResult]:
        """Compute bootstrap CIs for two samples and their difference.
        
        Parameters
        ----------
        sample1, sample2 : array-like
            Two independent samples to compare.
        statistic : callable, optional
            Statistic to compute (default: mean).
            
        Returns
        -------
        tuple
            (result1, result2, result_difference)
        """
        sample1 = np.asarray(sample1)
        sample2 = np.asarray(sample2)
        
        if statistic is None:
            statistic = np.mean
        
        result1 = self.compute_ci(sample1, statistic)
        result2 = self.compute_ci(sample2, statistic)
        
        # Bootstrap for difference
        diff_bootstrap = result2.bootstrap_distribution - result1.bootstrap_distribution
        diff_point = statistic(sample2) - statistic(sample1)
        
        alpha = 1 - self.confidence_level
        ci_lower = np.percentile(diff_bootstrap, 100 * alpha / 2)
        ci_upper = np.percentile(diff_bootstrap, 100 * (1 - alpha / 2))
        
        result_diff = BootstrapResult(
            point_estimate=diff_point,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=self.confidence_level,
            n_bootstrap=self.n_bootstrap,
            bootstrap_distribution=diff_bootstrap,
            standard_error=np.std(diff_bootstrap, ddof=1)
        )
        
        return result1, result2, result_diff


def bootstrap_confidence_interval(
    data: Union[np.ndarray, List[float]],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    statistic: callable = None,
    random_state: Optional[int] = None
) -> BootstrapResult:
    """Convenience function for computing bootstrap confidence intervals.
    
    Parameters
    ----------
    data : array-like
        Sample data.
    n_bootstrap : int
        Number of bootstrap samples.
    confidence_level : float
        Confidence level (e.g., 0.95).
    statistic : callable, optional
        Statistic function (default: mean).
    random_state : int, optional
        Random seed.
        
    Returns
    -------
    BootstrapResult
        Bootstrap analysis results.
    """
    boot = BootstrapCI(
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level,
        random_state=random_state
    )
    return boot.compute_ci(data, statistic)


# Lazy import for scipy (only needed for BCa method)
def scipy():
    import scipy
    import scipy.stats
    return scipy
