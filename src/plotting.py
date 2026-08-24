"""Figure generation from results/comparison_table.csv and src/analysis.py's
summary tables (CLAUDE.md "Plotting Conventions" / Phase 4 requirements).

Every figure follows CLAUDE.md's conventions: saved as both .png (300 DPI)
and .svg, a colorblind-safe categorical palette (Okabe & Ito, 2008 -- the
standard colorblind-safe qualitative palette), axes labeled with units, error
bars/shaded regions for Monte Carlo results, and a self-contained title
(doubling as the figure caption's core sentence).

Two kinds of figures need two different kinds of input:
  - Aggregate figures (bar charts, heatmaps) are built from a
    `analysis.summarize()` DataFrame -- no simulation needed.
  - `plot_tracking_trajectory()` needs a raw per-timestep power trace, which
    isn't in the summary CSV (only aggregate metrics are) -- callers (e.g.
    `main()` below) must re-run one illustrative scenario live via
    `scenarios.run_scenario()`/`scenarios_partial_shading.run_partial_shading_scenario()`
    and pass in the resulting RunResults directly.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import analysis

# Okabe & Ito (2008) colorblind-safe qualitative palette.
_OKABE_ITO = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
}

ALGORITHM_COLORS = {
    "p_and_o": _OKABE_ITO["blue"],
    "inc_cond": _OKABE_ITO["orange"],
    "fuzzy_logic": _OKABE_ITO["bluish_green"],
    "q_learning": _OKABE_ITO["vermillion"],
    "sliding_mode": _OKABE_ITO["reddish_purple"],
    "fuzzy_5x5": _OKABE_ITO["sky_blue"],
    "fuzzy_3x3": _OKABE_ITO["black"],
}

QL_CONDITION_COLORS = {
    "train": _OKABE_ITO["blue"],
    "held_out": _OKABE_ITO["vermillion"],
}

METRIC_LABELS = {
    "tracking_efficiency_pct": "Tracking efficiency (%)",
    "oscillation_p2p_w": "Steady-state oscillation, peak-to-peak (W)",
    "oscillation_std_w": "Steady-state oscillation, std. dev. (W)",
    "energy_yield_ratio": "Energy yield ratio (fraction of theoretical max)",
    "energy_yield_j": "Energy yield (J)",
    "convergence_time_s": "Convergence time (s)",
    "settling_time_s": "Settling time (s)",
    "convergence_rate": "Fraction of runs converged within 2% of MPP",
    "settling_rate": "Fraction of runs settled within 2% of MPP",
    "relative_burden": "Relative computational burden (P&O = 1.0)",
    "mean_step_time_s": "Mean step() execution time (s)",
}


def _color_for(name: str, fallback_cycle=list(_OKABE_ITO.values())) -> str:
    if name in ALGORITHM_COLORS:
        return ALGORITHM_COLORS[name]
    if name in QL_CONDITION_COLORS:
        return QL_CONDITION_COLORS[name]
    return fallback_cycle[hash(name) % len(fallback_cycle)]


def _save_fig(fig, output_dir: str, name: str) -> tuple:
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, f"{name}.png")
    svg_path = os.path.join(output_dir, f"{name}.svg")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, svg_path


def _yerr_from_ci(
    mean: np.ndarray, ci_low: np.ndarray, ci_high: np.ndarray
) -> np.ndarray:
    """(2, N) yerr array for matplotlib's asymmetric error bars.

    NaN half-widths (n_valid < 2, so no CI is defined) become 0 -- an
    invisible error bar rather than a matplotlib crash on NaN input; the
    underlying n_valid is still visible in the summary CSV for anyone
    checking why a given bar has no whiskers.
    """
    lower = np.nan_to_num(mean - ci_low, nan=0.0)
    upper = np.nan_to_num(ci_high - mean, nan=0.0)
    return np.vstack([lower, upper])


def _grouped_bar(
    df: pd.DataFrame,
    x_col: str,
    hue_col: str,
    title: str,
    ylabel: str,
    color_map: dict = None,
) -> plt.Figure:
    """Shared grouped-bar-chart-with-CI-error-bars renderer used by every
    aggregate comparison figure below (metric comparison, Q-learning
    train/held-out, fuzzy sensitivity)."""
    x_values = list(dict.fromkeys(df[x_col]))  # preserve first-seen order, dedup
    hue_values = list(dict.fromkeys(df[hue_col]))
    n_hue = len(hue_values)
    x_positions = np.arange(len(x_values))
    bar_width = 0.8 / max(n_hue, 1)

    fig, ax = plt.subplots(figsize=(max(6, 1.2 * len(x_values)), 5))
    for i, hue in enumerate(hue_values):
        sub = df[df[hue_col] == hue].set_index(x_col).reindex(x_values)
        offsets = x_positions + (i - (n_hue - 1) / 2) * bar_width
        color = (color_map or {}).get(hue, _color_for(hue))
        yerr = _yerr_from_ci(
            sub["mean"].to_numpy(),
            sub["ci95_low"].to_numpy(),
            sub["ci95_high"].to_numpy(),
        )
        ax.bar(
            offsets,
            sub["mean"],
            width=bar_width,
            label=str(hue),
            color=color,
            yerr=yerr,
            capsize=3,
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_values, rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    # Placed outside the axes (not loc="best") because "best" picks a corner
    # by trial data extent and reliably collides with a bar on these dense,
    # many-category charts -- e.g. it sat directly on top of the first bar
    # group in the fuzzy rule-base sensitivity figure until this fix.
    ax.legend(
        title=hue_col, frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5)
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def plot_metric_comparison(
    summary_df: pd.DataFrame,
    metric: str,
    output_dir: str,
    algorithms=analysis.CORE_ALGORITHMS,
) -> tuple:
    """Grouped bar chart: one group per scenario, one bar per algorithm,
    95% CI error bars. For tracking_efficiency_pct / oscillation_p2p_w /
    energy_yield_ratio (CLAUDE.md's core cross-scenario comparison figures)."""
    # No ql_condition filtering here: classify_ql_condition() tags a whole
    # scenario for q_learning (never splits one scenario's rows across two
    # conditions), so there is exactly one row per (q_learning, scenario) --
    # including every row shows q_learning's real cross-scenario performance
    # rather than only its 2 training-distribution scenarios, which would
    # otherwise look like a silently cherry-picked comparison. The title
    # flags which scenarios are out-of-distribution for it; see
    # plot_ql_train_vs_held_out for the dedicated train-vs-held-out figure.
    sub = summary_df[
        (summary_df["metric"] == metric)
        & (summary_df["algorithm"].isin(algorithms))
        & (summary_df["scenario"] != "_computational_burden")
    ]

    title = (
        f"{METRIC_LABELS.get(metric, metric)} by scenario\n"
        "(q_learning: held-out/untrained conditions except steady_state & step_change_irradiance -- "
        "see the train-vs-held-out figure)"
    )
    fig = _grouped_bar(
        sub,
        x_col="scenario",
        hue_col="algorithm",
        title=title,
        ylabel=METRIC_LABELS.get(metric, metric),
    )
    return _save_fig(fig, output_dir, f"metric_comparison_{metric}")


def plot_convergence_heatmap(
    summary_df: pd.DataFrame,
    output_dir: str,
    algorithms=analysis.CORE_ALGORITHMS,
    metric: str = "convergence_rate",
) -> tuple:
    """Algorithm x scenario heatmap of convergence_rate/settling_rate --
    surfaces total non-convergence (e.g. perturbative algorithms under
    partial shading) as a visible 0%-colored cell, not a missing data point."""
    sub = summary_df[
        (summary_df["metric"] == metric) & (summary_df["algorithm"].isin(algorithms))
    ]
    scenarios = sorted(sub["scenario"].unique())
    pivot = sub.pivot_table(
        index="algorithm", columns="scenario", values="mean"
    ).reindex(index=algorithms, columns=scenarios)

    fig, ax = plt.subplots(
        figsize=(max(6, 1.1 * len(scenarios)), max(3, 0.6 * len(algorithms) + 1))
    )
    # viridis, not a red-green diverging map like RdYlGn -- this heatmap's
    # natural default -- because red-green is exactly the confusion axis for
    # the most common form of color blindness; CLAUDE.md requires a
    # colorblind-safe palette and the per-cell text values are the intended
    # colorblind-safe fallback, but the color channel itself should be too.
    im = ax.imshow(pivot.to_numpy(), cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.set_yticks(range(len(algorithms)))
    ax.set_yticklabels(algorithms)
    for row in range(len(algorithms)):
        for col in range(len(scenarios)):
            value = pivot.to_numpy()[row, col]
            if not np.isnan(value):
                # viridis is dark at low values -- black text would be
                # unreadable there, so switch to white below the map's
                # perceptual midpoint (unlike the RdYlGn text color assumed
                # black always worked against a lighter red/green range).
                text_color = "white" if value < 0.5 else "black"
                ax.text(
                    col,
                    row,
                    f"{value * 100:.0f}%",
                    ha="center",
                    va="center",
                    color=text_color,
                    fontsize=8,
                )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(METRIC_LABELS.get(metric, metric))
    ax.set_title(f"{METRIC_LABELS.get(metric, metric)}, by algorithm and scenario")
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"convergence_heatmap_{metric}")


def plot_computational_burden(
    summary_df: pd.DataFrame, output_dir: str, algorithms=analysis.CORE_ALGORITHMS
) -> tuple:
    """Single bar chart of relative_burden per algorithm (P&O = 1.0 baseline)."""
    sub = (
        summary_df[
            (summary_df["metric"] == "relative_burden")
            & (summary_df["scenario"] == "_computational_burden")
            & (summary_df["algorithm"].isin(algorithms))
        ]
        .set_index("algorithm")
        .reindex(algorithms)
    )

    fig, ax = plt.subplots(figsize=(max(5, 1.2 * len(algorithms)), 4))
    colors = [_color_for(a) for a in algorithms]
    ax.bar(algorithms, sub["mean"], color=colors)
    ax.set_ylabel(METRIC_LABELS["relative_burden"])
    ax.set_title("Relative computational burden by algorithm")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, output_dir, "computational_burden")


