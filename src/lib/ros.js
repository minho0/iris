import { writable, readable } from 'svelte/store';
import ROSLIB from 'roslib';

// ────────────────────────────────────────────────────────
// Config
// ────────────────────────────────────────────────────────
// Use whatever host the browser used to load the page. Lets the same UI
// work both from the robot's own kiosk (localhost) and from other devices
// on the WiFi (192.168.x.x), without hardcoding an IP.
const browserHost =
  typeof window !== 'undefined' && window.location?.hostname
    ? window.location.hostname
    : 'localhost';

const env = import.meta.env ?? {};

export const config = {
  rosbridgeUrl: `ws://${browserHost}:9090`,
  videoServerUrl: `http://${browserHost}:18081`,
  apiUrl: `http://${browserHost}:8000`,
  ServiceName:
    env.VITE_START_NEXT_INSTRUCTION_SERVICE ?? '/bt/start_next_instruction',
  startNextInstructionServiceType:
    env.VITE_START_NEXT_INSTRUCTION_SERVICE_TYPE ?? 'inha_interfaces/srv/SetEnable'
};

// ────────────────────────────────────────────────────────
// Connection state
// ────────────────────────────────────────────────────────
export const connectionState = writable('connecting'); // connecting | connected | disconnected

export const ros = new ROSLIB.Ros({ url: config.rosbridgeUrl });

ros.on('connection', () => connectionState.set('connected'));
ros.on('close', () => {
  connectionState.set('disconnected');
  // Auto-reconnect
  setTimeout(() => {
    connectionState.set('connecting');
    ros.connect(config.rosbridgeUrl);
  }, 2000);
});
ros.on('error', () => connectionState.set('disconnected'));

// ────────────────────────────────────────────────────────
// Topic helpers
// ────────────────────────────────────────────────────────

/**
 * Subscribe to a ROS topic as a Svelte readable store.
 * Automatically tracks message rate (Hz).
 */
export function topic(name, messageType, initialValue = null) {
  const value = writable(initialValue);
  const hz = writable(0);

  let timestamps = [];

  const sub = new ROSLIB.Topic({
    ros,
    name,
    messageType,
    throttle_rate: 100 // ms — limit bandwidth
  });

  sub.subscribe((msg) => {
    value.set(msg);

    const now = performance.now();
    timestamps.push(now);
    // Keep last 1 second of timestamps
    timestamps = timestamps.filter((t) => now - t < 1000);
    hz.set(timestamps.length);
  });

  // Decay Hz if no messages
  setInterval(() => {
    const now = performance.now();
    timestamps = timestamps.filter((t) => now - t < 1000);
    hz.set(timestamps.length);
  }, 500);

  return { value, hz, topic: sub };
}

/**
 * Call a ROS 2 service.
 */
export function callService(name, serviceType, request) {
  return new Promise((resolve, reject) => {
    const service = new ROSLIB.Service({ ros, name, serviceType });
    const req = new ROSLIB.ServiceRequest(request);
    service.callService(req, resolve, reject);
  });
}

export async function startNextInstruction() {
  const res = await fetch(`${config.apiUrl}/bt/start-next-instruction`, { method: 'POST' });

  if (!res.ok) {
    throw new Error(await extractDetail(res, `Start next instruction failed: ${res.status}`));
  }

  const response = await res.json();
  if (response?.success === false) {
    throw new Error(response.message || 'Start next instruction rejected');
  }

  return response;
}

/**
 * Build a web_video_server MJPEG stream URL for a given image topic.
 */
export function videoStreamUrl(topicName, quality = 70, type = 'mjpeg') {
  const params = new URLSearchParams({ topic: topicName, type, quality: String(quality) });
  return `${config.videoServerUrl}/stream?${params}`;
}

/**
 * Trigger a launch file via the companion FastAPI server.
 */
async function extractDetail(res, fallback) {
  try {
    const body = await res.json();
    if (body?.detail) return body.detail;
  } catch {}
  return fallback;
}

export async function launchProfile(profile) {
  const res = await fetch(`${config.apiUrl}/launch/${profile}`, { method: 'POST' });
  if (!res.ok) throw new Error(await extractDetail(res, `Launch ${profile} failed: ${res.status}`));
  return res.json();
}

