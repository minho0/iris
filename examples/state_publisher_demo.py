#!/usr/bin/env python3
"""
Example: publish robot state to /robot_state so the IRIS picks it up.

The UI expects a std_msgs/String whose `data` field is a JSON blob with:
    {
      "task":   "Receptionist",          # short task name shown large
      "phase":  "Scanning for guest",    # one-line current sub-step
      "step":   3,                       # progress numerator
      "total":  7,                       # progress denominator
      "elapsed": 42,                     # seconds since task start
      "status": "running"                # running | idle | error | done
    }

Just publish this from your state machine / behavior tree node and the UI
takes care of the rest. If you prefer a typed message, swap std_msgs/String
for a custom .msg and adjust src/lib/TaskPanel.svelte accordingly.
"""
import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class StatePublisherDemo(Node):
    def __init__(self):
        super().__init__("state_publisher_demo")
        self.pub = self.create_publisher(String, "/robot_state", 10)
        self.start = time.time()
        self.timer = self.create_timer(0.5, self.tick)

        # Demo script — replace with hooks into your actual state machine
        self.script = [
            ("Receptionist", "Navigating to living room",   1, 7, "running"),
            ("Receptionist", "Scanning for waving person",  2, 7, "running"),
            ("Receptionist", "Approaching guest",           3, 7, "running"),
            ("Receptionist", "Asking guest their name",     4, 7, "running"),
            ("Receptionist", "Returning to host",           5, 7, "running"),
            ("Receptionist", "Introducing new guest",       6, 7, "running"),
            ("Receptionist", "Task complete",               7, 7, "done"),
        ]

    def tick(self):
        idx = int((time.time() - self.start) / 3) % len(self.script)
        task, phase, step, total, status = self.script[idx]
        payload = {
            "task": task,
            "phase": phase,
            "step": step,
            "total": total,
            "elapsed": int(time.time() - self.start),
            "status": status,
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = StatePublisherDemo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
