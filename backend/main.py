"""
IRIS — launch backend.

Responsibilities:
  - Start/stop ROS 2 launch profiles via subprocess
  - Report current process state
  - Stream stdout/stderr over WebSocket for the debug overlay

Run standalone:
    uvicorn main:app --host 0.0.0.0 --port 8000

Or via the provided run.sh which handles everything.
"""
from __future__ import annotations

import asyncio
import datetime
import os
import shlex
import signal
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

try:
    import rclpy
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String as StdString
    from inha_interfaces.srv import UiCommand
except ImportError:
    rclpy = None
    DiagnosticArray = None
    DiagnosticStatus = None
    Context = None
    SingleThreadedExecutor = None
    Node = None
    DurabilityPolicy = None
    HistoryPolicy = None
    QoSProfile = None
    ReliabilityPolicy = None
    StdString = None
    UiCommand = None

# ─────────────────────────────────────────────────────────────
# Config — edit profiles.yaml to match your launch setup
# ─────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "profiles.yaml"
GREENWAVE_CONFIG_PATH = Path(__file__).parent / "greenwave_topics.yaml"
LOG_BUFFER_SIZE = 50000  # lines kept per profile (full session log; cleared on stop)
LOG_SAVE_ROOT = Path("/home/thor/inha_ws/dryrun_log")
POSE_SCRIPT = Path("/home/thor/inha_scripts/default/robot_defaultpose.sh")
POSE_NAMES = {"zero", "ready", "packing"}
POSE_TIMEOUT_SEC = 60.0
DEFAULT_GREENWAVE_TOPICS = [
    "/scan",
    "/odom",
    "/color/image_raw",
    "/depth/image_raw",
    "/tf",
    "/joint_states",
]
DEFAULT_STALE_AFTER_SEC = 3.0
MISSION_LABELS = {
    "hri": "HRI",
    "pp": "Pick and Place",
    "restaurant": "Restaurant",
    "gpsr": "GPSR",
    "laundry": "Laundry",
    "final": "Final",
}
BAG_RECORD_PROFILE = "bag_record"
COMMON_VLM_NODES = [
    "/vlm_action_server",
    "/camera/camera_head",
    "/camera/camera_left",
    "/camera/camera_right",
]
VOICE_MISSION_NODES = [
    "/tts_node",
    "/whisper_node",
]
MISSION_NODE_TARGETS = {
    "hri": [
        "/align_to_person_node",
        "/bell_detect_action_server",
        "/camera/camera_head",
        "/camera/camera_left",
        "/camera/camera_right",
        "/face_node",
        "/human_following",
        "/tts_node",
        "/vlm_action_server",
        "/whisper_node",
    ],
    "pp": [
        *COMMON_VLM_NODES,
    ],
    "restaurant": [
        "/align_to_person_node",
        "/approach_node",
        "/camera/camera_head",
        "/camera/camera_left",
        "/camera/camera_right",
        "/detection_stability_node",
        "/face_node",
        "/generic_object_detection_node",
        "/gesture_detection_node",
        "/retreat_node",
        "/tts_node",
        "/vlm_action_server",
        "/whisper_node",
    ],
    "gpsr": [
        *VOICE_MISSION_NODES,
        *COMMON_VLM_NODES,
        "/face_node",
        "/human_following",
    ],
    "laundry": [
        *VOICE_MISSION_NODES,
        *COMMON_VLM_NODES,
    ],
    "final": [
        *VOICE_MISSION_NODES,
        *COMMON_VLM_NODES,
    ],
}
DEFAULT_ROS_DOMAIN_ID = os.environ.get("ROS_DOMAIN_ID", "101")
DEFAULT_RMW_IMPLEMENTATION = os.environ.get("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp")
ROS_NODE_LIST_TIMEOUT_SEC = float(os.environ.get("ROS_NODE_LIST_TIMEOUT_SEC", "2.5"))
ROS_NODE_LIST_SOURCE_CMD = os.environ.get(
    "ROS_NODE_LIST_SOURCE_CMD",
    "if [ -f /opt/ros/jazzy/setup.bash ]; then source /opt/ros/jazzy/setup.bash; fi",
)
AUDIO_CHECK_TIMEOUT_SEC = float(os.environ.get("AUDIO_CHECK_TIMEOUT_SEC", "2.0"))
EXPECTED_AUDIO_SINK = os.environ.get(
    "EXPECTED_AUDIO_SINK",
    "alsa_output.usb-TTGK_Technology_USB_Audio_33022920230925-00.analog-stereo",
)
EXPECTED_AUDIO_SOURCE = os.environ.get(
    "EXPECTED_AUDIO_SOURCE",
    "alsa_input.usb-SEEED_ReSpeaker_4_Mic_Array__UAC1.0_-00.analog-surround-21",
)
SIGNAL_EXIT_NAMES = {
    signal.SIGINT: "SIGINT",
    signal.SIGTERM: "SIGTERM",
    signal.SIGKILL: "SIGKILL",
}


