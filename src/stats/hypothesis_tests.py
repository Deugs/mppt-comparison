"""Hypothesis testing for MPPT algorithm comparison.

This module provides statistical hypothesis tests to determine if performance
differences between MPPT algorithms are statistically significant.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional, Union
from dataclasses import dataclass
from scipy import stats


@dataclass
class HypothesisTestResult:
    """Container for hypothesis test results."""
    
    test_name: str
    statistic: float
    p_value: float
    null_hypothesis: str
    alternative_hypothesis: str
    significance_level: float
    reject_null: bool
    effect_size: Optional[float] = None
    notes: str = ""
    
    def summary(self) -> str:
        """Return a formatted summary string."""
        decision = "REJECT" if self.reject_null else "FAIL TO REJECT"
        result = (
            f"{self.test_name}: {self.statistic:.4f}, p={self.p_value:.4g} "
            f"(α={self.significance_level}) → {decision} H₀"
        )
        if self.effect_size is not None:
            result += f", effect size={self.effect_size:.4f}"
        return result


def wilcoxon_signed_rank(
    sample1: Union[np.ndarray, List[float]],
    sample2: Union[np.ndarray, List[float]],
    alternative: str = 'two-sided',
    significance_level: float = 0.05
) -> HypothesisTestResult:
    """Perform Wilcoxon signed-rank test for paired samples.
    
    Non-parametric alternative to paired t-test. Tests whether the median
    difference between paired observations is zero.
    
    Parameters
    ----------
    sample1, sample2 : array-like
        Paired samples (must have same length).
    alternative : str
        Alternative hypothesis: 'two-sided', 'greater', or 'less'.
    significance_level : float
        Significance level (alpha) for the test.
        
    Returns
    -------
    HypothesisTestResult
        Test results including statistic, p-value, and decision.
        
    Notes
    -----
    Use this test when:
    - Samples are paired (e.g., same conditions, different algorithms)
    - Normality assumption is violated
    - Sample size is small (< 30)
    """
    sample1 = np.asarray(sample1)
    sample2 = np.asarray(sample2)
    
    if len(sample1) != len(sample2):
        raise ValueError("Samples must have the same length for paired test.")
    
    if len(sample1) < 6:
        raise ValueError("Wilcoxon test requires at least 6 paired observations.")
    
    # Perform Wilcoxon signed-rank test
    statistic, p_value = stats.wilcoxon(sample1, sample2, alternative=alternative)
    
    # Calculate effect size (rank-biserial correlation)
    n = len(sample1)
    differences = sample2 - sample1
    r_plus = np.sum(differences[differences > 0])
    r_minus = np.sum(np.abs(differences[differences < 0]))
    
    if r_plus + r_minus > 0:
        effect_size = (r_plus - r_minus) / (r_plus + r_minus)
    else:
        effect_size = 0.0
    
    return HypothesisTestResult(
        test_name="Wilcoxon Signed-Rank",
        statistic=float(statistic),
        p_value=float(p_value),
        null_hypothesis="Median difference between samples is zero",
        alternative_hypothesis=f"Median difference is {alternative} zero",
        significance_level=significance_level,
        reject_null=p_value < significance_level,
        effect_size=effect_size,
        notes="Non-parametric paired test; robust to outliers"
    )


def anova_oneway(
    *samples: Union[np.ndarray, List[float]],
    significance_level: float = 0.05
) -> HypothesisTestResult:
    """Perform one-way ANOVA for comparing multiple independent groups.
    
    Tests whether there are statistically significant differences between
    the means of three or more independent groups.
    
    Parameters
    ----------
    *samples : array-like
        Two or more independent samples to compare.
    significance_level : float
        Significance level (alpha) for the test.
        
    Returns
    -------
    HypothesisTestResult
        Test results including F-statistic, p-value, and decision.
        
    Notes
    -----
    Assumptions:
    - Independence of observations
    - Normality within each group
    - Homogeneity of variances (homoscedasticity)
    
    If assumptions are violated, consider Kruskal-Wallis test instead.
    """
    if len(samples) < 2:
        raise ValueError("Need at least 2 samples for ANOVA.")
    
    # Convert to numpy arrays
    samples_array = [np.asarray(s) for s in samples]
    
    # Check for minimum sample size
    for i, s in enumerate(samples_array):
        if len(s) < 2:
            raise ValueError(f"Sample {i+1} has fewer than 2 observations.")
    
    # Perform one-way ANOVA
    statistic, p_value = stats.f_oneway(*samples_array)
    
    # Calculate effect size (eta-squared)
    all_data = np.concatenate(samples_array)
    grand_mean = np.mean(all_data)
    ss_total = np.sum((all_data - grand_mean) ** 2)
    
    group_means = [np.mean(s) for s in samples_array]
    ss_between = sum(
        len(s) * (mean - grand_mean) ** 2 
        for s, mean in zip(samples_array, group_means)
    )
    
    eta_squared = ss_between / ss_total if ss_total > 0 else 0.0
    
    return HypothesisTestResult(
        test_name="One-way ANOVA",
        statistic=float(statistic),
        p_value=float(p_value),
        null_hypothesis="All group means are equal",
        alternative_hypothesis="At least one group mean differs",
        significance_level=significance_level,
        reject_null=p_value < significance_level,
        effect_size=eta_squared,
        notes=f"Effect size (η²): {eta_squared:.3f} - " + 
              ("large" if eta_squared > 0.14 else "medium" if eta_squared > 0.06 else "small")
    )


def tukey_hsd(
    *samples: Union[np.ndarray, List[float]],
    significance_level: float = 0.05
) -> Dict[Tuple[int, int], HypothesisTestResult]:
    """Perform Tukey's Honestly Significant Difference post-hoc test.
    
    Used after ANOVA to determine which specific pairs of groups differ.
    Controls family-wise error rate for multiple comparisons.
    
    Parameters
    ----------
    *samples : array-like
        Two or more independent samples to compare.
    significance_level : float
        Significance level (alpha) for the test.
        
    Returns
    -------
    dict
        Dictionary mapping (group_i, group_j) tuples to test results.
        
    Notes
    -----
    Should only be used after finding significant ANOVA result.
    Assumes equal variances across groups.
    """
    if len(samples) < 2:
        raise ValueError("Need at least 2 samples for pairwise comparisons.")
    
    samples_array = [np.asarray(s) for s in samples]
    n_groups = len(samples_array)
    
    # Combine all data for pooled variance
    all_data = np.concatenate(samples_array)
    n_total = len(all_data)
    group_sizes = [len(s) for s in samples_array]
    group_means = [np.mean(s) for s in samples_array]
    
    # Pooled variance
    ss_within = sum(np.sum((s - np.mean(s)) ** 2) for s in samples_array)
    df_within = n_total - n_groups
    ms_within = ss_within / df_within if df_within > 0 else 1.0
    
    # Studentized range statistic critical value
    from scipy.stats import tukey_hsd as scipy_tukey
    
    results = {}
    for i in range(n_groups):
        for j in range(i + 1, n_groups):
            # Mean difference
            mean_diff = group_means[j] - group_means[i]
            
            # Standard error
            se = np.sqrt(ms_within * (1/group_sizes[i] + 1/group_sizes[j]) / 2)
            
            # Q statistic
            q_stat = abs(mean_diff) / se if se > 0 else 0
            
            # P-value from studentized range distribution
            # Using approximation since scipy doesn't have direct studentized range
            df_error = df_within
            p_value = 1 - _studentized_range_cdf(q_stat, n_groups, df_error)
            
            results[(i, j)] = HypothesisTestResult(
                test_name="Tukey HSD",
                statistic=q_stat,
                p_value=float(p_value),
                null_hypothesis=f"Mean of group {i} equals mean of group {j}",
                alternative_hypothesis=f"Mean of group {i} differs from group {j}",
                significance_level=significance_level,
                reject_null=p_value < significance_level,
                effect_size=abs(mean_diff),
                notes=f"Mean diff: {mean_diff:.4f}, SE: {se:.4f}"
            )
    
    return results


def _studentized_range_cdf(q: float, k: int, df: int) -> float:
    """Approximate CDF of studentized range distribution.
    
    This is a simplified approximation. For production use, consider
    using the `statsmodels` library which has exact implementations.
    """
    # Approximation using normal distribution for large df
    if df > 100:
        # For large df, approaches normal-based calculation
        adjustment = np.sqrt(2) * stats.norm.cdf(q / np.sqrt(2)) - 1
        return adjustment ** k
    else:
        # Rough approximation for smaller df
        t_adjustment = q / np.sqrt(1 + df / (df - 2)) if df > 2 else q
        return stats.t.cdf(t_adjustment, df) ** k


class StatisticalComparison:
    """Comprehensive statistical comparison framework for MPPT algorithms.
    
    This class orchestrates multiple statistical tests to provide a complete
    analysis of performance differences between algorithms.
    
    Parameters
    ----------
    significance_level : float, default=0.05
        Alpha level for all hypothesis tests.
    n_bootstrap : int, default=1000
        Number of bootstrap samples for confidence intervals.
    
    Examples
    --------
    >>> comparator = StatisticalComparison(significance_level=0.05)
    >>> results = comparator.compare_algorithms(performance_data)
    >>> results.print_summary()
    """
    
    def __init__(
        self,
        significance_level: float = 0.05,
        n_bootstrap: int = 1000
    ):
        self.significance_level = significance_level
        self.n_bootstrap = n_bootstrap
        self.results: Dict[str, HypothesisTestResult] = {}
        self.pairwise_results: Dict[Tuple[str, str], HypothesisTestResult] = {}
    
    def compare_algorithms(
        self,
        performance_data: Dict[str, Union[np.ndarray, List[float]]],
        metric_name: str = "performance"
    ) -> 'StatisticalComparison':
        """Perform comprehensive statistical comparison of algorithms.
        
        Parameters
        ----------
        performance_data : dict
            Dictionary mapping algorithm names to performance score arrays.
        metric_name : str
            Name of the metric being compared (for reporting).
            
        Returns
        -------
        StatisticalComparison
            Self for method chaining.
        """
        algorithms = list(performance_data.keys())
        samples = [performance_data[alg] for alg in algorithms]
        
        # Overall test (ANOVA if > 2 algorithms, Wilcoxon if 2)
        if len(algorithms) >= 3:
            anova_result = anova_oneway(*samples, significance_level=self.significance_level)
            self.results['overall'] = anova_result
            
            # Post-hoc pairwise comparisons if ANOVA is significant
            if anova_result.reject_null:
                tukey_results = tukey_hsd(*samples, significance_level=self.significance_level)
                for (i, j), result in tukey_results.items():
                    alg_pair = (algorithms[i], algorithms[j])
                    self.pairwise_results[alg_pair] = result
        else:
            # Only 2 algorithms: use Wilcoxon
            result = wilcoxon_signed_rank(
                samples[0], samples[1],
                significance_level=self.significance_level
            )
            self.results['overall'] = result
            self.pairwise_results[(algorithms[0], algorithms[1])] = result
        
        return self
    
    def print_summary(self) -> None:
        """Print a formatted summary of all statistical tests."""
        print("=" * 70)
        print("STATISTICAL COMPARISON SUMMARY")
        print("=" * 70)
        
        if 'overall' in self.results:
            print(f"\nOverall Test:")
            print(f"  {self.results['overall'].summary()}")
        
        if self.pairwise_results:
            print(f"\nPairwise Comparisons:")
            for (alg1, alg2), result in self.pairwise_results.items():
                decision = "SIGNIFICANT" if result.reject_null else "NOT SIGNIFICANT"
                print(f"  {alg1} vs {alg2}: {decision} (p={result.p_value:.4g})")
                if result.effect_size is not None:
                    print(f"    Effect size: {result.effect_size:.4f}")
        
        print("\n" + "=" * 70)
    
    def generate_table(self) -> str:
        """Generate a LaTeX-ready table of statistical results.
        
        Returns
        -------
        str
            LaTeX tabular environment with statistical results.
        """
        lines = [
            "\\begin{table}[h]",
            "\\centering",
            "\\caption{Statistical Comparison of MPPT Algorithms}",
            "\\begin{tabular}{lccc}",
            "\\toprule",
            "\\textbf{Comparison} & \\textbf{Test} & \\textbf{Statistic} & \\textbf{p-value} \\\\",
            "\\midrule"
        ]
        
        for (alg1, alg2), result in self.pairwise_results.items():
            sig_marker = "*" if result.reject_null else ""
            lines.append(
                f"{alg1} vs {alg2} & {result.test_name} & "
                f"{result.statistic:.3f} & {result.p_value:.4f}{sig_marker} \\\\"
            )
        
        lines.extend([
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}"
        ])
        
        return "\n".join(lines)
