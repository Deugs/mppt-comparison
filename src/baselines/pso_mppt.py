"""Particle Swarm Optimization (PSO) based MPPT algorithm.

This module implements PSO-MPPT, a metaheuristic optimization approach
that searches for the optimal duty cycle using swarm intelligence.

References
----------
[1] K. Ishaque et al., "A PSO-Based Improved MPPT Technique for PV Systems,"
    IEEE Transactions on Industrial Electronics, 2012.
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class Particle:
    """Represents a single particle in the PSO swarm."""
    
    position: float  # Duty cycle value
    velocity: float
    best_position: float
    best_fitness: float
    
    def __post_init__(self):
        if self.best_fitness is None:
            self.best_fitness = -np.inf


class PSOMPPT:
    """Particle Swarm Optimization MPPT controller.
    
    PSO is a population-based optimization algorithm inspired by social behavior
    of bird flocking. Each particle represents a candidate duty cycle solution.
    
    Parameters
    ----------
    n_particles : int, default=10
        Number of particles in the swarm.
    w : float, default=0.7
        Inertia weight (balances exploration vs exploitation).
    c1 : float, default=1.5
        Cognitive coefficient (attraction to personal best).
    c2 : float, default=1.5
        Social coefficient (attraction to global best).
    max_velocity : float, default=0.1
        Maximum velocity (change in duty cycle per iteration).
    duty_bounds : tuple, default=(0.05, 0.95)
        Valid range for duty cycle values.
    random_state : int, optional
        Random seed for reproducibility.
    
    Examples
    --------
    >>> pso = PSOMPPT(n_particles=15, w=0.8)
    >>> duty_cycle = pso.step(measured_power, irradiance)
    >>> pso.reset()  # Reset for new operating condition
    """
    
    def __init__(
        self,
        n_particles: int = 10,
        w: float = 0.7,
        c1: float = 1.5,
        c2: float = 1.5,
        max_velocity: float = 0.1,
        duty_bounds: Tuple[float, float] = (0.05, 0.95),
        random_state: Optional[int] = None
    ):
        self.n_particles = n_particles
        self.w = w  # Inertia weight
        self.c1 = c1  # Cognitive coefficient
        self.c2 = c2  # Social coefficient
        self.max_velocity = max_velocity
        self.duty_min, self.duty_max = duty_bounds
        
        self.rng = np.random.default_rng(random_state)
        self.global_best_position = None
        self.global_best_fitness = -np.inf
        self.particles = []
        self.iteration = 0
        self.initialized = False
    
    def _initialize_swarm(self) -> None:
        """Initialize particle swarm with random positions and velocities."""
        self.particles = []
        
        for _ in range(self.n_particles):
            position = self.rng.uniform(self.duty_min, self.duty_max)
            velocity = self.rng.uniform(-self.max_velocity, self.max_velocity)
            
            particle = Particle(
                position=position,
                velocity=velocity,
                best_position=position,
                best_fitness=-np.inf
            )
            self.particles.append(particle)
        
        self.global_best_position = None
        self.global_best_fitness = -np.inf
        self.initialized = True
    
    def reset(self) -> None:
        """Reset the PSO state for a new operating condition."""
        self.global_best_position = None
        self.global_best_fitness = -np.inf
        self.particles = []
        self.iteration = 0
        self.initialized = False
    
    def step(self, v: float, i: float, duty_cycle: float) -> float:
        """Execute one PSO iteration and return the best duty cycle.
        
        This wrapper allows PSO to be used in the standard MPPT interface.
        It maintains an internal buffer of recent measurements for swarm evaluation.
        
        Parameters
        ----------
        v : float
            PV voltage measurement
        i : float
            PV current measurement
        duty_cycle : float
            Current duty cycle (not used directly by PSO)
            
        Returns
        -------
        float
            Current global best duty cycle.
        """
        power = v * i
        
        if not self.initialized:
            # Initialize swarm around current duty cycle
            self._initialize_swarm()
            # Evaluate initial power at all particle positions
            self._evaluate_swarm(power)
            return self.global_best_position
        
        self.iteration += 1
        
        # Update swarm with current power measurement
        self._evaluate_swarm(power)
        
        # Update particle velocities and positions
        for particle in self.particles:
            # Generate random coefficients
            r1 = self.rng.random()
            r2 = self.rng.random()
            
            # Update velocity
            cognitive = self.c1 * r1 * (particle.best_position - particle.position)
            social = self.c2 * r2 * (self.global_best_position - particle.position)
            particle.velocity = (self.w * particle.velocity + 
                                cognitive + social)
            
            # Clip velocity
            particle.velocity = np.clip(particle.velocity, 
                                       -self.max_velocity, self.max_velocity)
            
            # Update position
            particle.position += particle.velocity
            
            # Enforce bounds
            particle.position = np.clip(particle.position, 
                                       self.duty_min, self.duty_max)
        
        return self.global_best_position
    
    def _evaluate_swarm(self, current_power: float) -> None:
        """Evaluate all particles based on current power measurement.
        
        Parameters
        ----------
        current_power : float
            Current measured power from PV system.
        """
        for particle in self.particles:
            fitness = current_power  # All particles see the same power
            
            # Update personal best
            if fitness > particle.best_fitness:
                particle.best_fitness = fitness
                particle.best_position = particle.position
            
            # Update global best
            if fitness > self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best_position = particle.position
    
    def evaluate_and_step(
        self,
        power_func: callable,
        current_duty: Optional[float] = None
    ) -> Tuple[float, float]:
        """Evaluate particles and perform PSO update.
        
        Convenience method that evaluates the power function at each particle
        position and returns the best duty cycle and its power.
        
        Parameters
        ----------
        power_func : callable
            Function that takes duty_cycle and returns measured power.
        current_duty : float, optional
            Starting duty cycle (used for first iteration).
            
        Returns
        -------
        tuple
            (best_duty_cycle, best_power)
        """
        if not self.initialized:
            self._initialize_swarm()
        
        # Evaluate power at each particle position
        power_measurements = np.zeros(self.n_particles)
        for i, particle in enumerate(self.particles):
            power_measurements[i] = power_func(particle.position)
        
        best_duty = self.step(power_measurements)
        best_power = self.global_best_fitness
        
        return best_duty, best_power
    
    def get_convergence_history(self) -> dict:
        """Get PSO convergence statistics.
        
        Returns
        -------
        dict
            Dictionary with iteration count, best fitness, etc.
        """
        return {
            'iteration': self.iteration,
            'global_best_fitness': self.global_best_fitness,
            'global_best_position': self.global_best_position,
            'n_particles': self.n_particles,
            'swarm_diversity': self._calculate_diversity()
        }
    
    def _calculate_diversity(self) -> float:
        """Calculate swarm diversity (standard deviation of positions)."""
        if not self.particles:
            return 0.0
        
        positions = [p.position for p in self.particles]
        return np.std(positions)
    
    def get_parameters(self) -> dict:
        """Get PSO hyperparameters."""
        return {
            'n_particles': self.n_particles,
            'inertia_weight': self.w,
            'cognitive_coeff': self.c1,
            'social_coeff': self.c2,
            'max_velocity': self.max_velocity,
            'duty_bounds': (self.duty_min, self.duty_max)
        }
