#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosidl_runtime_py.utilities import get_message


DEFAULT_TOPICS = [
    "/scan0",
    "/scan1",
    "/scan_merged",
    "/camera/camera_head/color/image_raw",
    "/camera/camera_head/color/image_raw/compressed",
    "/camera/camera_head/depth/image_rect_raw",
    "/livox/lidar",
]

DEFAULT_TYPES = {
    "/scan0": "sensor_msgs/msg/LaserScan",
    "/scan1": "sensor_msgs/msg/LaserScan",
    "/scan_merged": "sensor_msgs/msg/LaserScan",
    "/camera/camera_head/color/image_raw": "sensor_msgs/msg/Image",
    "/camera/camera_head/color/image_raw/compressed": "sensor_msgs/msg/CompressedImage",
    "/camera/camera_head/depth/image_rect_raw": "sensor_msgs/msg/Image",
    "/livox/lidar": "sensor_msgs/msg/PointCloud2",
}


@dataclass
class TopicStats:
    name: str
    msg_type: str | None = None
    count: int = 0
    last_count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    last_delay_ms: float | None = None
    max_delay_ms: float | None = None
    intervals: list[float] = field(default_factory=list)
    last_arrival: float = 0.0
    error: str = ""


class TopicReceiveCheck(Node):
    def __init__(self, topics: list[str], report_sec: float, stale_sec: float, json_lines: bool):
        super().__init__("iris_topic_receive_check")
        self.topics = topics
        self.report_sec = report_sec
        self.stale_sec = stale_sec
        self.json_lines = json_lines
        self.stats = {name: TopicStats(name=name) for name in topics}
        self.subscriptions_by_topic: dict[str, Any] = {}
        self.last_report = time.monotonic()
        self.qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self.create_timer(0.5, self.ensure_subscriptions)
        self.create_timer(0.2, self.report_if_due)

    def discover_types(self) -> dict[str, str]:
        discovered = {}
        for name, type_names in self.get_topic_names_and_types():
            if name in self.stats and type_names:
                discovered[name] = type_names[0]
        return discovered

    def ensure_subscriptions(self):
        discovered = self.discover_types()
        for name in self.topics:
            if name in self.subscriptions_by_topic:
                continue

            type_name = discovered.get(name) or DEFAULT_TYPES.get(name)
            if not type_name:
                self.stats[name].error = "type unknown"
                continue

            try:
                msg_cls = get_message(type_name)
            except (AttributeError, ModuleNotFoundError, ValueError) as exc:
                self.stats[name].msg_type = type_name
                self.stats[name].error = f"type load failed: {exc}"
                continue

            self.stats[name].msg_type = type_name
            self.stats[name].error = ""
            self.subscriptions_by_topic[name] = self.create_subscription(
                msg_cls,
                name,
                lambda msg, topic_name=name: self.on_message(topic_name, msg),
                self.qos,
            )
            self.emit({"event": "subscribe", "topic": name, "type": type_name}, f"[SUB] {name} ({type_name})")

    def on_message(self, topic_name: str, msg):
        now = time.monotonic()
        stat = self.stats[topic_name]
        stat.count += 1
        if stat.first_seen == 0.0:
            stat.first_seen = now
        if stat.last_arrival:
            stat.intervals.append(now - stat.last_arrival)
            stat.intervals = stat.intervals[-100:]
        stat.last_arrival = now
        stat.last_seen = now
        stat.error = ""

        delay_ms = self.message_delay_ms(msg)
        if delay_ms is not None:
            stat.last_delay_ms = delay_ms
            stat.max_delay_ms = delay_ms if stat.max_delay_ms is None else max(stat.max_delay_ms, delay_ms)

    def message_delay_ms(self, msg) -> float | None:
        header = getattr(msg, "header", None)
        stamp = getattr(header, "stamp", None)
        if stamp is None:
            return None

        stamp_ns = int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
        if stamp_ns <= 0:
            return None

        now_ns = self.get_clock().now().nanoseconds
        return (now_ns - stamp_ns) / 1_000_000.0

    def report_if_due(self):
        now = time.monotonic()
        if now - self.last_report < self.report_sec:
            return

        elapsed = now - self.last_report
        self.last_report = now
        if not self.json_lines:
            print("\n--- topic receive check ---", flush=True)

        for name in self.topics:
            stat = self.stats[name]
            delta = stat.count - stat.last_count
            stat.last_count = stat.count
            hz = delta / elapsed if elapsed > 0 else 0.0
            age = now - stat.last_seen if stat.last_seen else None
            status = self.status_for(stat, age)
            delay = "-" if stat.last_delay_ms is None else f"{stat.last_delay_ms:.1f} ms"
            max_delay = "-" if stat.max_delay_ms is None else f"{stat.max_delay_ms:.1f} ms"
            age_label = "-" if age is None else f"{age:.1f}s"
            msg_type = stat.msg_type or "waiting type"
            suffix = f" | {stat.error}" if stat.error else ""

            self.emit(
                {
                    "event": "topic",
                    "topic": name,
                    "status": status,
                    "hz": round(hz, 2),
                    "age_s": None if age is None else round(age, 2),
                    "delay_ms": None if stat.last_delay_ms is None else round(stat.last_delay_ms, 2),
                    "max_delay_ms": None if stat.max_delay_ms is None else round(stat.max_delay_ms, 2),
                    "type": msg_type,
                    "error": stat.error,
                    "count": stat.count,
                },
                f"[{status:7}] {name} | {hz:6.1f} Hz | last {age_label:>5} "
                f"| delay {delay:>9} | max {max_delay:>9} | {msg_type}{suffix}",
            )

    def status_for(self, stat: TopicStats, age: float | None) -> str:
        if stat.error:
            return "ERROR"
        if stat.count == 0:
            return "WAIT"
        if age is not None and age > self.stale_sec:
            return "STALE"
        return "OK"

    def emit(self, payload: dict, text: str):
        if self.json_lines:
            print(json.dumps(payload, separators=(",", ":")), flush=True)
        else:
            print(text, flush=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Subscribe to key ROS 2 topics and report receive rate/delay.")
    parser.add_argument("--topic", action="append", dest="topics", help="Topic to monitor. Can be repeated.")
    parser.add_argument("--report-sec", type=float, default=1.0, help="Report interval in seconds.")
    parser.add_argument("--stale-sec", type=float, default=2.0, help="Seconds without messages before STALE.")
    parser.add_argument("--json-lines", action="store_true", help="Emit machine-readable JSON lines for the UI.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    topics = args.topics or DEFAULT_TOPICS
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    rclpy.init()
    node = TopicReceiveCheck(
        topics=topics,
        report_sec=max(args.report_sec, 0.2),
        stale_sec=max(args.stale_sec, 0.5),
        json_lines=args.json_lines,
    )
    print("[START] iris_topic_receive_check", flush=True)
    print("[INFO] Ctrl+C or iris stop will destroy the node.", flush=True)

    try:
        while running and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        print("[STOP] iris_topic_receive_check", flush=True)
        node.destroy_node()
        rclpy.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
