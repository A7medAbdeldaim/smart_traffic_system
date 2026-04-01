"""Optimizer configuration"""
from pydantic_settings import BaseSettings


class OptimizerConfig(BaseSettings):
    """Signal optimizer settings"""

    # Timing constraints
    min_green: int = 10  # seconds
    max_green: int = 120  # seconds
    yellow_time: int = 4  # seconds
    cycle_time: int = 180  # total cycle duration

    # Vehicle weights for density calculation
    car_weight: float = 1.0
    truck_weight: float = 2.5
    bus_weight: float = 3.0
    motorcycle_weight: float = 0.5

    # Emergency settings
    emergency_override_duration: int = 30  # seconds
    emergency_response_time_threshold: int = 2000  # milliseconds

    class Config:
        env_file = '.env'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from .env


# Global config instance
opt_config = OptimizerConfig()
