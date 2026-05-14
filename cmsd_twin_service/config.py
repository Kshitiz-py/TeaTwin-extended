"""CMSD Twin Service local configuration."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.config import config as root_config

SAP_API_BASE = root_config.services.sap_api_base_url
MES_API_BASE = root_config.services.mes_api_base_url
POLL_INTERVAL = root_config.orchestrator.poll_interval_seconds
INITIAL_BUILD_TIMEOUT = root_config.orchestrator.initial_build_timeout_seconds
CMSD_HOST = root_config.services.cmsd_service_host
CMSD_PORT = root_config.services.cmsd_service_port
DATABASE_URL = root_config.database.url