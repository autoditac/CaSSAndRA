import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.data.cfgdata import CommCfg, PathPlannerCfg
from src.pathdata import paths


def _commcfg_payload():
    return {
        "USE": "HTTP",
        "MQTT": [
            {"CLIENT_ID": "CaSSAndRA"},
            {"USERNAME": None},
            {"PASSWORD": None},
            {"MQTT_SERVER": "192.168.1.1"},
            {"PORT": 1883},
            {"MOWER_NAME": "ardumower/Ardumower"},
        ],
        "HTTP": [
            {"IP": "http://192.168.1.1"},
            {"PASSWORD": None},
        ],
        "UART": [
            {"SERPORT": "/dev/ttyACM0"},
            {"BAUDRATE": 115200},
        ],
        "API": None,
        "MQTT_API": [
            {"CLIENT_ID": "CaSSAndRA_api"},
            {"USERNAME": ""},
            {"PASSWORD": ""},
            {"MQTT_SERVER": "192.168.1.1"},
            {"PORT": 1883},
            {"API_SERVER_NAME": "myCaSSAndRA"},
        ],
        "MESSAGE_SERVICE": None,
        "TELEGRAM": [
            {"TOKEN": None},
            {"CHAT_ID": None},
        ],
        "PUSHOVER": [
            {"TOKEN": None},
            {"USER": None},
        ],
    }


def _set_user_paths(tmp_path, **files):
    user = SimpleNamespace(**{name: str(path) for name, path in files.items()})
    paths.file_paths = SimpleNamespace(user=user)


def test_commcfg_mqtt_api_environment_overrides(tmp_path, monkeypatch):
    commcfg_path = tmp_path / "commcfg.json"
    commcfg_path.write_text(json.dumps(_commcfg_payload()))
    _set_user_paths(tmp_path, comm=commcfg_path)

    monkeypatch.setenv("CASSANDRA_API", "MQTT")
    monkeypatch.setenv("CASSANDRA_API_MQTT_CLIENT_ID", "cassandra-alfred")
    monkeypatch.setenv("CASSANDRA_API_MQTT_USERNAME", "alfred")
    monkeypatch.setenv("CASSANDRA_API_MQTT_PASSWORD", "secret")
    monkeypatch.setenv("CASSANDRA_API_MQTT_SERVER", "mqtt.example.test")
    monkeypatch.setenv("CASSANDRA_API_MQTT_PORT", "1884")
    monkeypatch.setenv("CASSANDRA_API_MQTT_SERVER_NAME", "alfred")

    cfg = CommCfg()
    cfg.read_commcfg()

    assert cfg.api == "MQTT"
    assert cfg.api_mqtt_client_id == "cassandra-alfred"
    assert cfg.api_mqtt_username == "alfred"
    assert cfg.api_mqtt_pass == "secret"
    assert cfg.api_mqtt_server == "mqtt.example.test"
    assert cfg.api_mqtt_port == 1884
    assert cfg.api_mqtt_cassandra_server_name == "alfred"


def test_pathplannercfg_defaults_cpp_planner_for_legacy_files(tmp_path):
    pathplannercfg_path = tmp_path / "pathplannercfg.json"
    pathplannercfg_path.write_text(json.dumps({
        "pattern": "lines",
        "width": 0.18,
        "angle": 0,
        "distancetoborder": 2,
        "mowarea": True,
        "mowborder": 0,
        "mowexclusion": True,
        "mowborderccw": True,
    }))
    _set_user_paths(tmp_path, pathplannercfg=pathplannercfg_path)

    cfg = PathPlannerCfg()
    cfg.read_pathplannercfg()

    assert cfg.usecppplanner is True
    assert json.loads(pathplannercfg_path.read_text())["usecppplanner"] is True
