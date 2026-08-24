"""Tabular Q-learning MPPT controller (model-free, learning-based).

State: discretized (V, dP/dV). Action: {decrease, hold, increase} duty cycle
by a fixed step, mirroring P&O's action set for a fair cross-paradigm
comparison (CLAUDE.md). Training and deployment are separate by design:
`train_q_learning()` runs the epsilon-greedy training loop and mutates the
agent's Q-table in place; `QLearning.step()` (the MPPTAlgorithm interface
method) is greedy-only, matching how a trained policy is actually deployed.

Reward design note (flag for CLAUDE.md's mandatory Q-learning citation):
using raw instantaneous power P(k) as the reward, as CLAUDE.md lists as one
of two options, produced a policy that got permanently stuck 2-3 V past the
true MPP for some training irradiances. Cause: coarse voltage discretization
can keep the operating point in the *same* state bin for several consecutive
steps while it drifts away from the MPP, and the reward (tied to that bin's
power level) barely changes between those steps -- there's nothing in the
signal telling the agent the drift is bad. Switching to CLAUDE.md's other
listed option, reward = P(k) - P(k-1), fixed this: it penalizes power-losing
actions directly and immediately, regardless of which state bin they land in.

Citation (CLAUDE.md, mandatory): Kofinas, P., Doltsinis, S., Dounis, A.I.,
and Vouros, G.A. (2017). "A reinforcement learning approach for MPPT control
method of photovoltaic sources." Renewable Energy, 108, 461-473.
"""

import random

import numpy as np

from .. import config
from ..simulate import pv_operating_point
from .base import MPPTAlgorithm


class QLearning(MPPTAlgorithm):
    def __init__(
        self,
        n_voltage_bins: int = config.QL_N_VOLTAGE_BINS,
        n_dpdv_bins: int = config.QL_N_DPDV_BINS,
        dpdv_scale: float = config.QL_DPDV_SCALE,
        action_step: float = config.QL_ACTION_STEP,
        voltage_max: float = config.PANEL_VOC_STC,
        duty_min: float = config.MPPT_DUTY_MIN,
        duty_max: float = config.MPPT_DUTY_MAX,
    ):
        self.n_voltage_bins = n_voltage_bins
        self.n_dpdv_bins = n_dpdv_bins
        self.dpdv_scale = dpdv_scale
        self.actions = [-action_step, 0.0, action_step]
        self.voltage_max = voltage_max
        self.duty_min = duty_min
        self.duty_max = duty_max
        self.q_table = np.zeros((n_voltage_bins, n_dpdv_bins, len(self.actions)))
        self.reset()

    def reset(self) -> None:
        self._v_prev = None
        self._p_prev = None

    def discretize(self, v: float, dpdv: float) -> tuple:
        v_bin = int(np.clip(v / self.voltage_max, 0.0, 0.999999) * self.n_voltage_bins)
        e = np.clip(dpdv / self.dpdv_scale, -1.0, 1.0)
        dpdv_bin = int(np.clip((e + 1.0) / 2.0, 0.0, 0.999999) * self.n_dpdv_bins)
        return v_bin, dpdv_bin

    def step(self, v: float, i: float, duty_cycle: float) -> float:
        p = v * i

        if self._v_prev is None:
            self._v_prev, self._p_prev = v, p
            # No dV history yet -- bootstrap with a step in the positive
            # action direction so the next call has a dV to work with.
            return min(max(duty_cycle + self.actions[-1], self.duty_min), self.duty_max)

        dv = v - self._v_prev
        dp = p - self._p_prev
        dpdv = dp / dv if abs(dv) > 1e-9 else 0.0

        state = self.discretize(v, dpdv)
        action_index = int(np.argmax(self.q_table[state]))
        new_duty = duty_cycle + self.actions[action_index]

        self._v_prev, self._p_prev = v, p
        return min(max(new_duty, self.duty_min), self.duty_max)


def train_q_learning(
    agent: QLearning,
    pv_model,
    irradiances=config.QL_TRAINING_IRRADIANCES,
    episodes: int = config.QL_TRAINING_EPISODES,
    steps_per_episode: int = config.QL_STEPS_PER_EPISODE,
    alpha: float = config.QL_ALPHA,
    gamma: float = config.QL_GAMMA,
    epsilon_start: float = config.QL_EPSILON_START,
    epsilon_min: float = config.QL_EPSILON_MIN,
    epsilon_decay: float = config.QL_EPSILON_DECAY,
    initial_duty: float = 0.3,
    temperature_c: float = config.STC_TEMPERATURE_C,
    seed: int = 0,
) -> QLearning:
    """Train `agent`'s Q-table in place via epsilon-greedy Q-learning.

    Cycles through `irradiances` round-robin across episodes (deterministic
    and reproducible given `seed`). Reward is the change in power between
    consecutive operating points -- see the module docstring for why.
    """
    rng = random.Random(seed)

    for episode in range(episodes):
        irradiance = irradiances[episode % len(irradiances)]
        epsilon = max(epsilon_min, epsilon_start * (epsilon_decay**episode))

        duty = initial_duty
        v_prev, i_prev = pv_operating_point(
            pv_model, duty, irradiance=irradiance, temperature_c=temperature_c
        )
        p_prev = v_prev * i_prev
        # Bootstrap: one step with no learning update, so the main loop
        # always has a dV/dP history to compute dP/dV from.
        duty = min(max(duty + agent.actions[-1], agent.duty_min), agent.duty_max)
        v, i = pv_operating_point(
            pv_model, duty, irradiance=irradiance, temperature_c=temperature_c
        )
        p = v * i

        for _ in range(steps_per_episode):
            dv = v - v_prev
            dp = p - p_prev
            dpdv = dp / dv if abs(dv) > 1e-9 else 0.0
            state = agent.discretize(v, dpdv)

            if rng.random() < epsilon:
                action_index = rng.randrange(len(agent.actions))
            else:
                action_index = int(np.argmax(agent.q_table[state]))

            new_duty = min(
                max(duty + agent.actions[action_index], agent.duty_min), agent.duty_max
            )
            v_new, i_new = pv_operating_point(
                pv_model, new_duty, irradiance=irradiance, temperature_c=temperature_c
            )
            p_new = v_new * i_new
            reward = p_new - p

            dv_new = v_new - v
            dp_new = p_new - p
            dpdv_new = dp_new / dv_new if abs(dv_new) > 1e-9 else 0.0
            next_state = agent.discretize(v_new, dpdv_new)

            best_next = np.max(agent.q_table[next_state])
            td_error = reward + gamma * best_next - agent.q_table[state][action_index]
            agent.q_table[state][action_index] += alpha * td_error

            v_prev, p_prev = v, p
            v, i, p, duty = v_new, i_new, p_new, new_duty

    return agent
