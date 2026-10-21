"""Trace export to Application Insights, switched on only by its connection string."""
from __future__ import annotations

from collections.abc import Mapping

CONNECTION_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"


def setup_telemetry(env: Mapping[str, str]) -> bool:
    """Configure the Azure Monitor distro and Agent Framework tracing; return whether it ran."""
    if not env.get(CONNECTION_STRING):
        return False
    from agent_framework.observability import enable_instrumentation
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor()  # reads the connection string from the environment
    enable_instrumentation()  # sensitive data (prompts, replies) stays off
    return True