def load_profiles() -> Dict[str, dict]:
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("profiles", {})


def load_greenwave_config() -> dict:
    if not GREENWAVE_CONFIG_PATH.exists():
        return {
            "topics": DEFAULT_GREENWAVE_TOPICS,
            "stale_after_sec": DEFAULT_STALE_AFTER_SEC,
        }

    with open(GREENWAVE_CONFIG_PATH) as f:
        data = yaml.safe_load(f) or {}

    topics = [topic for topic in data.get("topics", DEFAULT_GREENWAVE_TOPICS) if isinstance(topic, str) and topic]
    try:
        stale_after_sec = max(float(data.get("stale_after_sec", DEFAULT_STALE_AFTER_SEC)), 1.0)
    except (TypeError, ValueError):
        stale_after_sec = DEFAULT_STALE_AFTER_SEC

    return {
        "topics": topics or DEFAULT_GREENWAVE_TOPICS,
        "stale_after_sec": stale_after_sec,
    }


def normalize_mission_id(mission: Optional[str]) -> str:
    mission_id = (mission or "hri").strip().lower()
    if mission_id not in MISSION_NODE_TARGETS:
        raise ValueError(f"Unknown mission: {mission_id}")
    return mission_id


def format_process_exit(rc: Optional[int]) -> str:
    if rc is None:
        return "unknown"
    if rc < 0:
        signal_num = -rc
        signal_name = SIGNAL_EXIT_NAMES.get(signal_num, f"SIG{signal_num}")
        return f"terminated by {signal_name}"
    return f"exit {rc}"


def has_cleanup_failure_marker(entries: deque) -> bool:
    failure_markers = (
        "cleanup verification failed",
        "remote process still alive after kill:",
    )
    for entry in reversed(entries):
        line = entry.get("line", "")
        if any(marker in line for marker in failure_markers):
            return True
    return False


def build_ros_nodes_payload(mission_id: str, active_nodes: list[str], available: bool, error: Optional[str]) -> dict:
    targets = MISSION_NODE_TARGETS[mission_id]
    active_lookup = set(active_nodes)
    return {
        "available": available,
        "mission": mission_id,
        "mission_label": MISSION_LABELS.get(mission_id, mission_id.upper()),
        "domain_id": DEFAULT_ROS_DOMAIN_ID,
        "rmw_implementation": DEFAULT_RMW_IMPLEMENTATION,
        "targets": targets,
        "nodes": [
            {"name": name, "online": name in active_lookup}
            for name in targets
        ],
        "active": active_nodes,
        "error": error,
    }



async def sample_ros_nodes(mission: Optional[str] = "hri") -> dict:
    mission_id = normalize_mission_id(mission)
    env = {
        **os.environ,
        "ROS_DOMAIN_ID": DEFAULT_ROS_DOMAIN_ID,
        "RMW_IMPLEMENTATION": DEFAULT_RMW_IMPLEMENTATION,
    }
    shell_cmd = f"{ROS_NODE_LIST_SOURCE_CMD} >/dev/null 2>&1; ros2 node list"

    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", "-lc", shell_cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
    except OSError as exc:
        return build_ros_nodes_payload(mission_id, active_nodes=[], available=False, error=str(exc))

    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=ROS_NODE_LIST_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return build_ros_nodes_payload(mission_id, active_nodes=[], available=False, error="ros2 node list timeout")

    if proc.returncode != 0:
        stderr_text = err.decode(errors="replace").strip()
        return build_ros_nodes_payload(
            mission_id,
            active_nodes=[],
            available=False,
            error=stderr_text or f"ros2 node list exited with code {proc.returncode}",
        )

    active_nodes = sorted({
        line.strip()
        for line in out.decode(errors="replace").splitlines()
        if line.strip()
    })
    return build_ros_nodes_payload(mission_id, active_nodes=active_nodes, available=True, error=None)


def parse_pactl_defaults(text: str) -> dict:
    defaults = {"sink": None, "source": None}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if key == "Default Sink":
            defaults["sink"] = value
        elif key == "Default Source":
            defaults["source"] = value
    return defaults


