"""
Shared configuration for SAP/MES → CMSD Digital Twin services.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class DatabaseConfig:
    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", "3306"))
    user: str = os.getenv("MYSQL_USER", "factory_user")
    password: str = os.getenv("MYSQL_PASSWORD", "factory_pass")
    database: str = os.getenv("MYSQL_DATABASE", "factory_digital_twin")

    @property
    def url(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_url(self) -> str:
        return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class ServiceConfig:
    sap_api_base_url: str = os.getenv("SAP_API_URL", "http://localhost:8001/api/sap/v1")
    mes_api_base_url: str = os.getenv("MES_API_URL", "http://localhost:8002/api/mes/v1")
    cmsd_service_host: str = os.getenv("CMSD_HOST", "0.0.0.0")
    cmsd_service_port: int = int(os.getenv("CMSD_PORT", "8000"))


@dataclass
class OrchestratorConfig:
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL", "10"))
    initial_build_timeout_seconds: int = int(os.getenv("INITIAL_BUILD_TIMEOUT", "60"))


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    services: ServiceConfig = field(default_factory=ServiceConfig)
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)


# Singleton
config = AppConfig()