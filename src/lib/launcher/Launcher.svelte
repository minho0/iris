<script>
  import { onMount, tick } from 'svelte';
  import BackBar from '$lib/common/BackBar.svelte';
  import {
    fetchAudioDefaults,
    fetchLaunchStatus,
    fetchProfileLog,
    fetchProfileLogSince,
    fetchRosNodes,
    fetchTimesyncDiff,
    gotoPose,
    launchProfile,
    profileLogSocketUrl,
    saveProfileLog,
    stopProfile
  } from '$lib/ros.js';
  import { localFixedUi } from '$lib/uiMode.js';
  import NodeButton from './NodeButton.svelte';

  const MAX_LINES_PER_TAG = 200;
  const TAG_REGEX = /^\[([^\]]+)\]\s*/;
  const UNTAGGED_KEY = '__untagged__';
  const UNTAGGED_LABEL = 'log';
  const missionTabs = [
    { id: 'hri', label: 'HRI' },
    { id: 'pp', label: 'Pick and Place' },
    { id: 'restaurant', label: 'Restaurant' },
    { id: 'gpsr', label: 'GPSR' },
    { id: 'laundry', label: 'Laundry' },
    { id: 'final', label: 'Final' },
    { id: 'option', label: 'Option' },
    { id: 'test', label: 'Test' }
  ];
  const standardMissionIds = missionTabs
    .filter((tab) => !['option', 'test'].includes(tab.id))
    .map((tab) => tab.id);
  const nonHriMissionIds = standardMissionIds.filter((id) => id !== 'hri');
  const nonRestaurantMissionIds = standardMissionIds.filter((id) => id !== 'restaurant');
  const nav2StandardMissionIds = standardMissionIds.filter((id) => !['hri', 'restaurant'].includes(id));
  const TOPIC_CHECK_PROFILE = 'topic_receive_check';
  const AUDIO_DEFAULTS_PROFILE = 'audio_defaults';
  const TOPIC_TARGETS = [
    '/scan0',
    '/scan1',
    '/scan_merged',
    '/camera/camera_head/color/image_raw',
    '/camera/camera_head/color/image_raw/compressed',
    '/camera/camera_head/depth/image_rect_raw',
    '/livox/lidar'
  ];
  const EXIT_SIGNAL_LABELS = {
    2: 'sigint',
    9: 'sigkill',
    15: 'sigterm'
  };

  let nodes = [
    {
      id: 'timesync',
      name: 'TimeSync',
      desc: 'PTP master/slave',
      group: 'mission',
      missions: [],
      status: 'down'
    },
    {
      id: 'sound',
      name: 'Sound',
      desc: 'Mic · speaker · whisper · TTS',
      group: 'mission',
      missions: standardMissionIds,
      status: 'down'
    },
    {
      id: 'face',
      name: 'Face',
      desc: 'Face landmark pipeline',
      group: 'mission',
      missions: ['hri', 'restaurant', 'gpsr'],
      status: 'down'
    },
    {
      id: 'human_following',
      name: 'Human Following',
      desc: 'Human following stack',
      group: 'mission',
      missions: ['hri', 'gpsr'],
      status: 'down'
    },
    {
      id: 'nav2',
      name: 'Nav2',
      desc: 'Nav2 navigation stack',
      group: 'mission',
      missions: nav2StandardMissionIds,
      status: 'down'
    },
    {
      id: 'nav2_hri',
      name: 'Nav2 HRI',
      desc: 'Nav2 navigation stack for HRI',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    },
    {
      id: 'bringup_common',
      name: 'Bringup',
      desc: 'Common robot bringup stack',
      group: 'default',
      status: 'down'
    },
    {
      id: 'head',
      name: 'Head Control',
      desc: 'Head control stack',
      group: 'default',
      status: 'down'
    },
    {
      id: 'vlm',
      name: 'VLM',
      desc: 'Vision-language model stack',
      group: 'default',
      status: 'down'
    },
    {
      id: 'subtask_generator',
      name: 'Subtask Generator',
      desc: 'RDMM GPSR parser',
      group: 'mission',
      missions: ['gpsr'],
      status: 'down'
    },
    {
      id: 'triple_camera',
      name: 'Triple Camera',
      desc: 'RGB-D camera pipeline',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    },
    {
      id: 'triple_camera_points',
      name: 'Camera + Points',
      desc: 'Triple camera with point stream',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'manipulation',
      name: 'Manipulation',
      desc: 'Manipulation control stack',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'safe_joint_move',
      name: 'Safe Joint Move',
      desc: 'Safe joint movement script',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    },
    {
      id: 'align_to_person',
      name: 'Align to Person',
      desc: 'Navigation alignment to person',
      group: 'mission',
      missions: ['hri', 'restaurant'],
      status: 'down'
    },
    {
      id: 'close_approach',
      name: 'Close Approach',
      desc: 'Navigation close approach behavior',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'mani_detection',
      name: 'Mani Detection',
      desc: 'Manipulation object detection',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'gdino_trt',
      name: 'GDINO',
      desc: 'Grounding DINO TRT detection',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    },
    {
      id: 'gesture_detector',
      name: 'Gesture Detector',
      desc: 'Gesture perception pipeline',
      group: 'mission',
      missions: ['hri','restaurant','gpsr'],
      status: 'down'
    },
    {
      id: 'posture_detector',
      name: 'Posture Detector',
      desc: 'Posture perception pipeline',
      group: 'mission',
      missions: [],
      status: 'down'
    },
    {
      id: 'camera_only_head',
      name: 'Camera Only Head',
      desc: 'Head camera only pipeline',
      group: 'mission',
      missions: ['option'],
      status: 'down'
    },
    {
      id: 'world_odom_tf',
      name: 'World Odom TF',
      desc: 'World ↔ odom TF publisher',
      group: 'mission',
      missions: ['option'],
      status: 'down'
    },
    {
      id: 'bell_detector',
      name: 'Bell Detector',
      desc: 'Bell detector HRI pipeline',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    },
    {
      id: 'table_person_associate',
      name: 'Table-Person Associate',
      desc: 'Table ↔ person association pipeline',
      group: 'mission',
      missions: ['restaurant'],
      status: 'down'
    },
    {
      id: 'find_start_bar',
      name: 'Find Start Bar',
      desc: 'Find Start Bar from initial pose',
      group: 'mission',
      missions: ['restaurant'],
      status: 'down'
    },
    {
      id: 'nav2_restaurant',
      name: 'Nav2 Restaurant',
      desc: 'Nav2 restaurant navigation stack',
      group: 'mission',
      missions: ['restaurant'],
      status: 'down'
    },
    
    {
      id: 'approach_mapping',
      name: 'Approach Mapping',
      desc: 'Approach mapping pipeline',
      group: 'mission',
      missions: ['pp', 'restaurant'],
      status: 'down'
    },
    {
      id: 'approach_icp',
      name: 'Approach ICP',
      desc: 'Approach ICP perception pipeline',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'local_search',
      name: 'Local Search',
      desc: 'Local search perception pipeline',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'world_map_tf',
      name: 'World Map TF',
      desc: 'World ↔ map TF publisher',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },
    {
      id: 'speak_test',
      name: 'Speak Test',
      desc: 'Test speech output script',
      group: 'mission',
      missions: ['test'],
      status: 'down'
    },
    {
      id: AUDIO_DEFAULTS_PROFILE,
      name: 'Audio Defaults',
      desc: 'Set default mic and speaker',
      group: 'side',
      status: 'down'
    },
    {
      id: 'detection_inha',
      name: 'Detection_INHA',
      desc: 'Yolo26E + SAM2 stack',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    },
    {
      id: 'align_to_map',
      name: 'Align To Map',
      desc: 'Align to Original Nav2 Goal',
      group: 'mission',
      missions: standardMissionIds,
      status: 'down'
    },
    {
      id: 'find_empty_seat',
      name: 'Find Empty Seat',
      desc: 'Find Empty Seat for Greeting Guest at HRI',
      group: 'mission',
      missions: ['hri'],
      status: 'down'
    }, 
    {
      id: 'place',
      name: 'Place',
      desc: 'Place Object',
      group: 'mission',
      missions: nonHriMissionIds,
      status: 'down'
    },

  ];
  const managedProfiles = nodes.map((node) => node.id);

  let launcherError = '';
  let backendOffline = false;
  let busyProfiles = {};
  let pendingStop = {};
  let prevProfileStatus = {};
  let timesyncRaw = null;      // raw payload for the monitor card
  let audioDefaults = null;
  let rosNodes = [];
  let rosNodesError = '';
  let rosNodeMeta = 'checking…';
  let rosNodeMissionLabel = 'HRI';
  let topicCheckRunning = false;
  let topicPanelOpen = false;
  let topicCheckBusy = '';
  let topicCheckError = '';
  let topicCheckLastLogTs = null;
  let topicRows = TOPIC_TARGETS.map((name) => ({
    topic: name,
    status: 'WAIT',
    hz: 0,
    age_s: null,
    delay_ms: null,
    max_delay_ms: null,
    type: '',
    error: '',
    count: 0
  }));
  let openLogProfile = null;
  let openLogName = '';
  let logsByTag = {};      // { tag: entry[] }
  let tagOrder = [];       // discovered insertion order of tags
  let logViewports = {};   // bound DOM viewports per tag
  let logRunning = false;
  let logLoading = false;
  let logConnected = false;
  let logExitCode = null;
  let logError = '';
  let logSocket = null;
  let logReconnectTimer = null;
  let logPollTimer = null;
  let logPollActive = false;
  let logStreamSupported = true;
  let lastLogTs = null;
  let saveStatus = '';
  let saveBusy = false;
  const POSE_BUTTONS = ['zero', 'ready', 'packing'];
  let poseBusy = '';
  let activeMissionTab = 'hri';
  let bulkStartBusy = false;
  let bulkStopBusy = false;

  const MISSION_BULK_CONFIG = {
    hri: {
      earlyStage: ['triple_camera', 'sound'],
      lateStage: ['bell_detector']
    },
    pp: {
      earlyStage: ['triple_camera_points', 'sound'],
      lateStage: []
    },
    restaurant: {
      earlyStage: ['triple_camera_points', 'sound'],
      lateStage: [],
      exclude: ['nav2_restaurant']
    },
    gpsr: {
      earlyStage: ['triple_camera_points', 'sound'],
      lateStage: []
    }
  };

  $: launcherNote = launcherError || (backendOffline ? 'Launcher backend unavailable' : '');
  $: logExitLabel = logExitCode == null
    ? ''
    : logExitCode < 0
      ? (EXIT_SIGNAL_LABELS[-logExitCode] ?? `signal ${-logExitCode}`)
      : `exit ${logExitCode}`;
  $: logMeta = logLoading
    ? 'loading…'
    : logRunning
      ? (logConnected ? 'running · live stream' : 'running')
      : logExitCode == null
        ? (logConnected ? 'idle · stream attached' : 'idle')
        : `stopped · ${logExitLabel}`;
  $: logPaneCount = Math.max(tagOrder.length, 1);
  $: logGridColumns = logPaneCount <= 1 ? 1 : logPaneCount <= 4 ? 2 : 3;
  $: logPaneMinHeight = logPaneCount <= 2 ? 220 : logPaneCount <= 4 ? 180 : 140;
  $: defaultNodes = nodes.filter((node) => node.group === 'default');
  $: missionNodes = nodes.filter((node) => node.group === 'mission' && (node.missions ?? []).includes(activeMissionTab));
  $: activeMissionLabel = missionTabs.find((tab) => tab.id === activeMissionTab)?.label ?? activeMissionTab;
  $: bulkConfig = MISSION_BULK_CONFIG[activeMissionTab] ?? null;
  $: topicOkCount = topicRows.filter((row) => row.status === 'OK').length;
  $: topicSummary = topicCheckRunning ? `${topicOkCount} / ${topicRows.length}` : 'stopped';
  $: topicDot = topicCheckRunning ? (topicOkCount === topicRows.length ? 'ok' : 'warn') : 'idle';
  $: timesyncNode = nodeById('timesync');
  $: timesyncStatus = timesyncNode?.status ?? 'down';
  $: timesyncActionIsStop = timesyncStatus === 'up';
  $: timesyncActionLabel = timesyncStatus === 'up' ? 'Stop' : timesyncStatus === 'starting' ? '…' : 'Start';
  $: audioDefaultsNode = nodeById(AUDIO_DEFAULTS_PROFILE);
  $: audioDefaultsStatus = audioDefaultsNode?.status ?? 'down';
  $: audioDefaultsBusy = Boolean(busyProfiles[AUDIO_DEFAULTS_PROFILE]);
  $: audioDefaultsActionLabel = audioDefaultsBusy
    ? '...'
    : audioDefaultsStatus === 'up'
      ? 'Stop'
      : 'Start';

  function updateNode(id, patch) {
    nodes = nodes.map((node) => (node.id === id ? { ...node, ...patch } : node));
  }

  function nodeById(id) {
    return nodes.find((node) => node.id === id);
  }

  async function refreshTimesyncDiff() {
    try {
      timesyncRaw = await fetchTimesyncDiff();
    } catch {
      timesyncRaw = null;
    }
  }

  async function refreshAudioDefaults() {
    try {
      audioDefaults = await fetchAudioDefaults();
    } catch (error) {
      audioDefaults = {
        available: false,
        ok: false,
        error: error?.message ?? 'audio check failed',
        sink: null,
        source: null
      };
    }
  }

  async function refreshRosNodes() {
    const missionId = activeMissionTab;
    const missionLabel = missionTabs.find((tab) => tab.id === missionId)?.label ?? missionId;

    try {
      const payload = await fetchRosNodes(missionId);
      if (missionId !== activeMissionTab) return;

      rosNodes = payload.nodes ?? [];
      rosNodesError = payload.error ?? '';
      rosNodeMissionLabel = payload.mission_label ?? missionLabel;
      const onlineCount = rosNodes.filter((node) => node.online).length;
      rosNodeMeta = payload.available
        ? `${rosNodeMissionLabel} · ${onlineCount} / ${rosNodes.length}`
        : `${rosNodeMissionLabel} · unavailable`;
    } catch (error) {
      if (missionId !== activeMissionTab) return;

      rosNodes = [];
      rosNodesError = error?.message ?? 'node check failed';
      rosNodeMissionLabel = missionLabel;
      rosNodeMeta = `${missionLabel} · error`;
    }
  }

  function resetTopicRows() {
    topicRows = TOPIC_TARGETS.map((name) => ({
      topic: name,
      status: 'WAIT',
      hz: 0,
      age_s: null,
      delay_ms: null,
      max_delay_ms: null,
      type: '',
      error: '',
      count: 0
    }));
  }

  function topicStatusClass(status) {
    if (status === 'OK') return 'ok';
    if (status === 'WAIT' || status === 'STALE') return 'warn';
    if (status === 'ERROR') return 'err';
    return 'idle';
  }

  function fmtTopicNumber(value, digits = 1) {
    return Number.isFinite(value) ? value.toFixed(digits) : '-';
  }

  function fmtTopicAge(value) {
    return Number.isFinite(value) ? `${value.toFixed(1)}s` : '-';
  }

  function fmtTopicDelay(value) {
    return Number.isFinite(value) ? `${value.toFixed(1)}ms` : '-';
  }

  function parseTopicLog(line) {
    if (!line || line[0] !== '{') return null;
    try {
      const payload = JSON.parse(line);
      return payload?.event === 'topic' && payload.topic ? payload : null;
    } catch {
      return null;
    }
  }

  function applyTopicLogEntries(entries) {
    if (!entries?.length) return;

    const byName = new Map(topicRows.map((row) => [row.topic, row]));
    let changed = false;

    for (const entry of entries) {
      if (entry.ts != null) {
        topicCheckLastLogTs = Math.max(topicCheckLastLogTs ?? entry.ts, entry.ts);
      }

      const parsed = parseTopicLog(entry.line);
      if (!parsed || !byName.has(parsed.topic)) continue;

      byName.set(parsed.topic, {
        topic: parsed.topic,
        status: parsed.status ?? 'WAIT',
        hz: Number(parsed.hz ?? 0),
        age_s: parsed.age_s == null ? null : Number(parsed.age_s),
        delay_ms: parsed.delay_ms == null ? null : Number(parsed.delay_ms),
        max_delay_ms: parsed.max_delay_ms == null ? null : Number(parsed.max_delay_ms),
        type: parsed.type ?? '',
        error: parsed.error ?? '',
        count: Number(parsed.count ?? 0)
      });
      changed = true;
    }

    if (changed) {
      topicRows = TOPIC_TARGETS.map((name) => byName.get(name));
    }
  }

  async function refreshTopicCheckStatus() {
    try {
      const payload = await fetchLaunchStatus();
      topicCheckRunning = Boolean(payload?.[TOPIC_CHECK_PROFILE]?.running);
    } catch {
      topicCheckRunning = false;
      topicCheckError = 'Launcher backend unavailable';
    }
  }

  async function refreshTopicCheckLogs() {
    if (!topicPanelOpen && !topicCheckRunning) return;

    try {
      const payload = await fetchProfileLogSince(TOPIC_CHECK_PROFILE, topicCheckLastLogTs);
      applyTopicLogEntries(payload.lines ?? []);
      if (payload.running != null) topicCheckRunning = Boolean(payload.running);
      if (topicCheckBusy !== 'stop' && !payload.running && payload.exit_code !== null && payload.exit_code !== 0 && payload.exit_code !== -2) {
        topicCheckError = `Topic Check stopped: exit ${payload.exit_code}`;
      }
    } catch (error) {
      if (topicCheckRunning) {
        topicCheckError = error?.message ?? 'Topic Check log unavailable';
      }
    }
  }

  async function startTopicCheck() {
    topicCheckBusy = 'start';
    topicCheckError = '';
    topicCheckLastLogTs = null;
    resetTopicRows();
    try {
      await launchProfile(TOPIC_CHECK_PROFILE);
      topicCheckRunning = true;
      topicPanelOpen = true;
      await refreshTopicCheckLogs();
    } catch (error) {
      topicCheckError = error?.message ?? 'Topic Check start failed';
    } finally {
      topicCheckBusy = '';
      refreshTopicCheckStatus();
    }
  }

  async function stopTopicCheck() {
    topicCheckBusy = 'stop';
    topicCheckError = '';
    topicPanelOpen = false;
    topicCheckRunning = false;
    topicCheckLastLogTs = null;
    resetTopicRows();
    try {
      await stopProfile(TOPIC_CHECK_PROFILE);
      topicCheckRunning = false;
      topicCheckError = '';
      topicCheckLastLogTs = null;
      resetTopicRows();
    } catch (error) {
      topicCheckError = error?.message ?? 'Topic Check stop failed';
    } finally {
      topicCheckBusy = '';
    }
  }

  function selectMissionTab(tabId) {
    if (tabId === activeMissionTab) return;
    activeMissionTab = tabId;
    rosNodeMissionLabel = missionTabs.find((tab) => tab.id === tabId)?.label ?? tabId;
    rosNodeMeta = `${rosNodeMissionLabel} · checking…`;
    rosNodesError = '';
    rosNodes = [];
    refreshRosNodes();
  }

  async function surfaceCrashLog(profile) {
    const node = nodeById(profile);
    const name = node?.name ?? profile;
    try {
      const payload = await fetchProfileLog(profile, 20);
      const tail = (payload.lines ?? []).map((entry) => entry.line).join('\n');
      const exit = payload.exit_code ?? '?';
      launcherError = `[${name}] exited unexpectedly (code ${exit})\n--- last log lines ---\n${tail || '(no output)'}`;
    } catch (error) {
      launcherError = `[${name}] exited unexpectedly (could not fetch log: ${error?.message ?? error})`;
    }
  }

  function parseTag(line) {
    const match = TAG_REGEX.exec(line);
    if (!match) return { tag: UNTAGGED_KEY, body: line };
    return { tag: match[1].trim() || UNTAGGED_KEY, body: line.slice(match[0].length) };
  }

  function appendLogEntries(entries) {
    if (!entries?.length) return new Set();

    const touched = new Set();
    let orderChanged = false;
    const nextOrder = [...tagOrder];
    const nextLogsByTag = { ...logsByTag };

    for (const entry of entries) {
      if (!entry?.line) continue;

      const { tag, body } = parseTag(entry.line);
      if (!nextLogsByTag[tag]) {
        nextLogsByTag[tag] = [];
        nextOrder.push(tag);
        orderChanged = true;
      }
      const arr = [...nextLogsByTag[tag], { ts: entry.ts, line: body }];
      if (arr.length > MAX_LINES_PER_TAG) {
        arr.splice(0, arr.length - MAX_LINES_PER_TAG);
      }
      nextLogsByTag[tag] = arr;
      touched.add(tag);
      if (entry.ts != null) {
        lastLogTs = Math.max(lastLogTs ?? entry.ts, entry.ts);
      }
    }

    if (touched.size > 0) {
      logsByTag = nextLogsByTag;
    }
    if (orderChanged) {
      tagOrder = nextOrder;
    }
    return touched;
  }

  async function scrollTagsToBottom(tags) {
    if (!tags || tags.size === 0) return;
    await tick();
    for (const tag of tags) {
      const node = logViewports[tag];
      if (node) node.scrollTop = node.scrollHeight;
    }
  }

  async function scrollAllTagsToBottom() {
    await tick();
    for (const tag of tagOrder) {
      const node = logViewports[tag];
      if (node) node.scrollTop = node.scrollHeight;
    }
  }

  function closeLogSocket() {
    if (logReconnectTimer) {
      clearTimeout(logReconnectTimer);
      logReconnectTimer = null;
    }
    if (logSocket) {
      logSocket.close();
      logSocket = null;
    }
    logConnected = false;
  }

  function stopLogPolling() {
    if (logPollTimer) {
      clearTimeout(logPollTimer);
      logPollTimer = null;
    }
    logPollActive = false;
  }

  async function pollLogUpdates(profile) {
    if (logPollActive || openLogProfile !== profile) return;

    logPollActive = true;
    try {
      const payload = await fetchProfileLogSince(profile, lastLogTs);
      if (openLogProfile !== profile) return;
      logRunning = payload.running;
      logExitCode = payload.exit_code;
      const touched = appendLogEntries(payload.lines ?? []);
      if (touched.size > 0) {
        await scrollTagsToBottom(touched);
      }
    } catch (error) {
      if (openLogProfile === profile) {
        logError = `Could not refresh logs: ${error?.message ?? error}`;
      }
    } finally {
      logPollActive = false;
      if (openLogProfile === profile && !logConnected) {
        logPollTimer = setTimeout(() => pollLogUpdates(profile), 1000);
      }
    }
  }

  function scheduleLogReconnect(profile) {
    if (logReconnectTimer || openLogProfile !== profile) return;

    logReconnectTimer = setTimeout(async () => {
      logReconnectTimer = null;
      if (openLogProfile !== profile) return;

      try {
        const payload = await fetchProfileLog(profile, 0);
        if (openLogProfile !== profile) return;
        logRunning = payload.running;
        logExitCode = payload.exit_code;
        logsByTag = {};
        tagOrder = [];
        logViewports = {};
        appendLogEntries(payload.lines ?? []);
        await scrollAllTagsToBottom();
      } catch (error) {
        if (openLogProfile === profile) {
          logError = `Could not refresh logs: ${error?.message ?? error}`;
        }
      }

      if (openLogProfile === profile && logStreamSupported) {
        openLogStream(profile);
      }
    }, 1000);
  }

  function closeLogViewer() {
    closeLogSocket();
    stopLogPolling();
    openLogProfile = null;
    openLogName = '';
    logsByTag = {};
    tagOrder = [];
    logViewports = {};
    logRunning = false;
    logLoading = false;
    logExitCode = null;
    logError = '';
    logStreamSupported = true;
    lastLogTs = null;
    saveStatus = '';
    saveBusy = false;
  }

  async function triggerPose(name) {
    if (poseBusy) return;
    poseBusy = name;
    launcherError = '';
    try {
      await gotoPose(name);
    } catch (error) {
      launcherError = `[pose ${name}] ${error?.message ?? 'failed'}`;
    } finally {
      poseBusy = '';
    }
  }

  async function saveLogs() {
    if (!openLogProfile || saveBusy) return;
    saveBusy = true;
    saveStatus = 'saving…';
    try {
      const result = await saveProfileLog(openLogProfile);
      saveStatus = `saved · ${result.lines} lines → ${result.path}`;
    } catch (error) {
      saveStatus = `save failed: ${error?.message ?? error}`;
    } finally {
      saveBusy = false;
    }
  }

  function openLogStream(profile) {
    if (!logStreamSupported) return;
    closeLogSocket();

    const ws = new WebSocket(profileLogSocketUrl(profile, { replay: false }));
    logSocket = ws;

    ws.onopen = () => {
      if (openLogProfile !== profile) return;
      stopLogPolling();
      logConnected = true;
      logError = '';
    };

    ws.onmessage = async (event) => {
      if (openLogProfile !== profile) return;

      try {
        const entry = JSON.parse(event.data);
        const touched = appendLogEntries([entry]);
        if (touched.size > 0) {
          await scrollTagsToBottom(touched);
        }
      } catch (error) {
        console.warn('log stream parse failed', error);
      }
    };

    ws.onerror = () => {
      if (openLogProfile !== profile) return;
      logStreamSupported = false;
      logError = 'log stream unavailable · polling';
    };

    ws.onclose = () => {
      if (logSocket === ws) {
        logSocket = null;
        logConnected = false;
      }
      if (openLogProfile === profile) {
        if (logStreamSupported) {
          scheduleLogReconnect(profile);
        }
        pollLogUpdates(profile);
      }
    };
  }

  async function toggleLogs(profile) {
    if (openLogProfile === profile) {
      closeLogViewer();
      return;
    }

    const requestedProfile = profile;
    const node = nodeById(profile);
    openLogProfile = profile;
    openLogName = node?.name ?? profile;
    logsByTag = {};
    tagOrder = [];
    logViewports = {};
    logRunning = prevProfileStatus[profile] === 'up';
    logLoading = true;
    logConnected = false;
    logExitCode = null;
    logError = '';
    logStreamSupported = true;
    lastLogTs = null;
    stopLogPolling();

    try {
      const payload = await fetchProfileLog(profile, 0);
      if (openLogProfile !== requestedProfile) return;
      logRunning = payload.running;
      logExitCode = payload.exit_code;
      appendLogEntries(payload.lines ?? []);
      await scrollAllTagsToBottom();
      openLogStream(profile);
      logPollTimer = setTimeout(() => pollLogUpdates(profile), 1200);
    } catch (error) {
      if (openLogProfile === requestedProfile) {
        logError = `Could not load logs: ${error?.message ?? error}`;
      }
    } finally {
      if (openLogProfile === requestedProfile) {
        logLoading = false;
      }
    }
  }

  async function refreshManagedProfiles() {
    try {
      const payload = await fetchLaunchStatus();
      backendOffline = false;

      for (const profile of managedProfiles) {
        if (busyProfiles[profile]) continue;

        const newStatus = payload[profile]?.running ? 'up' : 'down';
        const prev = prevProfileStatus[profile];

        if (prev === 'up' && newStatus === 'down') {
          if (pendingStop[profile]) {
            pendingStop = { ...pendingStop, [profile]: false };
          } else {
            surfaceCrashLog(profile);
          }
        }

        prevProfileStatus[profile] = newStatus;
        updateNode(profile, { status: newStatus });

        if (profile === openLogProfile) {
          logRunning = payload[profile]?.running ?? false;
        }
      }
    } catch {
      backendOffline = true;
    }
  }

  async function toggle(profile) {
    if (busyProfiles[profile]) return;
    const node = nodeById(profile);
    if (!node) return;

    busyProfiles = { ...busyProfiles, [profile]: true };
    updateNode(profile, { status: 'starting' });

    try {
      if (node.status === 'up') {
        pendingStop = { ...pendingStop, [profile]: true };
        if (openLogProfile === profile) {
          logsByTag = {};
          tagOrder = [];
          logViewports = {};
          logExitCode = null;
          logError = '';
          saveStatus = '';
        }
        await stopProfile(profile);
      } else {
        if (openLogProfile === profile) {
          logsByTag = {};
          tagOrder = [];
          logViewports = {};
          logExitCode = null;
          logError = '';
          saveStatus = '';
        }
        await launchProfile(profile);
      }
      launcherError = '';
    } catch (error) {
      console.error(error);
      launcherError = `[${node.name}] ${error?.message ?? 'control failed'}`;
    } finally {
      busyProfiles = { ...busyProfiles, [profile]: false };
      await refreshManagedProfiles();
    }
  }

  async function startAllMission() {
    if (bulkStartBusy || bulkStopBusy) return;
    const config = MISSION_BULK_CONFIG[activeMissionTab];
    if (!config) return;

    bulkStartBusy = true;
    launcherError = '';

    const startOne = async (id) => {
      const node = nodeById(id);
      if (!node || node.status === 'up' || node.status === 'starting' || busyProfiles[id]) return;
      try {
        busyProfiles = { ...busyProfiles, [id]: true };
        updateNode(id, { status: 'starting' });
        await launchProfile(id);
      } catch (error) {
        launcherError = `[${node.name}] ${error?.message ?? 'start failed'}`;
      } finally {
        busyProfiles = { ...busyProfiles, [id]: false };
      }
    };

    const excluded = new Set(config.exclude ?? []);

    const startStage = async (ids) => {
      const targets = ids.filter((id) => {
        const n = nodeById(id);
        return n && !excluded.has(id) && n.status !== 'up' && n.status !== 'starting' && !busyProfiles[id];
      });
      await Promise.all(targets.map(startOne));
    };

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    try {
      const stage1 = defaultNodes.map((n) => n.id);
      const stage2 = config.earlyStage;
      const stage4 = config.lateStage;
      const stage3 = missionNodes
        .map((n) => n.id)
        .filter((id) => !stage2.includes(id) && !stage4.includes(id));

      await startStage(stage1);
      await sleep(5000);
      await startStage(stage2);
      await sleep(1000);
      await startStage(stage3);
      if (stage4.length > 0) {
        await sleep(1000);
        await startStage(stage4);
      }
    } finally {
      bulkStartBusy = false;
      await refreshManagedProfiles();
    }
  }

  async function stopAllMission() {
    if (bulkStartBusy || bulkStopBusy) return;
    if (!MISSION_BULK_CONFIG[activeMissionTab]) return;

    bulkStopBusy = true;
    launcherError = '';

    const stopOne = async (id) => {
      const node = nodeById(id);
      if (!node || node.status !== 'up' || busyProfiles[id]) return;
      try {
        busyProfiles = { ...busyProfiles, [id]: true };
        pendingStop = { ...pendingStop, [id]: true };
        await stopProfile(id);
      } catch (error) {
        launcherError = `[${node.name}] ${error?.message ?? 'stop failed'}`;
      } finally {
        busyProfiles = { ...busyProfiles, [id]: false };
      }
    };

    try {
      const targets = [...defaultNodes, ...missionNodes]
        .filter((n) => n.status === 'up' && !busyProfiles[n.id])
        .map((n) => n.id);
      await Promise.all(targets.map(stopOne));
    } finally {
      bulkStopBusy = false;
      await refreshManagedProfiles();
    }
  }

  onMount(() => {
    refreshManagedProfiles();
    refreshTimesyncDiff();
    refreshAudioDefaults();
    refreshRosNodes();
    refreshTopicCheckStatus();
    refreshTopicCheckLogs();
    const statusTimer = setInterval(refreshManagedProfiles, 1500);
    const diffTimer = setInterval(refreshTimesyncDiff, 1000);
    const audioTimer = setInterval(refreshAudioDefaults, 3000);
    const nodeTimer = setInterval(refreshRosNodes, 1500);
    const topicStatusTimer = setInterval(refreshTopicCheckStatus, 1500);
    const topicLogTimer = setInterval(refreshTopicCheckLogs, 1000);
    return () => {
      closeLogSocket();
      stopLogPolling();
      clearInterval(statusTimer);
      clearInterval(diffTimer);
      clearInterval(audioTimer);
      clearInterval(nodeTimer);
      clearInterval(topicStatusTimer);
      clearInterval(topicLogTimer);
    };
  });

  $: syncDot = timesyncRaw?.available
    ? Math.abs(timesyncRaw.diff_s * 1000) < 5
      ? 'ok'
      : Math.abs(timesyncRaw.diff_s * 1000) < 50
      ? 'warn'
      : 'err'
    : 'idle';