def build_audio_defaults_payload(
    default_sink: Optional[str],
    default_source: Optional[str],
    available: bool,
    error: Optional[str],
) -> dict:
    sink_ok = default_sink == EXPECTED_AUDIO_SINK
    source_ok = default_source == EXPECTED_AUDIO_SOURCE
    return {
        "available": available,
        "ok": available and sink_ok and source_ok,
        "sink": {
            "label": "Default Sink",
            "actual": default_sink,
            "expected": EXPECTED_AUDIO_SINK,
            "ok": sink_ok,
        },
        "source": {
            "label": "Default Source",
            "actual": default_source,
            "expected": EXPECTED_AUDIO_SOURCE,
            "ok": source_ok,
        },
        "error": error,
    }


async def sample_audio_defaults() -> dict:
    try:
        proc = await asyncio.create_subprocess_exec(
            "pactl", "info",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return build_audio_defaults_payload(None, None, available=False, error=str(exc))

    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=AUDIO_CHECK_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return build_audio_defaults_payload(None, None, available=False, error="pactl info timeout")

    if proc.returncode != 0:
        stderr_text = err.decode(errors="replace").strip()
        return build_audio_defaults_payload(
            None,
            None,
            available=False,
            error=stderr_text or f"pactl info exited with code {proc.returncode}",
        )

    defaults = parse_pactl_defaults(out.decode(errors="replace"))
    return build_audio_defaults_payload(
        defaults["sink"],
        defaults["source"],
        available=True,
        error=None,
    )


# ─────────────────────────────────────────────────────────────
# Process manager
# ─────────────────────────────────────────────────────────────
@dataclass
class ManagedProcess:
    profile: str
    command: str
    strict_stop: bool = False
    allow_quick_exit: bool = False
    stop_grace_sec: float = 5.0
    stop_term_sec: float = 3.0
    process: Optional[asyncio.subprocess.Process] = None
    started_at: Optional[float] = None
    last_exit_code: Optional[int] = None
    last_exit_at: Optional[float] = None
    log_buffer: deque = field(default_factory=lambda: deque(maxlen=LOG_BUFFER_SIZE))
    subscribers: set = field(default_factory=set)

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    @property
    def pid(self) -> Optional[int]:
        return self.process.pid if self.process else None


@dataclass
class TopicSnapshot:
    name: str
    status: str = "NO_DATA"
    pub_rate: str = "-"
    expected_frequency: str = "-"
    latency: str = "-"
    last_update: float = 0.0


class GreenwaveSnapshotBridge:
    def __init__(self, topic_names: list[str], stale_after_sec: float):
        self.topic_names = list(dict.fromkeys(topic_names))
        self.stale_after_sec = stale_after_sec
        self._lock = threading.Lock()
        self._snapshots = {
            topic: TopicSnapshot(name=topic)
            for topic in self.topic_names
        }
        self._running = False
        self._started = False
        self._error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._context = None
        self._executor = None
        self._node = None
        self._subscription = None

    @property
    def available(self) -> bool:
        return all([
            rclpy is not None,
            DiagnosticArray is not None,
            DiagnosticStatus is not None,
            Context is not None,
            SingleThreadedExecutor is not None,
            Node is not None,
        ])

    def start(self):
        if not self.available or self._running:
            if not self.available:
                self._error = "rclpy or diagnostic_msgs is not available in backend environment"
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._spin_loop,
            name="greenwave-snapshot-bridge",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False

        if self._executor is not None:
            self._executor.wake()

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _spin_loop(self):
        try:
            self._context = Context()
            rclpy.init(args=None, context=self._context)
            self._node = Node("iris_greenwave_bridge", context=self._context)
            self._subscription = self._node.create_subscription(
                DiagnosticArray,
                "/diagnostics",
                self._on_diagnostics,
                100,
            )
            self._executor = SingleThreadedExecutor(context=self._context)
            self._executor.add_node(self._node)
            self._started = True
            self._error = None

            while self._running and self._context.ok():
                self._executor.spin_once(timeout_sec=0.5)
        except Exception as exc:
            self._error = str(exc)
        finally:
            self._running = False
            self._started = False
            self._teardown_ros()

    def _teardown_ros(self):
        if self._executor is not None:
            try:
                if self._node is not None:
                    self._executor.remove_node(self._node)
                self._executor.shutdown()
            except Exception:
                pass
            self._executor = None

        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None

        if self._context is not None:
            try:
                if self._context.ok():
                    self._context.shutdown()
            except Exception:
                pass
            self._context = None

        self._subscription = None

    def _extract_topic_name(self, diagnostic_name: str) -> str:
        if diagnostic_name.startswith("/"):
            return diagnostic_name

        idx = diagnostic_name.find("/")
        if idx >= 0:
            return diagnostic_name[idx:]
        return diagnostic_name

    def _get_value(self, status, key: str) -> str:
        for kv in status.values:
            if kv.key == key:
                return kv.value
        return "-"

    def _map_status(self, level: int) -> str:
        if DiagnosticStatus is None:
            return "UNKNOWN"
        if level == DiagnosticStatus.OK:
            return "OK"
        if level == DiagnosticStatus.WARN:
            return "WARN"
        if level == DiagnosticStatus.ERROR:
            return "ERROR"
        if level == DiagnosticStatus.STALE:
            return "STALE"
        return "UNKNOWN"

    def _float_or_none(self, value: str) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _status_class(self, status: str) -> str:
        if status == "OK":
            return "ok"
        if status in {"WARN", "STALE"}:
            return "warn"
        if status == "ERROR":
            return "err"
        return "idle"

    def _on_diagnostics(self, msg):
        now = time.time()
        updates = {}

        for status in msg.status:
            topic_name = self._extract_topic_name(status.name)
            if topic_name not in self._snapshots:
                continue

            updates[topic_name] = TopicSnapshot(
                name=topic_name,
                status=self._map_status(status.level),
                pub_rate=self._get_value(status, "frame_rate_node"),
                expected_frequency=self._get_value(status, "expected_frequency"),
                latency=self._get_value(status, "current_delay_from_realtime_ms"),
                last_update=now,
            )

        if not updates:
            return

        with self._lock:
            self._snapshots.update(updates)

    def _serialize_snapshot(self, snapshot: TopicSnapshot, now: float) -> dict:
        monitored = snapshot.last_update > 0.0
        age_s = (now - snapshot.last_update) if monitored else None
        status = snapshot.status

        if monitored and age_s is not None and age_s > self.stale_after_sec:
            status = "STALE"
        elif not monitored:
            status = "NO_DATA"

        pub_rate_hz = self._float_or_none(snapshot.pub_rate)
        expected_hz = self._float_or_none(snapshot.expected_frequency)
        latency_ms = self._float_or_none(snapshot.latency)

        return {
            "name": snapshot.name,
            "status": status,
            "status_class": self._status_class(status),
            "monitored": monitored,
            "ok": status == "OK",
            "pub_rate_hz": pub_rate_hz,
            "expected_hz": expected_hz,
            "latency_ms": latency_ms,
            "pub_rate_label": snapshot.pub_rate if monitored else "-",
            "expected_label": snapshot.expected_frequency if monitored else "-",
            "latency_label": snapshot.latency if monitored else "-",
            "age_s": round(age_s, 1) if age_s is not None else None,
        }

    def topics_payload(self) -> dict:
        now = time.time()

        with self._lock:
            topics = [
                self._serialize_snapshot(self._snapshots[name], now)
                for name in self.topic_names
            ]

        ok_count = sum(topic["status"] == "OK" for topic in topics)
        monitored_count = sum(topic["monitored"] for topic in topics)

        return {
            "available": self.available,
            "connected": self._started and not self._error,
            "error": self._error,
            "summary": {
                "total": len(topics),
                "monitored": monitored_count,
                "ok": ok_count,
            },
            "topics": topics,
        }


class BtStateBridge:
    """Subscribe to /bt/state with TRANSIENT_LOCAL QoS and expose the latest
    string value over REST. Bridges around rosbridge_server's QoS limitations."""

    def __init__(self):
        self._lock = threading.Lock()
        self._latest: Optional[str] = None
        self._last_update: float = 0.0
        self._running = False
        self._started = False
        self._error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._context = None
        self._executor = None
        self._node = None
        self._subscription = None

    @property
    def available(self) -> bool:
        return all([
            rclpy is not None,
            Context is not None,
            SingleThreadedExecutor is not None,
            Node is not None,
            QoSProfile is not None,
            StdString is not None,
        ])

    def start(self):
        if not self.available or self._running:
            if not self.available:
                self._error = "rclpy or std_msgs is not available in backend environment"
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._spin_loop,
            name="iris-bt-state-bridge",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._executor is not None:
            self._executor.wake()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _spin_loop(self):
        try:
            self._context = Context()
            rclpy.init(args=None, context=self._context)
            self._node = Node("iris_bt_state_bridge", context=self._context)

            qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                history=HistoryPolicy.KEEP_LAST,
                depth=1,
            )
            self._subscription = self._node.create_subscription(
                StdString, "/bt/state", self._on_state, qos
            )
            self._executor = SingleThreadedExecutor(context=self._context)
            self._executor.add_node(self._node)
            self._started = True
            self._error = None

            while self._running and self._context.ok():
                self._executor.spin_once(timeout_sec=0.5)
        except Exception as exc:
            self._error = str(exc)
        finally:
            self._running = False
            self._started = False
            self._teardown_ros()

    def _teardown_ros(self):
        if self._executor is not None:
            try:
                if self._node is not None:
                    self._executor.remove_node(self._node)
                self._executor.shutdown()
            except Exception:
                pass
            self._executor = None

        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None

        if self._context is not None:
            try:
                if self._context.ok():
                    self._context.shutdown()
            except Exception:
                pass
            self._context = None

        self._subscription = None

    def _on_state(self, msg):
        with self._lock:
            self._latest = msg.data
            self._last_update = time.time()

    def payload(self) -> dict:
        with self._lock:
            latest = self._latest
            last_update = self._last_update
        age_s = (time.time() - last_update) if last_update else None
        return {
            "available": self.available,
            "connected": self._started and not self._error,
            "error": self._error,
            "state": latest,
            "age_s": round(age_s, 2) if age_s is not None else None,
        }