def plot_ql_train_vs_held_out(
    summary_df: pd.DataFrame, output_dir: str, metric: str = "tracking_efficiency_pct"
) -> tuple:
    """Grouped bar: Q-learning's `metric`, split by ql_condition (train vs.
    held_out) per scenario -- CLAUDE.md's mandatory generalization check."""
    sub = summary_df[
        (summary_df["algorithm"] == "q_learning")
        & (summary_df["metric"] == metric)
        & (summary_df["ql_condition"].isin(["train", "held_out"]))
    ]
    title = (
        f"Q-learning {METRIC_LABELS.get(metric, metric)}: train vs. held-out conditions"
    )
    fig = _grouped_bar(
        sub,
        x_col="scenario",
        hue_col="ql_condition",
        title=title,
        ylabel=METRIC_LABELS.get(metric, metric),
        color_map=QL_CONDITION_COLORS,
    )
    return _save_fig(fig, output_dir, f"ql_train_vs_held_out_{metric}")


def plot_fuzzy_sensitivity(
    fuzzy_df: pd.DataFrame, output_dir: str, metric: str = "tracking_efficiency_pct"
) -> tuple:
    """Grouped bar: 7x7 (fuzzy_logic) vs. 5x5 vs. 3x3 rule-base size, per
    scenario -- CLAUDE.md's fuzzy "Sensitivity Analysis (Contribution)"."""
    sub = fuzzy_df[
        (fuzzy_df["metric"] == metric)
        & (fuzzy_df["scenario"] != "_computational_burden")
        & (
            fuzzy_df["ql_condition"] != "held_out"
            if "ql_condition" in fuzzy_df.columns
            else True
        )
    ]
    title = f"Fuzzy rule-base size sensitivity: {METRIC_LABELS.get(metric, metric)}"
    fig = _grouped_bar(
        sub,
        x_col="scenario",
        hue_col="algorithm",
        title=title,
        ylabel=METRIC_LABELS.get(metric, metric),
    )
    return _save_fig(fig, output_dir, f"fuzzy_sensitivity_{metric}")


