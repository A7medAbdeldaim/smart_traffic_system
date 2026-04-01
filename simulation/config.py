"""Simulation configuration"""
from pydantic_settings import BaseSettings


class SimulationConfig(BaseSettings):
    """Simulation settings"""

    # General
    demo_mode: bool = True
    sumo_gui: bool = False
    simulation_step_length: float = 1.0

    # Traffic light timing
    cycle_time: int = 180
    min_green: int = 10
    max_green: int = 120
    yellow_time: int = 4

    # Demo mode settings
    demo_base_traffic: int = 15  # Base vehicles per lane
    demo_peak_amplitude: int = 10  # Peak variation
    demo_noise_level: float = 0.3  # Random noise (0-1)

    class Config:
        env_file = '.env'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from .env


# Global config instance
sim_config = SimulationConfig()