export async function stopProfile(profile) {
  const res = await fetch(`${config.apiUrl}/stop/${profile}`, { method: 'POST' });
  if (!res.ok) throw new Error(await extractDetail(res, `Stop ${profile} failed: ${res.status}`));
  return res.json();
}

export async function fetchLaunchStatus() {
  const res = await fetch(`${config.apiUrl}/status`);
  if (!res.ok) throw new Error(`Launcher status failed: ${res.status}`);
  return res.json();
}

export async function fetchProfileLog(profile, tail = 30) {
  const res = await fetch(`${config.apiUrl}/profiles/${profile}/log?tail=${tail}`);
  if (!res.ok) throw new Error(`Profile log failed: ${res.status}`);
  return res.json();
}

export async function fetchProfileLogSince(profile, afterTs) {
  const params = new URLSearchParams();
  if (afterTs != null) {
    params.set('after_ts', String(afterTs));
  }
  const res = await fetch(`${config.apiUrl}/profiles/${profile}/log?${params.toString()}`);
  if (!res.ok) throw new Error(`Profile log failed: ${res.status}`);
  return res.json();
}

export async function saveProfileLog(profile) {
  const res = await fetch(`${config.apiUrl}/profiles/${profile}/save`, { method: 'POST' });
  if (!res.ok) throw new Error(await extractDetail(res, `Save ${profile} log failed: ${res.status}`));
  return res.json();
}

export async function gotoPose(name) {
  const res = await fetch(`${config.apiUrl}/pose/${name}`, { method: 'POST' });
  if (!res.ok) throw new Error(await extractDetail(res, `Pose ${name} failed: ${res.status}`));
  return res.json();
}

export function profileLogSocketUrl(profile, options = {}) {
  const url = new URL(config.apiUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = `/ws/logs/${profile}`;
  url.search = '';
  url.hash = '';
  if (options.replay === false) {
    url.searchParams.set('replay', '0');
  }
  return url.toString();
}

export async function fetchTimesyncDiff() {
  const res = await fetch(`${config.apiUrl}/timesync/diff`);
  if (!res.ok) throw new Error(`Timesync diff failed: ${res.status}`);
  return res.json();
}

export async function fetchGreenwaveTopics() {
  const res = await fetch(`${config.apiUrl}/gw/topics`);
  if (!res.ok) throw new Error(`Greenwave topics failed: ${res.status}`);
  return res.json();
}

export async function fetchRosNodes(mission = 'hri') {
  const params = new URLSearchParams({ mission });
  const res = await fetch(`${config.apiUrl}/ros/nodes?${params.toString()}`);
  if (!res.ok) throw new Error(`ROS node check failed: ${res.status}`);
  return res.json();
}

export async function fetchAudioDefaults() {
  const res = await fetch(`${config.apiUrl}/audio/defaults`);
  if (!res.ok) throw new Error(`Audio defaults check failed: ${res.status}`);
  return res.json();
}

export async function fetchBtState() {
  const res = await fetch(`${config.apiUrl}/bt/state`);
  if (!res.ok) throw new Error(`BT state failed: ${res.status}`);
  return res.json();
}

export async function fetchBtMessage() {
  const res = await fetch(`${config.apiUrl}/bt/message`);
  if (!res.ok) throw new Error(`BT message failed: ${res.status}`);
  return res.json();
}

export async function stopEveryNode() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 70000);

  try {
    const res = await fetch(`${config.apiUrl}/stop-every-node`, {
      method: 'POST',
      signal: controller.signal
    });

    if (!res.ok) throw new Error(await extractDetail(res, `Stop every node failed: ${res.status}`));

    const payload = await res.json();
    if (payload?.errors && Object.keys(payload.errors).length > 0) {
      throw new Error(`Stop every node partially failed: ${Object.keys(payload.errors).join(', ')}`);
    }
    return payload;
  } finally {
    clearTimeout(timeout);
  }
}

// ────────────────────────────────────────────────────────
// Wall clock (for header)
// ────────────────────────────────────────────────────────
export const clock = readable(new Date(), (set) => {
  const i = setInterval(() => set(new Date()), 1000);
  return () => clearInterval(i);
});