def plot_tracking_trajectory(
    results: dict, theoretical_max_power, output_dir: str, name: str, title: str
) -> tuple:
    """Time-series power-tracking figure: one line per algorithm plus the
    theoretical max power as a dashed reference.

    `results`: dict[algorithm_name -> scenarios.RunResult] (or
    scenarios_partial_shading.RunResult, same shape), from ONE live
    simulation per algorithm -- not from the summary CSV, which only has
    aggregate metrics, no raw traces. `theoretical_max_power`: either a
    scalar (partial-shading scenarios: fixed shading pattern for the whole
    run) or an array matching each result's `times` (single-module
    scenarios where irradiance/temperature vary over time).
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    for algorithm_name, result in results.items():
        ax.plot(
            result.times,
            result.powers,
            label=algorithm_name,
            color=_color_for(algorithm_name),
            linewidth=1.5,
        )

    any_result = next(iter(results.values()))
    max_power_curve = (
        theoretical_max_power
        if np.ndim(theoretical_max_power) > 0
        else np.full_like(any_result.times, theoretical_max_power)
    )
    ax.plot(
        any_result.times,
        max_power_curve,
        label="Theoretical max",
        color="black",
        linestyle="--",
        linewidth=1.0,
    )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Power (W)")
    ax.set_title(title)
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save_fig(fig, output_dir, name)


def generate_all_aggregate_figures(
    summary_df: pd.DataFrame, fuzzy_df: pd.DataFrame, output_dir: str
) -> list:
    """Every figure that can be built from summary tables alone (no live
    re-simulation needed). Returns the list of (png_path, svg_path) pairs."""
    paths = []
    for metric in (
        "tracking_efficiency_pct",
        "oscillation_p2p_w",
        "energy_yield_ratio",
    ):
        paths.append(plot_metric_comparison(summary_df, metric, output_dir))
    paths.append(
        plot_convergence_heatmap(summary_df, output_dir, metric="convergence_rate")
    )
    paths.append(
        plot_convergence_heatmap(summary_df, output_dir, metric="settling_rate")
    )
    paths.append(plot_computational_burden(summary_df, output_dir))
    paths.append(plot_ql_train_vs_held_out(summary_df, output_dir))
    if not fuzzy_df.empty:
        paths.append(plot_fuzzy_sensitivity(fuzzy_df, output_dir))
    return paths


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate all Phase 4 figures from the MPPT comparison results."
    )
    parser.add_argument("--input", type=str, default="results/comparison_table.csv")
    parser.add_argument("--output", type=str, default="results/figures/")
    parser.add_argument(
        "--skip-trajectories",
        action="store_true",
        help="Skip the live-resimulation trajectory figures.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    summary_df = analysis.summarize(df)
    fuzzy_df = analysis.fuzzy_sensitivity_table(summary_df)

    paths = generate_all_aggregate_figures(summary_df, fuzzy_df, args.output)

    if not args.skip_trajectories:
        from . import config, scenarios, scenarios_partial_shading
        from .pv_model import TwoDiodeModel, extract_two_diode_parameters

        panel_params = extract_two_diode_parameters(
            voc=config.PANEL_VOC_STC,
            isc=config.PANEL_ISC_STC,
            vmp=config.PANEL_VMP_STC,
            imp=config.PANEL_IMP_STC,
        )
        pv_model = TwoDiodeModel(panel_params, num_cells=config.PANEL_NS)
        algorithms = scenarios.build_default_algorithms(pv_model)

        steady_scenario = scenarios.scenario_steady_state()
        steady_results = {
            name: scenarios.run_scenario(
                steady_scenario, algo, pv_model, sample_period_s=0.01
            )
            for name, algo in algorithms.items()
        }
        _, steady_mpp = pv_model.find_mpp(
            config.STC_IRRADIANCE, config.STC_TEMPERATURE_C
        )
        paths.append(
            plot_tracking_trajectory(
                steady_results,
                steady_mpp,
                args.output,
                "trajectory_steady_state",
                "Power tracking at STC (steady state)",
            )
        )

        shading_scenario = scenarios_partial_shading.scenario_partial_shading_simple()
        pv_string = scenarios_partial_shading.build_pv_string(
            panel_params, num_modules=len(shading_scenario.irradiances)
        )
        shading_results = {
            name: scenarios_partial_shading.run_partial_shading_scenario(
                shading_scenario, algo, pv_string
            )
            for name, algo in algorithms.items()
        }
        _, shading_mpp = pv_string.find_global_mpp(
            shading_scenario.irradiances, shading_scenario.temperature_c
        )
        paths.append(
            plot_tracking_trajectory(
                shading_results,
                shading_mpp,
                args.output,
                "trajectory_partial_shading_simple",
                "Power tracking under simple partial shading (1000/400 W/m^2)",
            )
        )

    print(f"Wrote {len(paths)} figures (.png + .svg each) to {args.output}")


if __name__ == "__main__":
    main()