class BtMessageService:
    """Expose /bt/message as a ROS service and keep the latest UI command for the UI."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active = False
        self._mode = 0
        self._message: str = ""
        self._last_update: float = 0.0
        self._running = False
        self._started = False
        self._error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._context = None
        self._executor = None
        self._node = None
        self._service = None
        self._image_path: str = ""

    @property
    def available(self) -> bool:
        return all([
            rclpy is not None,
            Context is not None,
            SingleThreadedExecutor is not None,
            Node is not None,
            UiCommand is not None,
        ])

    def start(self):
        if not self.available or self._running:
            if not self.available:
                self._error = "rclpy or inha_interfaces.srv.UiCommand is not available"
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._spin_loop,
            name="iris-bt-message-service",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._executor is not None:
            self._executor.wake()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _spin_loop(self):
        try:
            self._context = Context()
            rclpy.init(args=None, context=self._context)
            self._node = Node("iris_bt_message_service", context=self._context)
            self._service = self._node.create_service(UiCommand, "/bt/message", self._on_request)
            self._executor = SingleThreadedExecutor(context=self._context)
            self._executor.add_node(self._node)
            self._started = True
            self._error = None

            while self._running and self._context.ok():
                self._executor.spin_once(timeout_sec=0.5)
        except Exception as exc:
            self._error = str(exc)
        finally:
            self._running = False
            self._started = False
            self._teardown_ros()

    def _teardown_ros(self):
        if self._executor is not None:
            try:
                if self._node is not None:
                    self._executor.remove_node(self._node)
                self._executor.shutdown()
            except Exception:
                pass
            self._executor = None

        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None

        if self._context is not None:
            try:
                if self._context.ok():
                    self._context.shutdown()
            except Exception:
                pass
            self._context = None

        self._service = None

    def _on_request(self, request, response):
        command = str(request.command or "start").strip().lower()
        now = time.time()

        if command not in {"start", "stop"}:
            response.success = False
            response.message = f"unsupported command: {command}"
            return response

        with self._lock:
            if command == "stop":
                self._active = False
                self._message = ""
                self._image_path = ""
            else:
                self._active = True
                self._mode = int(request.mode)
                self._message = str(request.text or "").strip()
                self._image_path = str(request.image_path or "").strip()
            self._last_update = now

        response.success = True
        response.message = "stopped" if command == "stop" else f"displaying mode={int(request.mode)}"
        return response

    def payload(self) -> dict:
        with self._lock:
            active = self._active
            mode = self._mode
            message = self._message
            image_path = self._image_path
            last_update = self._last_update

        now = time.time()
        return {
            "available": self.available,
            "connected": self._started and not self._error,
            "error": self._error,
            "active": active,
            "mode": mode,
            "message": message if active else "",
            "image_path": image_path if active else "",
            "age_s": round(now - last_update, 2) if last_update else None,
        }


class ProcessManager:
    def __init__(self, profiles: Dict[str, dict]):
        self.profiles = profiles
        self.managed: Dict[str, ManagedProcess] = {
            name: ManagedProcess(
                profile=name,
                command=cfg["command"],
                strict_stop=bool(cfg.get("strict_stop", False)),
                allow_quick_exit=bool(cfg.get("allow_quick_exit", False)),
                stop_grace_sec=float(cfg.get("stop_grace_sec", 5.0)),
                stop_term_sec=float(cfg.get("stop_term_sec", 3.0)),
            )
            for name, cfg in profiles.items()
        }

    async def start(self, profile: str) -> dict:
        if profile not in self.managed:
            raise KeyError(f"Unknown profile: {profile}")

        mp = self.managed[profile]
        if mp.running:
            return {"status": "already_running", "pid": mp.pid}

        # Fresh process group so we can SIGTERM the whole tree on stop.
        # preexec_fn=os.setsid puts children in their own process group.
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(mp.command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            preexec_fn=os.setsid,
            env={**os.environ},
        ) # 26.04.26 mhlee : 해당 proc에서 preexec_fn=os.set로 자식에게 setsid()를 호출하여 프로세스 그룹을 만들음. 그래서 같은 PGID를 공유하게 됨.
        mp.process = proc
        mp.started_at = asyncio.get_event_loop().time()
        mp.last_exit_code = None
        mp.last_exit_at = None
        mp.log_buffer.clear()

        # Fan out log lines to WS subscribers in the background
        asyncio.create_task(self._pump_logs(mp))

        # Give the process a moment to fail early so the UI can show why.
        await asyncio.sleep(0.8)

        if proc.returncode is not None:
            if mp.allow_quick_exit:
                mp.last_exit_code = proc.returncode
                mp.last_exit_at = asyncio.get_event_loop().time()
                mp.process = None
                mp.started_at = None
                return {"status": "completed", "exit_code": proc.returncode}

            tail = "\n".join(entry["line"] for entry in list(mp.log_buffer)[-15:])
            rc = proc.returncode
            mp.process = None
            mp.started_at = None
            raise RuntimeError(
                f"`{mp.command}` exited with code {rc}\n"
                f"--- last log lines ---\n{tail or '(no output)'}"
            )

        return {"status": "started", "pid": proc.pid}

    async def stop(self, profile: str) -> dict:
        if profile not in self.managed:
            raise KeyError(f"Unknown profile: {profile}")

        mp = self.managed[profile]
        if not mp.running:
            return {"status": "not_running"}

        pid = mp.pid
        try:
            # Kill the whole process group (roslaunch spawns many children)
            os.killpg(os.getpgid(pid), signal.SIGINT)
        except ProcessLookupError:
            return {"status": "already_exited"}

        # Give it 5s to shut down gracefully, then SIGTERM
        try:
            await asyncio.wait_for(mp.process.wait(), timeout=mp.stop_grace_sec)
        except asyncio.TimeoutError:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                await asyncio.wait_for(mp.process.wait(), timeout=mp.stop_term_sec)
            except (ProcessLookupError, asyncio.TimeoutError):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                try:
                    await asyncio.wait_for(mp.process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass

        mp.last_exit_code = mp.process.returncode if mp.process else None
        mp.last_exit_at = asyncio.get_event_loop().time()
        mp.process = None
        mp.started_at = None
        if mp.strict_stop and has_cleanup_failure_marker(mp.log_buffer):
            raise RuntimeError(
                f"{profile} stop verification failed (exit {mp.last_exit_code})"
            )
        return {"status": "stopped"}

    async def stop_all(self):
        for name in list(self.managed.keys()):
            try:
                await self.stop(name)
            except Exception as e:
                print(f"[stop_all] {name}: {e}")

    async def _pump_logs(self, mp: ManagedProcess):
        """Read subprocess output line by line, buffer + fan out to WS."""
        assert mp.process and mp.process.stdout
        proc = mp.process

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            entry = {"ts": asyncio.get_event_loop().time(), "line": text}
            mp.log_buffer.append(entry)

            # Fan out to active WS clients; drop any that are broken
            dead = []
            for ws in mp.subscribers:
                try:
                    await ws.send_json(entry)
                except Exception:
                    dead.append(ws)
            for d in dead:
                mp.subscribers.discard(d)

        # EOF — process is exiting/exited. Reap it and append a marker
        # so the UI can show why a "running" profile suddenly went down.
        try:
            rc = await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            rc = proc.returncode
        mp.last_exit_code = rc
        mp.last_exit_at = asyncio.get_event_loop().time()
        marker = {
            "ts": mp.last_exit_at,
            "line": f"[launcher] process {format_process_exit(rc)}",
        }
        mp.log_buffer.append(marker)
        for ws in list(mp.subscribers):
            try:
                await ws.send_json(marker)
            except Exception:
                mp.subscribers.discard(ws)

        if is_bt_profile(mp.profile):
            try:
                await stop_bag_record_if_bt_idle()
            except Exception as e:
                print(f"[auto-stop bag_record after {mp.profile} exit] {e}")
            stop_bt_bridges_if_idle()

    def status(self) -> dict:
        loop_time = asyncio.get_event_loop().time()
        return {
            name: {
                "running": mp.running,
                "pid": mp.pid,
                "uptime": (loop_time - mp.started_at) if mp.started_at else None,
                "command": mp.command,
            }
            for name, mp in self.managed.items()
        }


class TimesyncDiffMonitor:
    """Background sampler: continuously SSHes to the slave and measures
    the wall-clock difference using `date +%s.%N` on both ends. Runs
    independent of the timesync profile so the UI can always show the
    current divergence."""

    def __init__(self, remote: str, interval: float = 1.0, ssh_timeout: float = 2.0):
        self.remote = remote
        self.interval = max(interval, 0.2)
        self.ssh_timeout = max(ssh_timeout, 1.0)
        self._task: Optional[asyncio.Task] = None
        self._latest: Optional[dict] = None
        self._error: Optional[str] = None

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self):
        while True:
            try:
                await self._sample_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._error = str(exc)[:200]
                self._latest = None
            await asyncio.sleep(self.interval)

    async def _sample_once(self):
        m_before = time.time()
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-q",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={int(self.ssh_timeout)}",
            self.remote,
            "date +%s.%N",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(
                proc.communicate(), timeout=self.ssh_timeout + 1.0
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            self._error = "ssh timeout"
            self._latest = None
            return

        m_after = time.time()

        if proc.returncode != 0:
            stderr_text = err.decode(errors="replace").strip()
            self._error = (stderr_text or f"ssh exit {proc.returncode}")[:200]
            self._latest = None
            return

        try:
            slave_time = float(out.decode().strip())
        except ValueError:
            self._error = "could not parse remote date"
            self._latest = None
            return

        master_time = (m_before + m_after) / 2.0
        rtt = m_after - m_before
        self._latest = {
            "master": master_time,
            "slave": slave_time,
            "diff_s": master_time - slave_time,
            "rtt_s": rtt,
            "ts": time.time(),
        }
        self._error = None

    def payload(self) -> dict:
        if self._latest is None:
            return {
                "available": False,
                "remote": self.remote,
                "reason": self._error or "no sample yet",
            }
        return {
            "available": True,
            "remote": self.remote,
            "master": self._latest["master"],
            "slave": self._latest["slave"],
            "diff_s": self._latest["diff_s"],
            "rtt_s": self._latest["rtt_s"],
            "age_s": max(0.0, time.time() - self._latest["ts"]),
        }


# ─────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────
profiles = load_profiles()
manager = ProcessManager(profiles)
greenwave_config = load_greenwave_config()
greenwave_bridge = GreenwaveSnapshotBridge(
    topic_names=greenwave_config["topics"],
    stale_after_sec=greenwave_config["stale_after_sec"],
)
timesync_monitor = TimesyncDiffMonitor(
    remote=os.environ.get("TIMESYNC_REMOTE", "nvidia@192.168.78.10"),
    interval=float(os.environ.get("TIMESYNC_INTERVAL", "1.0")),
    ssh_timeout=float(os.environ.get("TIMESYNC_SSH_TIMEOUT", "2.0")),
)
bt_state_bridge = BtStateBridge()
bt_message_service = BtMessageService()

app = FastAPI(title="IRIS — Launch API")

# Permissive CORS — this runs on the robot, accessed from the same host
# (localhost via Chromium kiosk). Tighten if exposing to a network.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def is_bt_profile(profile: str) -> bool:
    return profile.startswith("bt_")


def has_running_bt_profile() -> bool:
    return any(
        is_bt_profile(name) and mp.running
        for name, mp in manager.managed.items()
    )


async def start_bag_record_for_bt() -> bool:
    mp = manager.managed.get(BAG_RECORD_PROFILE)
    if mp is None:
        raise RuntimeError(f"{BAG_RECORD_PROFILE} profile is missing from profiles.yaml")
    if mp.running:
        return False

    await manager.start(BAG_RECORD_PROFILE)
    return True


async def stop_bag_record_if_bt_idle():
    if has_running_bt_profile():
        return
    if BAG_RECORD_PROFILE in manager.managed:
        await manager.stop(BAG_RECORD_PROFILE)


def start_bt_bridges_if_needed():
    if has_running_bt_profile():
        bt_state_bridge.start()
        bt_message_service.start()


def stop_bt_bridges_if_idle():
    if not has_running_bt_profile():
        bt_state_bridge.stop()
        bt_message_service.stop()


@app.get("/")
async def root():
    return {"service": "iris-launcher", "profiles": list(profiles.keys())}


@app.get("/status")
async def status():
    stop_bt_bridges_if_idle()
    return manager.status()


@app.get("/profiles/{profile}/log")
async def profile_log(profile: str, tail: int = 50, after_ts: Optional[float] = None):
    mp = manager.managed.get(profile)
    if mp is None:
        raise HTTPException(status_code=404, detail=f"Unknown profile: {profile}")

    lines = list(mp.log_buffer)
    if after_ts is not None:
        lines = [entry for entry in lines if entry.get("ts") is not None and entry["ts"] > after_ts]
    if tail > 0:
        lines = lines[-tail:]

    loop_now = asyncio.get_event_loop().time()
    return {
        "profile": profile,
        "running": mp.running,
        "exit_code": mp.last_exit_code,
        "exit_age_s": (loop_now - mp.last_exit_at) if mp.last_exit_at else None,
        "lines": lines,
    }


@app.get("/timesync/diff")
async def timesync_diff():
    return timesync_monitor.payload()


@app.get("/bt/state")
async def bt_state():
    start_bt_bridges_if_needed()
    return bt_state_bridge.payload()


@app.get("/bt/message")
async def bt_message():
    start_bt_bridges_if_needed()
    return bt_message_service.payload()

from fastapi.responses import FileResponse

@app.get("/bt/message/image")
async def bt_message_image():
    payload = bt_message_service.payload()
    image_path = payload.get("image_path", "")
    if not image_path:
        raise HTTPException(status_code=404, detail="No image active")

    path = Path(image_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")

    return FileResponse(path)


@app.get("/gw/topics")
async def gw_topics():
    return greenwave_bridge.topics_payload()


@app.get("/gw/summary")
async def gw_summary():
    return greenwave_bridge.topics_payload()["summary"]


@app.get("/ros/nodes")
async def ros_nodes(mission: str = "hri"):
    try:
        return await sample_ros_nodes(mission)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/audio/defaults")
async def audio_defaults():
    return await sample_audio_defaults()


@app.post("/launch/{profile}")
async def launch(profile: str):
    if profile not in manager.managed:
        raise HTTPException(status_code=404, detail=f"Unknown profile: {profile}")

    bag_record_started = False
    try:
        if is_bt_profile(profile):
            bag_record_started = await start_bag_record_for_bt()

        result = await manager.start(profile)
        if is_bt_profile(profile):
            start_bt_bridges_if_needed()
        return result
    except Exception as e:
        if bag_record_started:
            try:
                await manager.stop(BAG_RECORD_PROFILE)
            except Exception as stop_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"{e}\n\nbag_record rollback failed: {stop_error}",
                )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop/{profile}")
async def stop(profile: str):
    if profile not in manager.managed:
        raise HTTPException(status_code=404, detail=f"Unknown profile: {profile}")

    try:
        result = await manager.stop(profile)
        if is_bt_profile(profile):
            try:
                await stop_bag_record_if_bt_idle()
            finally:
                stop_bt_bridges_if_idle()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pose/{name}")
async def goto_pose(name: str):
    if name not in POSE_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown pose: {name}")

    proc = await asyncio.create_subprocess_exec(
        "/bin/bash", str(POSE_SCRIPT), name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    try:
        stdout_b, _ = await asyncio.wait_for(proc.communicate(), timeout=POSE_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise HTTPException(status_code=504, detail=f"Pose '{name}' timed out after {POSE_TIMEOUT_SEC:.0f}s")

    output = (stdout_b or b"").decode("utf-8", errors="replace")
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Pose '{name}' failed (exit {proc.returncode}):\n{output[-1500:]}",
        )

    return {"pose": name, "output": output[-1500:]}


@app.post("/profiles/{profile}/save")
async def save_profile_log(profile: str):
    if profile not in manager.managed:
        raise HTTPException(status_code=404, detail=f"Unknown profile: {profile}")

    mp = manager.managed[profile]
    entries = list(mp.log_buffer)
    if not entries:
        raise HTTPException(status_code=409, detail="Log buffer is empty")

    now = datetime.datetime.now()
    save_dir = LOG_SAVE_ROOT / now.strftime("%Y-%m-%d") / profile
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{profile}_{now.strftime('%H-%M-%S')}.log"

    with open(save_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry["line"] + "\n")

    return {"path": str(save_path), "lines": len(entries)}


def _terminate_process_group():
    try:
        os.killpg(os.getpgid(os.getpid()), signal.SIGTERM)
    except ProcessLookupError:
        try:
            os.kill(os.getpid(), signal.SIGTERM)
        except ProcessLookupError:
            pass


@app.post("/app/exit")
async def exit_app():
    loop = asyncio.get_running_loop()
    loop.call_later(0.2, _terminate_process_group)
    return {"status": "exiting"}


@app.websocket("/ws/logs/{profile}")
async def ws_logs(websocket: WebSocket, profile: str):
    if profile not in manager.managed:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    mp = manager.managed[profile]
    mp.subscribers.add(websocket)
    replay = websocket.query_params.get("replay", "1").lower() not in {"0", "false", "no"}

    # Flush buffered lines so late subscribers see recent history
    try:
        if replay:
            for entry in list(mp.log_buffer):
                await websocket.send_json(entry)

        while True:
            # Keep the connection alive; we don't expect incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        mp.subscribers.discard(websocket)


@app.on_event("shutdown")
async def on_shutdown():
    greenwave_bridge.stop()
    bt_state_bridge.stop()
    bt_message_service.stop()
    await timesync_monitor.stop()
    await manager.stop_all()


@app.on_event("startup")
async def on_startup():
    timesync_monitor.start()
