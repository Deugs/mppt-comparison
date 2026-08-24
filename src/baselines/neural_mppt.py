"""Neural Network based MPPT algorithm.

This module implements a simple Multi-Layer Perceptron (MLP) based MPPT
controller that learns the mapping from environmental conditions to optimal
duty cycle.

References
----------
[1] L. M. Elobaid et al., "Artificial Neural Network-Based Photovoltaic 
    Maximum Power Point Tracking Techniques," IET Renewable Power Generation, 2015.
"""

import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class MLPConfig:
    """Configuration for the neural network."""
    
    input_size: int = 2  # irradiance, temperature
    hidden_sizes: Tuple[int, ...] = (16, 8)
    output_size: int = 1  # duty cycle
    learning_rate: float = 0.01
    activation: str = 'relu'
    dropout_rate: float = 0.0
    weight_decay: float = 0.0001


class SimpleMLP:
    """Simple Multi-Layer Perceptron for MPPT.
    
    A lightweight implementation without external ML frameworks.
    Uses backpropagation with gradient descent for training.
    """
    
    def __init__(self, config: MLPConfig, random_state: Optional[int] = None):
        self.config = config
        self.rng = np.random.default_rng(random_state)
        
        # Initialize weights using He initialization
        self.layers = []
        layer_sizes = [config.input_size] + list(config.hidden_sizes) + [config.output_size]
        
        for i in range(len(layer_sizes) - 1):
            # He initialization
            scale = np.sqrt(2.0 / layer_sizes[i])
            W = self.rng.normal(0, scale, (layer_sizes[i], layer_sizes[i+1]))
            b = np.zeros((1, layer_sizes[i+1]))
            self.layers.append({'W': W, 'b': b})
        
        self.cache = {}  # For backpropagation
    
    def _activation(self, x: np.ndarray, deriv: bool = False) -> np.ndarray:
        """Apply activation function."""
        if self.config.activation == 'relu':
            if deriv:
                return (x > 0).astype(float)
            return np.maximum(0, x)
        elif self.config.activation == 'tanh':
            if deriv:
                return 1 - np.tanh(x) ** 2
            return np.tanh(x)
        elif self.config.activation == 'sigmoid':
            if deriv:
                s = 1 / (1 + np.exp(-x))
                return s * (1 - s)
            return 1 / (1 + np.exp(-x))
        else:
            if deriv:
                return np.ones_like(x)
            return x  # Linear
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Forward pass through the network.
        
        Parameters
        ----------
        X : np.ndarray
            Input features (batch_size, input_size).
            
        Returns
        -------
        np.ndarray
            Network output (batch_size, output_size).
        """
        self.cache['activations'] = [X]
        self.cache['pre_activations'] = []
        
        current = X
        for i, layer in enumerate(self.layers):
            z = current @ layer['W'] + layer['b']
            self.cache['pre_activations'].append(z)
            
            # Apply activation (except last layer)
            if i < len(self.layers) - 1:
                current = self._activation(z)
            else:
                # Output layer: sigmoid to bound duty cycle [0, 1]
                current = 1 / (1 + np.exp(-z))
            
            self.cache['activations'].append(current)
        
        return current
    
    def backward(self, y_true: np.ndarray, y_pred: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Backward pass to compute gradients.
        
        Parameters
        ----------
        y_true : np.ndarray
            Target values.
        y_pred : np.ndarray
            Predicted values.
            
        Returns
        -------
        list
            List of (grad_W, grad_b) tuples for each layer.
        """
        batch_size = y_true.shape[0]
        gradients = []
        
        # Output layer gradient (MSE loss derivative + sigmoid derivative)
        delta = (y_pred - y_true) * y_pred * (1 - y_pred)
        
        for i in reversed(range(len(self.layers))):
            # Compute gradients for this layer
            grad_W = self.cache['activations'][i].T @ delta / batch_size
            grad_b = np.mean(delta, axis=0, keepdims=True)
            
            # Add L2 regularization
            grad_W += self.config.weight_decay * self.layers[i]['W']
            
            gradients.insert(0, (grad_W, grad_b))
            
            if i > 0:
                # Propagate error to previous layer
                delta = (delta @ self.layers[i]['W'].T) * \
                       self._activation(self.cache['pre_activations'][i-1], deriv=True)
        
        return gradients
    
    def update(self, gradients: List[Tuple[np.ndarray, np.ndarray]]) -> None:
        """Update network weights using computed gradients.
        
        Parameters
        ----------
        gradients : list
            List of (grad_W, grad_b) tuples from backward pass.
        """
        for i, (grad_W, grad_b) in enumerate(gradients):
            self.layers[i]['W'] -= self.config.learning_rate * grad_W
            self.layers[i]['b'] -= self.config.learning_rate * grad_b
    
    def train_step(self, X: np.ndarray, y: np.ndarray) -> float:
        """Perform one training step.
        
        Parameters
        ----------
        X : np.ndarray
            Input features.
        y : np.ndarray
            Target values.
            
        Returns
        -------
        float
            Loss value after this step.
        """
        y_pred = self.forward(X)
        loss = np.mean((y_pred - y) ** 2)
        
        gradients = self.backward(y, y_pred)
        self.update(gradients)
        
        return loss
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions (forward pass without caching).
        
        Parameters
        ----------
        X : np.ndarray
            Input features.
            
        Returns
        -------
        np.ndarray
            Predictions.
        """
        current = X
        for i, layer in enumerate(self.layers):
            z = current @ layer['W'] + layer['b']
            if i < len(self.layers) - 1:
                current = self._activation(z)
            else:
                current = 1 / (1 + np.exp(-z))
        return current


class NeuralMPPT:
    """Neural Network-based MPPT controller.
    
    This controller uses an MLP to learn the optimal duty cycle from
    environmental conditions (irradiance and temperature).
    
    Parameters
    ----------
    hidden_sizes : tuple, default=(16, 8)
        Number of neurons in each hidden layer.
    learning_rate : float, default=0.01
        Learning rate for training.
    training_samples : int, default=100
        Number of samples to collect before online training.
    random_state : int, optional
        Random seed for reproducibility.
    
    Examples
    --------
    >>> nn_mppt = NeuralMPPT(hidden_sizes=(32, 16), learning_rate=0.001)
    >>> duty = nn_mppt.predict(irradiance=800, temperature=35)
    >>> nn_mppt.train(irradiance_batch, temp_batch, optimal_duty_batch)
    """
    
    def __init__(
        self,
        hidden_sizes: Tuple[int, ...] = (16, 8),
        learning_rate: float = 0.01,
        training_samples: int = 100,
        random_state: Optional[int] = None
    ):
        config = MLPConfig(
            hidden_sizes=hidden_sizes,
            learning_rate=learning_rate
        )
        self.network = SimpleMLP(config, random_state=random_state)
        self.training_samples = training_samples
        
        # Training buffer
        self.irradiance_buffer = []
        self.temperature_buffer = []
        self.duty_buffer = []
        
        self.training_count = 0
        self.is_trained = False
    
    def predict(self, irradiance: float, temperature: float) -> float:
        """Predict optimal duty cycle from environmental conditions.
        
        Parameters
        ----------
        irradiance : float
            Current irradiance (W/m²).
        temperature : float
            Current temperature (°C).
            
        Returns
        -------
        float
            Predicted optimal duty cycle.
        """
        # Normalize inputs
        G_norm = irradiance / 1000.0  # Normalize to [0, 1] assuming max 1000 W/m²
        T_norm = (temperature - 15) / 50.0  # Normalize around typical range
        
        X = np.array([[G_norm, T_norm]])
        duty_pred = self.network.predict(X)[0, 0]
        
        # Clip to valid range
        return np.clip(duty_pred, 0.05, 0.95)
    
    def store_sample(
        self,
        irradiance: float,
        temperature: float,
        optimal_duty: float
    ) -> bool:
        """Store a training sample.
        
        Parameters
        ----------
        irradiance : float
            Measured irradiance.
        temperature : float
            Measured temperature.
        optimal_duty : float
            Optimal duty cycle (from P&O or known optimum).
            
        Returns
        -------
        bool
            True if enough samples collected for training.
        """
        self.irradiance_buffer.append(irradiance / 1000.0)
        self.temperature_buffer.append((temperature - 15) / 50.0)
        self.duty_buffer.append(np.clip(optimal_duty, 0.05, 0.95))
        
        self.training_count += 1
        
        return self.training_count >= self.training_samples
    
    def train(self, epochs: int = 10, batch_size: int = 32) -> List[float]:
        """Train the network on collected samples.
        
        Parameters
        ----------
        epochs : int
            Number of training epochs.
        batch_size : int
            Mini-batch size.
            
        Returns
        -------
        list
            Loss history per epoch.
        """
        if self.training_count < 10:
            raise ValueError("Need at least 10 samples for training.")
        
        # Convert to numpy arrays
        X = np.array([
            self.irradiance_buffer,
            self.temperature_buffer
        ]).T
        y = np.array(self.duty_buffer).reshape(-1, 1)
        
        loss_history = []
        n_samples = len(X)
        
        for epoch in range(epochs):
            # Shuffle data
            indices = np.random.permutation(n_samples)
            X_shuffled = X[indices]
            y_shuffled = y[indices]
            
            epoch_losses = []
            
            # Mini-batch training
            for i in range(0, n_samples, batch_size):
                X_batch = X_shuffled[i:i+batch_size]
                y_batch = y_shuffled[i:i+batch_size]
                
                loss = self.network.train_step(X_batch, y_batch)
                epoch_losses.append(loss)
            
            avg_loss = np.mean(epoch_losses)
            loss_history.append(avg_loss)
        
        self.is_trained = True
        return loss_history
    
    def reset(self) -> None:
        """Reset the controller state."""
        self.irradiance_buffer = []
        self.temperature_buffer = []
        self.duty_buffer = []
        self.training_count = 0
        self.is_trained = False


class MLPTracker:
    """Wrapper for integrating Neural MPPT into simulation framework."""
    
    def __init__(self, **nn_kwargs):
        self.controller = NeuralMPPT(**nn_kwargs)
        self.current_duty = 0.5
        self.exploration_rate = 0.1  # For initial exploration
        self.last_irradiance = 1000.0  # Default STC
        self.last_temperature = 25.0   # Default STC
    
    def step(self, v: float, i: float, duty_cycle: float) -> float:
        """Execute one step and return new duty cycle.
        
        Parameters
        ----------
        v : float
            PV voltage measurement
        i : float
            PV current measurement
        duty_cycle : float
            Current duty cycle (not used directly)
            
        Returns
        -------
        float
            New duty cycle recommendation
        """
        power = v * i
        
        # Estimate irradiance and temperature from power (simplified)
        # Assume power proportional to irradiance at fixed temperature
        estimated_irradiance = 1000.0 * (power / 300.0)  # Rough estimate
        estimated_temp = 25.0  # Assume constant for now
        
        self.last_irradiance = estimated_irradiance
        self.last_temperature = estimated_temp
        
        return self.get_duty_cycle(v, i, estimated_irradiance, estimated_temp)
    
    def get_duty_cycle(
        self,
        voltage: float,
        current: float,
        irradiance: float = None,
        temperature: float = None,
        **kwargs
    ) -> float:
        """Get duty cycle from neural network controller.
        
        If not trained, uses exploration strategy.
        """
        if irradiance is not None and temperature is not None:
            if self.controller.is_trained:
                self.current_duty = self.controller.predict(irradiance, temperature)
            else:
                # Exploration: perturb around current estimate
                perturbation = np.random.uniform(-0.05, 0.05)
                self.current_duty = np.clip(self.current_duty + perturbation, 0.05, 0.95)
        else:
            # Fallback: simple perturbation
            perturbation = np.random.uniform(-0.02, 0.02)
            self.current_duty = np.clip(self.current_duty + perturbation, 0.05, 0.95)
        
        return self.current_duty
    
    def update(
        self,
        voltage: float,
        current: float,
        irradiance: float = None,
        temperature: float = None,
        **kwargs
    ) -> float:
        """Update controller with new measurements."""
        power = voltage * current
        
        # Store sample if we have environmental data
        if irradiance is not None and temperature is not None:
            # Use current duty as "optimal" (can be improved with offline training)
            self.controller.store_sample(irradiance, temperature, self.current_duty)
        
        return self.get_duty_cycle(voltage, current, irradiance, temperature)
    
    def reset(self) -> None:
        """Reset controller state."""
        self.controller.reset()
        self.current_duty = 0.5
        self.last_irradiance = 1000.0
        self.last_temperature = 25.0
