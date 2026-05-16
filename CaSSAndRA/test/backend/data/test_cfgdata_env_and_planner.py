import importlib
import json
import os
import sys
import types
from types import SimpleNamespace

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

if importlib.util.find_spec("pandas") is None:
    sys.modules["pandas"] = types.ModuleType("pandas")
if importlib.util.find_spec("PIL") is None:
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")
    pil_module.Image = image_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module

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
    monkeypatch.setenv("CASSANDRA_API_MQTT_USE_TLS", "true")

    cfg = CommCfg()
    cfg.read_commcfg()

    assert cfg.api == "MQTT"
    assert cfg.api_mqtt_client_id == "cassandra-alfred"
    assert cfg.api_mqtt_username == "alfred"
    assert cfg.api_mqtt_pass == "secret"
    assert cfg.api_mqtt_server == "mqtt.example.test"
    assert cfg.api_mqtt_port == 1884
    assert cfg.api_mqtt_cassandra_server_name == "alfred"
    assert cfg.api_mqtt_use_tls is True


def test_commcfg_mqtt_api_use_tls_defaults_false_for_legacy_files(tmp_path):
    commcfg_path = tmp_path / "commcfg.json"
    commcfg_path.write_text(json.dumps(_commcfg_payload()))
    _set_user_paths(tmp_path, comm=commcfg_path)

    cfg = CommCfg()
    cfg.read_commcfg()

    assert cfg.api_mqtt_use_tls is False


def test_commcfg_save_persists_mqtt_api_use_tls(tmp_path):
    commcfg_path = tmp_path / "commcfg.json"
    _set_user_paths(tmp_path, comm=commcfg_path)

    cfg = CommCfg(api_mqtt_use_tls=True)
    cfg.save_commcfg()

    saved = json.loads(commcfg_path.read_text())
    assert saved["MQTT_API"][6] == {"USE_TLS": True}


def test_mqtt_create_configures_tls_when_requested(monkeypatch):
    created_clients = []

    class FakeClient:
        def __init__(self, client_id):
            self.client_id = client_id
            self.connection_flag = None
            self.username = None
            self.password = None
            self.tls_cert_reqs = None
            self.tls_insecure = None

        def username_pw_set(self, username, password):
            self.username = username
            self.password = password

        def tls_set(self, cert_reqs=None):
            self.tls_cert_reqs = cert_reqs

        def tls_insecure_set(self, value):
            self.tls_insecure = value

    def client_factory(client_id):
        client = FakeClient(client_id)
        created_clients.append(client)
        return client

    paho_module = types.ModuleType("paho")
    paho_mqtt_module = types.ModuleType("paho.mqtt")
    paho_client_module = types.SimpleNamespace(Client=client_factory)
    class FakeSerial:
        pass

    serial_module = types.ModuleType("serial")
    serial_module.Serial = FakeSerial
    icecream_module = types.ModuleType("icecream")
    icecream_module.ic = lambda *args, **_kwargs: args[0] if len(args) == 1 else args
    datatodf_module = types.ModuleType("src.backend.data.datatodf")
    robotinterface_module = types.ModuleType("src.backend.comm.robotinterface")
    robotinterface_module.robotInterface = types.SimpleNamespace(
        performCmd=lambda _command: None,
        onRobotMessageReceived=lambda _source, _data: None,
    )

    monkeypatch.setitem(sys.modules, "paho", paho_module)
    monkeypatch.setitem(sys.modules, "paho.mqtt", paho_mqtt_module)
    monkeypatch.setitem(sys.modules, "paho.mqtt.client", paho_client_module)
    monkeypatch.setitem(sys.modules, "serial", serial_module)
    monkeypatch.setitem(sys.modules, "icecream", icecream_module)
    monkeypatch.setitem(sys.modules, "src.backend.data.datatodf", datatodf_module)
    monkeypatch.setitem(sys.modules, "src.backend.comm.robotinterface", robotinterface_module)
    sys.modules.pop("src.backend.comm.connections", None)

    connections = importlib.import_module("src.backend.comm.connections")
    mqtt_connection = connections.MQTT()
    mqtt_connection.create({
        "CLIENT_ID": "cassandra-batman",
        "USERNAME": "batman",
        "PASSWORD": "secret",
        "MQTT_SERVER": "mqtt.example.test",
        "PORT": 8883,
        "NAME": "batman",
        "USE_TLS": True,
    }, {})

    client = created_clients[0]
    assert client.username == "batman"
    assert client.password == "secret"
    assert client.tls_cert_reqs == connections.ssl.CERT_REQUIRED
    assert client.tls_insecure is False


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
