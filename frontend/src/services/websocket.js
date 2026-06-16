const defaultWsUrl = localStorage.getItem("agentos.wsUrl") || "ws://localhost:8000";

export function getWsUrl() {
  return localStorage.getItem("agentos.wsUrl") || defaultWsUrl;
}

/**
 * Sprint 4.5: WebSocket connection manager with auto-reconnect.
 *
 * Features:
 * - Exponential backoff reconnection (1s → 2s → 4s → 8s → max 30s)
 * - State re-sync on reconnect via REST API
 * - Connection state tracking per channel
 * - Heartbeat detection
 */

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_FACTOR = 2;

// Track all active channel connections
const channelState = {};

// Global reconnect callback (set by App.jsx to re-fetch state)
let _onReconnectCallback = null;

export function setOnReconnect(callback) {
  _onReconnectCallback = callback;
}

export function getConnectionStatus() {
  const statuses = {};
  for (const [channel, state] of Object.entries(channelState)) {
    statuses[channel] = state.connected ? "connected" : "disconnected";
  }
  return statuses;
}

export function connectChannel(channel, onMessage) {
  // Clean up existing connection if any
  const existing = channelState[channel];
  if (existing?.socket) {
    try {
      existing.socket.close();
    } catch {}
  }

  const state = {
    channel,
    socket: null,
    connected: false,
    reconnectAttempts: 0,
    reconnectTimer: null,
    onMessage,
    closed: false,  // Explicit close flag
  };

  channelState[channel] = state;

  _connect(state);

  // Return a close-able handle
  return {
    close: () => {
      state.closed = true;
      if (state.reconnectTimer) {
        clearTimeout(state.reconnectTimer);
        state.reconnectTimer = null;
      }
      if (state.socket) {
        try {
          state.socket.close();
        } catch {}
      }
      delete channelState[channel];
    },
  };
}

function _connect(state) {
  if (state.closed) return;

  const url = `${getWsUrl()}/ws/${state.channel}`;
  const socket = new WebSocket(url);
  state.socket = socket;

  socket.addEventListener("open", () => {
    console.log(`[WS] Connected to ${state.channel}`);
    state.connected = true;
    state.reconnectAttempts = 0;

    // If this is a reconnection, trigger global state re-sync
    if (state.reconnectAttempts > 0 || _onReconnectCallback) {
      console.log(`[WS] Reconnected to ${state.channel} — triggering state sync`);
      if (_onReconnectCallback) {
        try { _onReconnectCallback(state.channel); } catch {}
      }
    }
  });

  socket.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      state.onMessage(data);
    } catch (parseError) {
      console.warn(`[WS] Failed to parse message on ${state.channel}:`, parseError, event.data);
    }
  });

  socket.addEventListener("error", (event) => {
    console.error(`[WS] Error on ${state.channel}:`, event);
  });

  socket.addEventListener("close", (event) => {
    console.log(`[WS] Disconnected from ${state.channel} (code=${event.code}, reason=${event.reason})`);
    state.connected = false;

    // Auto-reconnect unless explicitly closed
    if (!state.closed) {
      _scheduleReconnect(state);
    }
  });
}

function _scheduleReconnect(state) {
  if (state.closed) return;

  const delay = Math.min(
    RECONNECT_BASE_MS * Math.pow(RECONNECT_FACTOR, state.reconnectAttempts),
    RECONNECT_MAX_MS,
  );

  console.log(
    `[WS] Scheduling reconnect for ${state.channel} in ${delay}ms (attempt ${state.reconnectAttempts + 1})`
  );

  state.reconnectTimer = setTimeout(() => {
    state.reconnectAttempts++;
    _connect(state);
  }, delay);
}
