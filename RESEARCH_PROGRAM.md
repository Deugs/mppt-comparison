# MPPT Research Program — Multi-Paper Roadmap

Master document. `CLAUDE.md` in the project root remains the active working
plan for **Paper 1 only**. Papers 2-5 below are scoped but not started — do
not begin implementation on them until their stated dependencies are met.
This document exists so nothing from the original brainstorm gets lost, while
keeping each actual manuscript coherent enough that a reviewer can describe
its contribution in one sentence.

**Standing rule across every paper in this program:** no planning document,
CLAUDE.md, or draft may contain a specific numeric result (efficiency %,
RMSE, p-value, payoff matrix entry, etc.) unless it was actually produced by
a run. Use `[fill in from actual run]` placeholders. This was flagged as a
real problem in the single-paper draft and applies with equal force here —
more papers means more opportunities for a placeholder number to survive
into a real submission unchanged.

---

## Paper 1: Cross-Paradigm MPPT Comparison (Foundation)
**Status:** Actively planned in `CLAUDE.md`. Build this first — everything else depends on it.

**One-sentence contribution:** A reproducible, open-source comparison of MPPT
algorithms spanning four genuinely different design paradigms (perturbative,
rule-based, learning-based, model-based control), rigorously validated
against a real panel datasheet.

**Algorithms:** P&O, IncCond, Fuzzy Logic, Q-learning, Sliding Mode Control
**Reference panel:** Canadian Solar CS6P-250P (locked — do not revert to Kyocera KD240)
**Target venue:** IEEE Transactions on Energy Conversion or IEEE Journal of Photovoltaics
**Produces (reused by all later papers):** validated two-diode PV model,
boost converter model, scenario runner, Monte Carlo framework, metrics module

**Do not add to this paper:** GWO, LSTM-PPO, FOCV-P&O, SM-Fuzzy, ANN-MPPT, or
any game-theory content. They belong to Papers 2-5 below.

---

## Paper 2: Learning-Based MPPT — How Far Can Deep Learning Push Tracking, and Where Does It Break?
**Status:** Scoped, not started. **Depends on:** Paper 1's PV model, converter, and Q-learning baseline.

**One-sentence contribution:** A comparison of supervised (ANN) and deep RL
(LSTM-PPO) approaches to MPPT against the tabular Q-learning baseline from
Paper 1, with explicit, honest reporting of generalization failure on unseen
shading patterns — the ANN-MPPT design note already flags this candidly
("ANN fails on unseen shading patterns"), which is a strength if reported
directly rather than a weakness to hide.

**Algorithms:** ANN-MPPT (supervised regression), LSTM-PPO (deep RL);
Q-learning appears as a cited baseline from Paper 1, not re-implemented
**Key methodological requirement:** train/held-out split for all three
learning-based methods, reported separately — this is the paper's actual
spine, not a side detail
**Target venue:** IEEE Journal of Photovoltaics or IEEE Access (ML-in-PV work
often lands well here; TEC is more conservative about ML-heavy contributions)
**Reused from Paper 1:** PV model, converter, scenario suite (extend with the
specific shading-pattern train/test split design)
**New infrastructure needed:** PyTorch training pipeline, training-data
generation via exhaustive duty-cycle sweep (already sketched in the archived
notes — see Appendix below)

---

## Paper 3: Metaheuristic MPPT for Complex Partial Shading — A Fair Benchmark, Not Another Proposal
**Status:** Scoped, not started. **Depends on:** Paper 1's PV model, converter, PSC scenario suite.

**One-sentence contribution:** Rather than proposing yet another bio-inspired
optimizer (the pattern reviewers are fatigued by), this paper positions
itself as a rigorous, reproducible *benchmark* of existing metaheuristics
under a shared, validated simulation — filling the actual gap, which is fair
comparison infrastructure, not more optimizers.

