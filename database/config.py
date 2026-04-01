"""Database configuration"""
from pydantic_settings import BaseSettings
from typing import Literal


class DatabaseConfig(BaseSettings):
    """Database configuration from environment variables"""

    db_mode: Literal['sqlite', 'mysql'] = 'sqlite'

    # SQLite settings
    sqlite_db_path: str = './smart_traffic.db'

    # MySQL settings
    mysql_host: str = 'localhost'
    mysql_port: int = 3306
    mysql_user: str = 'traffic_admin'
    mysql_password: str = 'traffic_pass'
    mysql_database: str = 'smart_traffic'

    class Config:
        env_file = '.env'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from .env

    def get_database_url(self) -> str:
        """Get SQLAlchemy database URL based on mode"""
        if self.db_mode == 'sqlite':
            return f'sqlite+aiosqlite:///{self.sqlite_db_path}'
        else:
            return (
                f'mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@'
                f'{self.mysql_host}:{self.mysql_port}/{self.mysql_database}'
            )


# Global config instance
db_config = DatabaseConfig()