</script>

<div class="launcher" class:local-fixed-ui={$localFixedUi}>
  <BackBar title="Launcher" to="landing">
    <div class="pose-buttons">
      {#each POSE_BUTTONS as pose (pose)}
        <button
          type="button"
          class="pose-btn"
          class:pose-zero={pose === 'zero'}
          class:pose-ready={pose === 'ready'}
          class:pose-packing={pose === 'packing'}
          class:busy={poseBusy === pose}
          disabled={poseBusy !== '' && poseBusy !== pose}
          on:click={() => triggerPose(pose)}
        >
          {poseBusy === pose ? `${pose}…` : pose}
        </button>
      {/each}
    </div>
  </BackBar>

  <div class="body">
    <div class="main-col">
      {#if launcherNote}
        <div class="note" class:err={launcherError}>
          <pre>{launcherNote}</pre>
          {#if launcherError}
            <button type="button" class="note-dismiss" on:click={() => (launcherError = '')} aria-label="dismiss">×</button>
          {/if}
        </div>
      {/if}

      <!-- Sync monitor: always-on date diff measurement -->
      <section class="card sync">
        <div class="card-head">
          <span class="card-title">Sync monitor</span>
          <div class="sync-head-actions">
            <span class="card-meta mono">{timesyncRaw?.remote ?? '—'}</span>
            <button
              type="button"
              class="sync-log-btn"
              class:active={openLogProfile === 'timesync'}
              on:click={() => toggleLogs('timesync')}
            >
              {openLogProfile === 'timesync' ? 'Hide logs' : 'Logs'}
            </button>
            <button
              type="button"
              class="sync-control-btn"
              class:stop={timesyncActionIsStop}
              disabled={timesyncStatus === 'starting'}
              on:click={() => toggle('timesync')}
            >
              {timesyncActionLabel}
            </button>
          </div>
        </div>
        <div class="sync-body">
          <span class="dot {syncDot}"></span>
          {#if timesyncRaw?.available}
            <div class="sync-main">
              <span class="sync-diff mono {syncDot}">
                {(timesyncRaw.diff_s >= 0 ? '+' : '')}{timesyncRaw.diff_s.toFixed(6)} s
              </span>
              <span class="sync-meta mono">
                rtt {timesyncRaw.rtt_s.toFixed(4)} s · {timesyncRaw.age_s.toFixed(1)}s ago
              </span>
            </div>
          {:else}
            <div class="sync-main">
              <span class="sync-diff muted">— no sample —</span>
              <span class="sync-meta">{timesyncRaw?.reason ?? 'connecting…'}</span>
            </div>
          {/if}
        </div>
      </section>

      <section class="card compact-card">
        <div class="card-head">
          <span class="card-title">Default</span>
          <span class="card-meta mono">{defaultNodes.filter((n) => n.status === 'up').length} / {defaultNodes.length}</span>
        </div>
        <div class="card-body list compact-list">
          {#each defaultNodes as n (n.id)}
            <NodeButton
              name={n.name}
              desc={n.desc}
              status={n.status}
              logsOpen={openLogProfile === n.id}
              onLogs={() => toggleLogs(n.id)}
              onToggle={() => toggle(n.id)}
            />
          {/each}
        </div>
      </section>

      <section class="card compact-card mission-card">
        <div class="card-head">
          <span class="card-title">Mission</span>
          <span class="card-meta mono">{activeMissionLabel} · {missionNodes.filter((n) => n.status === 'up').length} / {missionNodes.length}</span>
        </div>
        <div class="mission-tabs">
          {#each missionTabs as tab (tab.id)}
            <button
              type="button"
              class="mission-tab"
              class:active={tab.id === activeMissionTab}
              on:click={() => selectMissionTab(tab.id)}
            >
              {tab.label}
            </button>
          {/each}
          {#if bulkConfig}
            <button
              type="button"
              class="mission-start-all"
              class:busy={bulkStartBusy}
              disabled={bulkStartBusy || bulkStopBusy}
              on:click={startAllMission}
            >
              {bulkStartBusy ? 'starting…' : 'Start All'}
            </button>
            <button
              type="button"
              class="mission-stop-all"
              class:busy={bulkStopBusy}
              disabled={bulkStartBusy || bulkStopBusy}
              on:click={stopAllMission}
            >
              {bulkStopBusy ? 'stopping…' : 'Stop All'}
            </button>
          {/if}
        </div>
        <div class="card-body list compact-list mission-list scroll">
          {#if missionNodes.length > 0}
            {#each missionNodes as n (n.id)}
              <NodeButton
                name={n.name}
                desc={n.desc}
                status={n.status}
                logsOpen={openLogProfile === n.id}
                onLogs={() => toggleLogs(n.id)}
                onToggle={() => toggle(n.id)}
              />
            {/each}
          {:else}
            <div class="mission-empty">
              No subsystem mapped to this mission yet.
            </div>
          {/if}
        </div>
      </section>
    </div>

    <div class="side-col">
      <section class="card log-card">
        <div class="card-head">
          <span class="card-title">Logs{openLogProfile ? ` · ${openLogName}` : ''}</span>
          <span class="card-meta mono">{openLogProfile ? logMeta : 'select a profile'}</span>
        </div>
        {#if openLogProfile}
          <div class="log-toolbar">
            <div class="log-status">
              <span class="log-chip" class:live={logConnected} class:stop={!logRunning && logExitCode != null}>
                {logConnected ? 'stream on' : 'stream off'}
              </span>
              <span class="log-chip" class:run={logRunning} class:stop={!logRunning && logExitCode != null}>
                {logRunning ? 'running' : logExitCode == null ? 'idle' : `exit ${logExitCode}`}
              </span>
              {#if logError}
                <span class="log-error">{logError}</span>
              {/if}
              {#if saveStatus}
                <span class="log-save-status" class:err={saveStatus.startsWith('save failed')}>{saveStatus}</span>
              {/if}
            </div>

            <div class="log-actions">
              <button type="button" class="log-save" on:click={saveLogs} disabled={saveBusy || tagOrder.length === 0}>
                {saveBusy ? 'Saving…' : 'Save'}
              </button>
              <button type="button" class="log-close" on:click={closeLogViewer}>
                Hide logs
              </button>
            </div>
          </div>
          <div class="log-body">
            {#if tagOrder.length > 0}
              <div
                class="log-grid scroll"
                style={`--pane-count: ${tagOrder.length}; --log-grid-cols: ${logGridColumns}; --log-pane-min-height: ${logPaneMinHeight}px;`}
              >
                {#each tagOrder as tag (tag)}
                  <div class="log-pane">
                    <div class="log-pane-head">
                      <span class="log-pane-name mono">{tag === UNTAGGED_KEY ? UNTAGGED_LABEL : tag}</span>
                      <span class="log-pane-meta mono">{logsByTag[tag]?.length ?? 0}</span>
                    </div>
                    <div class="log-pane-body" bind:this={logViewports[tag]}>
                      {#each logsByTag[tag] ?? [] as entry, index (`${entry.ts ?? index}:${index}`)}
                        <div class="log-line mono">{entry.line}</div>
                      {/each}
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="log-console">
                {#if logLoading}
                  <div class="log-empty mono">Loading buffered lines…</div>
                {:else}
                  <div class="log-empty mono">No log lines yet.</div>
                {/if}
              </div>
            {/if}
          </div>
        {:else}
          <div class="log-placeholder">
            Pick `Logs` on any subsystem card to open a live scrollable console here.
          </div>
        {/if}
      </section>

      <section class="card side-card">
        <div class="card-head">
          <span class="card-title">Nodes</span>
          <span class="card-meta mono">{rosNodeMeta}</span>
        </div>
        <div class="card-body list node-list scroll">
          {#if rosNodes.length > 0}
            {#each rosNodes as node (node.name)}
              <div class="node-row">
                <span class="dot {node.online ? 'ok' : 'idle'}"></span>
                <div class="node-info">
                  <div class="node-name mono">{node.name}</div>
                  <div class="node-desc">{node.online ? 'detected via ros2 node list' : 'not detected'}</div>
                </div>
                <div class="node-state" class:down={!node.online}>
                  {node.online ? 'UP' : 'DOWN'}
                </div>
              </div>
            {/each}
          {:else}
            <div class="node-empty">
              {rosNodesError || `No node targets mapped to ${rosNodeMissionLabel} yet.`}
            </div>
          {/if}

          {#if rosNodesError && rosNodes.length > 0}
            <div class="node-error">{rosNodesError}</div>
          {/if}
        </div>
      </section>

      <section class="card side-card audio-card">
        <div class="card-head">
          <span class="card-title">Audio defaults</span>
          <div class="audio-head-actions">
            <span class="card-meta mono">{audioDefaults?.available ? (audioDefaults.ok ? 'matched' : 'mismatch') : 'checking'}</span>
            <button
              type="button"
              class="audio-log-btn"
              class:active={openLogProfile === AUDIO_DEFAULTS_PROFILE}
              on:click={() => toggleLogs(AUDIO_DEFAULTS_PROFILE)}
            >
              {openLogProfile === AUDIO_DEFAULTS_PROFILE ? 'Hide logs' : 'Logs'}
            </button>
            <button
              type="button"
              class="audio-control-btn"
              class:stop={audioDefaultsStatus === 'up'}
              disabled={audioDefaultsBusy}
              on:click={() => toggle(AUDIO_DEFAULTS_PROFILE)}
            >
              {audioDefaultsActionLabel}
            </button>
          </div>
        </div>
        <div class="audio-body">
          <div class="audio-main">
            {#if audioDefaults?.available}
              {#each [audioDefaults.sink, audioDefaults.source] as item (item.label)}
                <div class="audio-row">
                  <span class="audio-label">{item.label}</span>
                  <span class="audio-value mono" class:bad={!item.ok}>{item.actual ?? 'not found'}</span>
                </div>
              {/each}
            {:else}
              <div class="audio-row">
                <span class="audio-label">pactl info</span>
                <span class="audio-value bad">{audioDefaults?.error ?? 'checking...'}</span>
              </div>
            {/if}
          </div>
        </div>
      </section>

      <section class="card side-card topic-card" class:open={topicPanelOpen}>
        <div class="card-head">
          <span class="card-title">Topics</span>
          <span class="card-meta mono">{topicSummary}</span>
        </div>
        <div class="topic-toolbar">
          <div class="topic-state">
            <span class="dot {topicDot}"></span>
            <span>{topicCheckRunning ? 'subscribing' : 'stopped'}</span>
          </div>
          <div class="topic-actions">
            <button
              type="button"
              class="topic-action start"
              disabled={topicCheckRunning || topicCheckBusy}
              on:click={startTopicCheck}
            >
              {topicCheckBusy === 'start' ? 'Starting…' : 'Start'}
            </button>
            <button
              type="button"
              class="topic-action stop"
              disabled={!topicCheckRunning || topicCheckBusy}
              on:click={stopTopicCheck}
            >
              {topicCheckBusy === 'stop' ? 'Stopping…' : 'Stop'}
            </button>
          </div>
        </div>
        {#if topicPanelOpen}
          <div class="card-body topic-body scroll">
          {#if topicCheckError}
            <div class="topic-check-error">{topicCheckError}</div>
          {/if}
          <div class="topic-table">
            <div class="topic-table-head">
              <span>Topic</span>
              <span>Hz</span>
              <span>Delay</span>
              <span>Last</span>
              <span>Status</span>
            </div>
            {#each topicRows as t (t.topic)}
              <div class="topic-table-row">
                <div class="topic-name-cell">
                  <span class="topic-name mono">{t.topic}</span>
                  <span class="topic-type mono">{t.type || 'waiting type'}</span>
                </div>
                <span class="topic-num mono">{fmtTopicNumber(t.hz)}</span>
                <span class="topic-num mono">{fmtTopicDelay(t.delay_ms)}</span>
                <span class="topic-num mono">{fmtTopicAge(t.age_s)}</span>
                <span class="topic-status mono">
                  <span class="dot {topicStatusClass(t.status)}"></span>
                  {t.status}
                </span>
              </div>
              {#if t.error}
                <div class="topic-row-error">{t.error}</div>
              {/if}
            {/each}
          </div>
          </div>
        {/if}
      </section>
    </div>
  </div>
</div>

<style>
  .launcher {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  /* Thin, click-draggable scrollbar — applied only inside card bodies and
     existing .scroll regions. Outer containers fall back to the native bar. */
  .launcher :global(.card-body),
  .launcher :global(.scroll) {
    scrollbar-width: thin;
    scrollbar-color: var(--border-3) transparent;
  }

  .launcher :global(.card-body::-webkit-scrollbar),
  .launcher :global(.scroll::-webkit-scrollbar) {
    width: 8px;
    height: 8px;
  }

  .launcher :global(.card-body::-webkit-scrollbar-track),
  .launcher :global(.scroll::-webkit-scrollbar-track) {
    background: transparent;
  }

  .launcher :global(.card-body::-webkit-scrollbar-thumb),
  .launcher :global(.scroll::-webkit-scrollbar-thumb) {
    background: var(--border-3);
    border-radius: 999px;
    min-height: 24px;
  }

  .launcher :global(.card-body::-webkit-scrollbar-thumb:hover),
  .launcher :global(.scroll::-webkit-scrollbar-thumb:hover) {
    background: var(--text-3);
  }

  .launcher :global(.card-body::-webkit-scrollbar-thumb:active),
  .launcher :global(.scroll::-webkit-scrollbar-thumb:active) {
    background: var(--text-2);
  }

  .pose-buttons {
    display: flex;
    gap: 6px;
  }

  .pose-btn {
    height: 30px;
    padding: 0 14px;
    color: var(--pose-color, var(--text-1));
    background: var(--pose-bg, var(--bg-1));
    border: 1px solid var(--pose-border, var(--border-2));
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    text-transform: capitalize;
    cursor: pointer;
    transition: color 0.12s ease, background 0.12s ease, border-color 0.12s ease;
  }

  .pose-zero {
    --pose-color: #dc2626;
    --pose-bg: rgba(220, 38, 38, 0.08);
    --pose-border: rgba(220, 38, 38, 0.28);
    --pose-bg-hover: rgba(220, 38, 38, 0.14);
  }

  .pose-ready {
    --pose-color: #16a34a;
    --pose-bg: rgba(22, 163, 74, 0.08);
    --pose-border: rgba(22, 163, 74, 0.28);
    --pose-bg-hover: rgba(22, 163, 74, 0.14);
  }

  .pose-packing {
    --pose-color: #2563eb;
    --pose-bg: rgba(37, 99, 235, 0.08);
    --pose-border: rgba(37, 99, 235, 0.28);
    --pose-bg-hover: rgba(37, 99, 235, 0.14);
  }

  .pose-btn:hover:not(:disabled) {
    color: var(--pose-color, var(--text-0));
    background: var(--pose-bg-hover, var(--bg-2));
    border-color: var(--pose-color, var(--border-3));
  }

  .pose-btn.busy {
    color: #ffffff;
    background: var(--pose-color, var(--ok));
    border-color: var(--pose-color, var(--ok));
  }

  .pose-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .body {
    flex: 1;
    padding: 12px 14px 14px;
    display: grid;
    grid-template-columns: minmax(0, 1.12fr) minmax(360px, 0.88fr);
    gap: 12px;
    min-height: 0;
    overflow: auto;
    max-width: none;
    width: 100%;
  }

  .main-col,
  .side-col {
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    /* always-on bar so the column scrollbar is visible + draggable */
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .card {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .card-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-1);
    background: #ffffff;
  }

  .card-title {
    color: var(--text-1);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .card-meta {
    color: var(--text-3);
    font-size: 11px;
  }

  .sync-head-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .sync-log-btn,
  .sync-control-btn {
    height: 24px;
    padding: 0 10px;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-2);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .sync-log-btn:hover,
  .sync-control-btn:hover:not(:disabled) {
    color: var(--text-0);
    background: var(--bg-2);
    border-color: var(--border-3);
  }

  .sync-log-btn.active {
    color: var(--ok);
    border-color: rgba(22, 163, 74, 0.28);
    background: rgba(22, 163, 74, 0.06);
  }

  .sync-control-btn.stop {
    color: var(--err);
    border-color: rgba(220, 38, 38, 0.28);
    background: #ffffff;
  }

  .sync-control-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .card-body {
    padding: 8px 10px;
    overflow: auto;
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .compact-card {
    overflow: hidden;
  }

  .compact-list {
    gap: 4px;
  }

  .mission-card {
    flex: 1;
    min-height: 0;
  }

  .mission-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 10px 0;
    background: #ffffff;
  }

  .mission-tab {
    min-height: 26px;
    padding: 0 10px;
    color: var(--text-2);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .mission-tab:hover {
    color: var(--text-0);
    border-color: var(--border-3);
    background: var(--bg-2);
  }

  .mission-tab.active {
    color: var(--text-0);
    border-color: rgba(22, 163, 74, 0.24);
    background: rgba(22, 163, 74, 0.08);
  }

  .mission-start-all {
    margin-left: auto;
    min-height: 26px;
    padding: 0 12px;
    color: #ffffff;
    background: rgba(22, 163, 74, 0.92);
    border: 1px solid rgba(22, 163, 74, 0.24);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
  }

  .mission-start-all:hover:not(:disabled) {
    background: rgba(21, 128, 61, 0.95);
  }

  .mission-start-all:disabled,
  .mission-start-all.busy {
    opacity: 0.65;
    cursor: progress;
  }

  .mission-stop-all {
    min-height: 26px;
    padding: 0 12px;
    color: #ffffff;
    background: rgba(220, 38, 38, 0.92);
    border: 1px solid rgba(220, 38, 38, 0.24);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
  }

  .mission-stop-all:hover:not(:disabled) {
    background: rgba(185, 28, 28, 0.95);
  }

  .mission-stop-all:disabled,
  .mission-stop-all.busy {
    opacity: 0.65;
    cursor: progress;
  }

  .mission-empty {
    padding: 6px 4px;
    color: var(--text-2);
    font-size: 12px;
  }

  .mission-list {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  /* Sync monitor */
  .sync-body {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: #ffffff;
  }

  .sync-main {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .sync-diff {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-0);
  }

  .sync-diff.ok { color: var(--ok); }
  .sync-diff.warn { color: var(--warn); }
  .sync-diff.err { color: var(--err); }
  .sync-diff.muted { color: var(--text-3); font-weight: 500; }

  .sync-meta {
    color: var(--text-2);
    font-size: 12px;
  }

  .audio-body {
    padding: 10px 12px;
    background: #ffffff;
  }

  .audio-main {
    min-width: 0;
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 8px;
  }

  .audio-row {
    min-width: 0;
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    gap: 8px;
    align-items: baseline;
  }

  .audio-label {
    color: var(--text-2);
    font-size: 11px;
    font-weight: 600;
  }

  .audio-value {
    min-width: 0;
    overflow-wrap: anywhere;
    color: var(--text-0);
    font-size: 11px;
    line-height: 1.35;
  }

  .audio-value.bad {
    color: var(--err);
  }

  .audio-head-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .audio-log-btn,
  .audio-control-btn {
    height: 24px;
    padding: 0 10px;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-2);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .audio-log-btn:hover,
  .audio-control-btn:hover:not(:disabled) {
    color: var(--text-0);
    background: var(--bg-2);
    border-color: var(--border-3);
  }

  .audio-log-btn.active {
    color: var(--ok);
    border-color: rgba(22, 163, 74, 0.28);
    background: rgba(22, 163, 74, 0.06);
  }

  .audio-control-btn.stop {
    color: var(--err);
    border-color: rgba(220, 38, 38, 0.28);
    background: #ffffff;
  }

  .audio-control-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .node-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 6px;
    border-bottom: 1px solid var(--border-1);
  }

  .node-row:last-child {
    border-bottom: none;
  }

  .node-info {
    flex: 1;
    min-width: 0;
  }

  .node-name {
    color: var(--text-0);
    font-size: 12px;
    font-weight: 600;
  }

  .node-desc {
    color: var(--text-2);
    font-size: 11px;
  }

  .node-state {
    flex-shrink: 0;
    min-width: 48px;
    color: var(--ok);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-align: right;
  }

  .node-state.down {
    color: var(--text-3);
  }

  .node-empty {
    padding: 8px 4px;
    color: var(--text-2);
    font-size: 12px;
  }

  .node-error {
    padding: 8px 4px 2px;
    color: var(--err);
    font-size: 12px;
  }

  .log-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 12px;
    background: #ffffff;
    border-bottom: 1px solid var(--border-1);
  }

  .log-status {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    min-width: 0;
    color: var(--text-2);
    font-size: 12px;
  }

  .log-chip {
    display: inline-flex;
    align-items: center;
    height: 24px;
    padding: 0 9px;
    color: var(--text-2);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .log-chip.live,
  .log-chip.run {
    color: var(--ok);
    border-color: rgba(22, 163, 74, 0.24);
    background: rgba(22, 163, 74, 0.06);
  }

  .log-chip.stop {
    color: var(--err);
    border-color: rgba(220, 38, 38, 0.24);
    background: rgba(220, 38, 38, 0.05);
  }

  .log-error {
    color: var(--err);
  }

  .log-close {
    flex-shrink: 0;
    height: 26px;
    padding: 0 12px;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
  }

  .log-close:hover {
    color: var(--text-0);
    background: var(--bg-2);
    border-color: var(--border-3);
  }

  .log-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .log-save {
    height: 26px;
    padding: 0 12px;
    color: #ffffff;
    background: var(--ok);
    border: 1px solid var(--ok);
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .log-save:hover:not(:disabled) {
    filter: brightness(0.95);
  }

  .log-save:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .log-save-status {
    color: var(--text-2);
    font-size: 11px;
    word-break: break-all;
  }

  .log-save-status.err {
    color: var(--err);
  }

  .log-console {
    flex: 1;
    min-height: 0;
    height: 100%;
    overflow: auto;
    padding: 12px 14px;
    background: #11151b;
    color: #e5e7eb;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    line-height: 1.5;
    user-select: text;
  }

  .log-grid {
    flex: 1;
    min-height: 0;
    height: 100%;
    overflow: auto;
    padding: 8px;
    background: #0a0d12;
    display: grid;
    grid-template-columns: repeat(var(--log-grid-cols, 1), minmax(0, 1fr));
    grid-auto-rows: minmax(var(--log-pane-min-height, 160px), 1fr);
    align-content: stretch;
    gap: 8px;
  }

  .log-pane {
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: #11151b;
    border: 1px solid #1f2731;
    border-radius: 6px;
    overflow: hidden;
  }

  .log-pane-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 10px;
    background: #161c25;
    border-bottom: 1px solid #1f2731;
  }

  .log-pane-name {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  .log-pane-meta {
    color: #64748b;
    font-size: 10px;
  }

  .log-pane-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 8px 10px;
    color: #e5e7eb;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px;
    line-height: 1.45;
    user-select: text;
  }

  .log-card {
    flex: 1.15 1 0;
    min-height: 0;
    height: 0;
    display: flex;
    flex-direction: column;
  }

  .log-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .log-placeholder {
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 18px;
    color: var(--text-2);
    background: #ffffff;
    text-align: center;
    font-size: 13px;
  }

  .log-line {
    white-space: pre-wrap;
    word-break: break-word;
    user-select: text;
  }

  .log-empty {
    color: #98a2b3;
    user-select: text;
  }

  .side-card {
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .node-list {
    max-height: 220px;
    overflow: auto;
  }

  .topic-card {
    flex: 0 0 auto;
  }

  .topic-card.open {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .topic-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 10px;
    background: #ffffff;
    border-bottom: 1px solid var(--border-1);
  }

  .topic-state {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    color: var(--text-1);
    font-size: 12px;
    font-weight: 600;
  }

  .topic-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .topic-action {
    height: 26px;
    padding: 0 11px;
    color: var(--text-1);
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .topic-action:hover:not(:disabled) {
    color: var(--text-0);
    background: var(--bg-2);
    border-color: var(--border-3);
  }

  .topic-action.start:not(:disabled) {
    color: var(--ok);
    border-color: rgba(22, 163, 74, 0.28);
    background: rgba(22, 163, 74, 0.06);
  }

  .topic-action.stop:not(:disabled) {
    color: var(--err);
    border-color: rgba(220, 38, 38, 0.28);
    background: rgba(220, 38, 38, 0.05);
  }

  .topic-action:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .topic-body {
    flex: 1;
    min-height: 0;
    max-height: 330px;
  }

  .topic-card.open .topic-body {
    max-height: none;
  }

  .topic-check-error {
    margin-bottom: 8px;
    padding: 7px 8px;
    color: var(--err);
    background: rgba(220, 38, 38, 0.05);
    border: 1px solid rgba(220, 38, 38, 0.18);
    border-radius: var(--radius);
    font-size: 12px;
  }

  .topic-table {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border-1);
    border-radius: var(--radius);
    overflow: hidden;
    background: #ffffff;
  }

  .topic-table-head,
  .topic-table-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) 42px 58px 44px 62px;
    align-items: center;
    gap: 6px;
  }

  .topic-table-head {
    min-height: 28px;
    padding: 0 8px;
    color: var(--text-3);
    background: var(--bg-1);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .topic-table-row {
    min-height: 48px;
    padding: 6px 8px;
    border-top: 1px solid var(--border-1);
    font-size: 11px;
  }

  .topic-name-cell {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .topic-name,
  .topic-type {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .topic-name {
    color: var(--text-0);
    font-size: 11px;
    font-weight: 700;
  }

  .topic-type {
    color: var(--text-3);
    font-size: 10px;
  }

  .topic-num {
    color: var(--text-1);
    text-align: right;
  }

  .topic-status {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
    color: var(--text-2);
    font-size: 10px;
    font-weight: 700;
  }

  .topic-row-error {
    padding: 0 8px 7px;
    color: var(--err);
    border-top: 1px solid var(--border-1);
    font-size: 10px;
  }

  /* Skeletons */
  .skeleton-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .skel-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 4px;
  }

  .skel-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--bg-3);
    flex-shrink: 0;
  }

  .skel-bar {
    height: 10px;
    background: var(--bg-3);
    border-radius: 4px;
  }

  .w-20 { width: 20%; }
  .w-25 { width: 25%; }
  .w-30 { width: 30%; }
  .w-35 { width: 35%; }
  .w-40 { width: 40%; }
  .w-50 { width: 50%; }
  .w-55 { width: 55%; }

  /* Note banner */
  .note {
    position: relative;
    padding: 10px 32px 10px 12px;
    color: var(--warn);
    background: rgba(217, 119, 6, 0.10);
    border: 1px solid rgba(217, 119, 6, 0.28);
    border-radius: var(--radius);
    font-size: 12px;
  }

  .note.err {
    color: var(--err);
    background: rgba(220, 38, 38, 0.06);
    border-color: rgba(220, 38, 38, 0.24);
  }

  .note pre {
    margin: 0;
    max-height: 220px;
    overflow: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
    color: inherit;
  }

  .note-dismiss {
    position: absolute;
    top: 4px;
    right: 6px;
    padding: 0 6px;
    color: inherit;
    background: transparent;
    border: none;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    opacity: 0.6;
  }

  .note-dismiss:hover {
    opacity: 1;
  }

  @media (max-width: 1180px) {
    .body {
      grid-template-columns: minmax(0, 1fr);
      overflow: auto;
    }

    .main-col,
    .side-col {
      overflow: visible;
    }

    .mission-card,
    .log-card {
      flex: none;
    }

    .mission-list,
    .node-list,
    .log-console {
      max-height: none;
    }
  }

  @media (max-width: 760px) {
    .pose-buttons {
      width: 100%;
      flex-wrap: wrap;
    }

    .pose-btn {
      flex: 1 1 calc(33.333% - 4px);
      min-width: 92px;
      padding: 0 10px;
    }

    .body {
      padding: 10px;
      gap: 10px;
    }

    .card-head,
    .log-toolbar {
      align-items: flex-start;
      gap: 8px;
      flex-direction: column;
    }

    .log-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .log-grid {
      grid-template-columns: 1fr;
      grid-auto-rows: minmax(180px, auto);
    }

    .log-console,
    .log-grid,
    .log-placeholder {
      min-height: 220px;
    }

    .node-list {
      max-height: none;
    }
  }

  .launcher.local-fixed-ui {
    overflow: hidden;
  }

  .launcher.local-fixed-ui .bar {
    padding-top: 10px;
    padding-bottom: 10px;
  }

  .launcher.local-fixed-ui .pose-btn {
    height: 28px;
    padding: 0 12px;
    font-size: 11px;
  }

  .launcher.local-fixed-ui .body {
    padding: 6px 8px 8px;
    gap: 6px;
    grid-template-columns: minmax(0, 1.12fr) minmax(320px, 0.88fr);
    overflow: hidden;
  }

  .launcher.local-fixed-ui .main-col,
  .launcher.local-fixed-ui .side-col {
    gap: 6px;
    overflow: hidden;
  }

  .launcher.local-fixed-ui .card-head,
  .launcher.local-fixed-ui .log-toolbar {
    padding: 5px 8px;
  }

  .launcher.local-fixed-ui .card-body {
    padding: 5px 7px;
  }

  .launcher.local-fixed-ui .sync-body {
    padding: 6px 8px;
  }

  .launcher.local-fixed-ui .sync-diff {
    font-size: 13px;
  }

  .launcher.local-fixed-ui .sync-meta,
  .launcher.local-fixed-ui .node-desc,
  .launcher.local-fixed-ui .mission-empty,
  .launcher.local-fixed-ui .log-status,
  .launcher.local-fixed-ui .log-placeholder {
    font-size: 11px;
  }

  .launcher.local-fixed-ui .node-row {
    padding: 5px 3px;
  }

  .launcher.local-fixed-ui .node-name,
  .launcher.local-fixed-ui .log-close,
  .launcher.local-fixed-ui .log-save {
    font-size: 11px;
  }

  .launcher.local-fixed-ui .note {
    padding: 6px 24px 6px 8px;
    font-size: 11px;
  }

  .launcher.local-fixed-ui .note pre {
    max-height: 84px;
    font-size: 11px;
  }

  .launcher.local-fixed-ui .mission-tabs {
    gap: 4px;
    padding: 5px 7px 0;
  }

  .launcher.local-fixed-ui .mission-tab {
    min-height: 22px;
    padding: 0 7px;
    font-size: 10px;
  }

  .launcher.local-fixed-ui .list {
    gap: 4px;
  }

  .launcher.local-fixed-ui .compact-list {
    gap: 3px;
  }

  .launcher.local-fixed-ui .mission-card {
    flex: 1 1 0;
    min-height: 0;
  }

  .launcher.local-fixed-ui .log-console,
  .launcher.local-fixed-ui .log-grid,
  .launcher.local-fixed-ui .log-placeholder {
    min-height: 150px;
  }

  .launcher.local-fixed-ui .log-grid {
    grid-auto-rows: minmax(100px, 1fr);
  }

  .launcher.local-fixed-ui .node-list {
    max-height: 132px;
  }
</style>