**Algorithms:** GWO-MPPT, plus at least one contrasting metaheuristic (do not
submit with GWO alone — a single bio-inspired algorithm invites the "why this
one" objection; pick a second one, e.g. Particle Swarm or Whale Optimization,
during scoping)
**Target venue:** IEEE Access (the framing — "reproducible benchmark" — fits
Access's lower novelty bar better than TEC/TIE, and sidesteps the credibility
problem of proposing a single new optimizer to a skeptical Transactions reviewer)
**Reused from Paper 1:** PV model, converter, PSC scenario definitions

---

## Paper 4: Game-Theoretic Meta-Controller for Adaptive MPPT Algorithm Selection
**Status:** Scoped, not started. **Depends on:** Paper 1 (and ideally Paper 3) Monte Carlo results as real payoff data.

**One-sentence contribution:** Formalizes MPPT algorithm selection as a
normal-form game, proves no single algorithm dominates all scenarios (using
*actual* Monte Carlo payoff data from Papers 1 and 3, not the illustrative
matrix in the archived notes), and derives a meta-controller via replicator
dynamics that adaptively switches algorithms.

**Content:** Normal-form game + Nash equilibrium analysis, evolutionary game
/ replicator dynamics + ESS analysis, the `MetaMPPT` and `EvolutionaryMPPT`
controller designs already sketched in the archived notes
**Why this sequencing matters:** the entire payoff matrix this paper analyzes
must come from real numbers your earlier papers actually measured — this is
the clearest case in the whole program where building out of order would
force you to fabricate the input data
**Target venue:** this is your highest-novelty piece — worth aiming at IEEE
TIE or a controls-focused venue rather than defaulting to TEC
**Citations already identified:** Nash (1950), Taylor & Jonker (1978)

---

## Paper 5: Cooperative Game-Theoretic Power Allocation for Multi-Converter PV Arrays
**Status:** Scoped, not started — treat as a stretch goal / second research phase.
**Depends on:** new simulation infrastructure, not just Paper 1's codebase.

**One-sentence contribution:** Models multi-converter PV systems (e.g.,
micro-inverters, string optimizers) as a cooperative/Stackelberg game,
showing coordinated MPPT via Shapley-value allocation outperforms
independent per-converter tracking.

**Why this is its own paper, not a section:** it requires modeling electrical
coupling between multiple converters — a fundamentally different system
architecture than the single-converter tracking problem every other paper in
this program addresses. This isn't a small extension; budget it as a
separate project.

**Content:** Shapley value fair allocation, Stackelberg leader-follower
hierarchy, Nash bargaining solution, the multi-converter simulation scenario
(3 converters, series-parallel, differential shading) already sketched in
the archived notes
**Target venue:** IEEE TIE or TEC, given the systems-level contribution
**Citation already identified:** Chen (2025), *Systems*, cooperative game PV/storage

---

## Content Folded In Rather Than Given Its Own Paper

**FOCV-P&O hybrid and SM-Fuzzy** — both are real, citable, implementable
ideas, but individually incremental (FOCV-P&O: "simplest hardware
implementation," low novelty per your own Appendix E rating; SM-Fuzzy:
fixes a specific SMC failure mode). Recommendation: add both as extra
baseline algorithms in **Paper 1's supplementary material** rather than
inventing a sixth paper around them. If you later want a quick, low-effort
publication, they could become a short IEEE Access or Letters-format paper
on hardware-oriented MPPT — but that's optional, not required for this
program to be complete.

---

## Sequencing Summary

```
Paper 1 (Foundation)
   |
   |-- unlocks --> Paper 2 (Learning-based deep dive)
   |-- unlocks --> Paper 3 (Metaheuristic benchmark)
                        |
                        |-- (with Paper 1) unlocks --> Paper 4 (Game-theoretic meta-controller)

Paper 5 (Multi-converter cooperative game) -- independent track,
   needs new infrastructure, start whenever capacity allows
```

Realistic expectation: Paper 1 alone is a semester-scale commitment (per its
own CLAUDE.md timeline reality check). This is a multi-year research program,
not a single "big" paper. That's a legitimate and good thing to be doing —
just worth naming plainly so the plan doesn't quietly slide back into trying
to cram five papers' worth of contribution into one submission.
