const defaultWsUrl = localStorage.getItem("agentos.wsUrl") || "ws://localhost:8000";

export function getWsUrl() {
  return localStorage.getItem("agentos.wsUrl") || defaultWsUrl;
}

export function connectChannel(channel, onMessage) {
  const url = `${getWsUrl()}/ws/${channel}`;
  const socket = new WebSocket(url);

  socket.addEventListener("open", () => {
    console.log(`[WS] Connected to ${channel}`);
  });

  socket.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (parseError) {
      console.warn(`[WS] Failed to parse message on ${channel}:`, parseError, event.data);
    }
  });

  socket.addEventListener("error", (event) => {
    console.error(`[WS] Error on ${channel}:`, event);
  });

  socket.addEventListener("close", (event) => {
    console.log(`[WS] Disconnected from ${channel} (code=${event.code}, reason=${event.reason})`);
  });

  return socket;
}
