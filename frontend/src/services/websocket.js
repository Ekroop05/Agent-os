const defaultWsUrl = localStorage.getItem("agentos.wsUrl") || "ws://localhost:8000";

export function getWsUrl() {
  return localStorage.getItem("agentos.wsUrl") || defaultWsUrl;
}

export function connectChannel(channel, onMessage) {
  const socket = new WebSocket(`${getWsUrl()}/ws/${channel}`);

  socket.addEventListener("message", (event) => {
    onMessage(JSON.parse(event.data));
  });

  return socket;
}
