# IRIS

A minimal, dark-themed web UI for a RoboCup@Home robot. Designed for a
1920×1280 touchscreen running on Jetson Thor with ROS 2 Jazzy.

## Features

- **Status display** — current task, phase, progress, recent actions
- **One-tap node launching** — competition and debug profiles
- **Live topic visualization** — waving person + detection debug streams
- **Topic health monitoring** — heartbeat dots for core ROS topics
- **Emergency stop** — large, always-visible hardware-style button

## Architecture

```
┌─────────────── Jetson Thor ─────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────────┐                                   │
│  │  Chromium window         │  ← robot touchscreen              │
│  │  localhost:4173          │                                   │
│  └──┬───────────┬───────────┘                                   │
│     │           │                                               │
│     │  ws:9090  │  http:8080                                    │
│     ▼           ▼                                               │
│  rosbridge   web_video_server      FastAPI :8000                │
│     │           │                     │                         │
│     └───────────┴─────────────────────┴─── subprocess ────┐     │
│                      │                                     │    │
│                      ▼                                     ▼    │
│              ROS 2 Jazzy DDS                       roslaunch    │
│              topics / services                    (competition, │
│                                                    debug)       │
└─────────────────────────────────────────────────────────────────┘
```

- **Frontend** — SvelteKit, static build, ~kB-scale runtime
- **ROS bridge** — `rosbridge_suite` for topics/services over WebSocket
- **Video** — `web_video_server` for MJPEG streams of image topics
- **Launch API** — small FastAPI service that manages `roslaunch` subprocesses

## Prerequisites

```bash
# ROS 2 packages
sudo apt install \
    ros-jazzy-rosbridge-suite \
    ros-jazzy-web-video-server \
    chromium-browser

# Node + Python
# (Node 20+, Python 3.10+)
```

## Install

```bash
git clone <this repo> iris
cd iris

# frontend
npm install

# backend
cd backend
pip install -r requirements.txt
cd ..
```

## Run — development (hot reload)

```bash
./run-dev.sh
```

Opens on <http://localhost:1352>. Edit any `.svelte` file and it hot reloads.
All component logs go to `./logs/`.

## Run — production

```bash
npm run build
./run.sh
```

Launches Chromium as a window on `$DISPLAY`.

### Auto-start at boot

```bash
sudo cp systemd/iris.service /etc/systemd/system/
# edit User/Group/WorkingDirectory paths first
sudo systemctl enable --now iris
journalctl -u iris -f    # watch logs
```

## Configuration

### Launch profiles

Edit `backend/profiles.yaml`:

```yaml
profiles:
  competition:
    command: "ros2 launch robot_bringup competition.launch.py"
  debug:
    command: "ros2 launch robot_bringup debug.launch.py rviz:=true"
```

### Topic names

Edit `src/lib/ros.js` (`config` object) for rosbridge/video/API endpoints.

Per-panel topic names live in the respective components:
- `src/routes/+page.svelte` — video stream topic names
- `src/lib/TopicMonitor.svelte` — list of monitored topics
- `src/lib/TaskPanel.svelte` — subscribes to `/robot_state`

### Publishing robot state

Your state machine / behavior tree needs to publish to `/robot_state` as
`std_msgs/String` containing a JSON object. See
`examples/state_publisher_demo.py` for the exact schema and a runnable demo:

```bash
python3 examples/state_publisher_demo.py
```

## Troubleshooting

**UI loads but shows "Connecting"**
rosbridge isn't running. Check `logs/rosbridge.log`.

**Video streams show a broken image icon**
`web_video_server` isn't running, or the image topic doesn't exist.
Verify with `ros2 topic list | grep image`.

**Launch buttons do nothing**
Backend API isn't reachable. Check `logs/backend.log` and `curl http://localhost:8000/status`.

**Chromium shows a crash restore bar**
Delete `.chrome-profile/` — it caches the session state.

**Touchscreen accidentally triggers swipe navigation**
Already handled in `run.sh` via `--overscroll-history-navigation=0` and
`--disable-features=TouchpadOverscrollHistoryNavigation`. If you see it
anyway, double-check the Chromium version picked up the flags.

## File map

```
iris/
├── src/                          # Svelte frontend
│   ├── app.css                   # Design tokens
│   ├── app.html
│   ├── lib/
│   │   ├── ros.js                # rosbridge connection + helpers
│   │   ├── Header.svelte         # Top bar: status + system metrics
│   │   ├── TaskPanel.svelte      # Big current-task display
│   │   ├── LaunchPanel.svelte    # Profile buttons + E-stop
│   │   ├── VideoStream.svelte    # MJPEG video frame
│   │   ├── TopicMonitor.svelte   # Heartbeat list
│   │   └── TopicRow.svelte
│   └── routes/
│       ├── +layout.js            # SSR off
│       └── +page.svelte          # 3-column main layout
├── backend/
│   ├── main.py                   # FastAPI launch/stop/status/logs
│   ├── profiles.yaml             # Edit me to match your launch files
│   └── requirements.txt
├── examples/
│   └── state_publisher_demo.py   # /robot_state message schema
├── systemd/
│   └── iris.service    # Boot-time autostart
├── run.sh                        # Production launcher
├── run-dev.sh                    # Development (hot reload)
├── package.json
├── svelte.config.js
└── vite.config.js
```
