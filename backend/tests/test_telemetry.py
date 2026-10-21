from unittest.mock import patch

from lineup_oracle.telemetry import CONNECTION_STRING, setup_telemetry

AZURE = "azure.monitor.opentelemetry.configure_azure_monitor"
AF = "agent_framework.observability.enable_instrumentation"


def test_skipped_without_connection_string():
    with patch(AZURE) as azure, patch(AF) as af:
        assert setup_telemetry({}) is False
        assert setup_telemetry({CONNECTION_STRING: ""}) is False
    azure.assert_not_called()
    af.assert_not_called()


def test_configured_once_with_connection_string():
    with patch(AZURE) as azure, patch(AF) as af:
        assert setup_telemetry({CONNECTION_STRING: "InstrumentationKey=00000000-0000-0000-0000-000000000000"}) is True
    azure.assert_called_once_with()
    af.assert_called_once_with()


def test_create_app_calls_setup_with_environment(monkeypatch):
    from lineup_oracle.api import create_app

    monkeypatch.delenv(CONNECTION_STRING, raising=False)
    with patch("lineup_oracle.api.setup_telemetry") as setup:
        create_app()
    setup.assert_called_once()
