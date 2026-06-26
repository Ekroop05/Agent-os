const defaultApiUrl = localStorage.getItem("agentos.apiUrl") || "http://127.0.0.1:8000";

export function getApiUrl() {
  return localStorage.getItem("agentos.apiUrl") || defaultApiUrl;
}

async function request(path, options) {
  const response = await fetch(`${getApiUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = `Request failed: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail);
      }
    } catch (e) {
      // Ignore JSON parse error, use default message
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  // Agents
  getAgents: () => request("/agents"),
  getAgent: (agentId) => request(`/agents/${agentId}`),
  startAgent: (agentId) =>
    request("/agents/start", { method: "POST", body: JSON.stringify({ agent_id: agentId }) }),
  stopAgent: (agentId) =>
    request("/agents/stop", { method: "POST", body: JSON.stringify({ agent_id: agentId }) }),
  pauseAgent: (agentId) =>
    request("/agents/pause", { method: "POST", body: JSON.stringify({ agent_id: agentId }) }),
  restartAgent: (agentId) =>
    request("/agents/restart", { method: "POST", body: JSON.stringify({ agent_id: agentId }) }),

  // Tasks
  getTasks: () => request("/tasks"),
  getTask: (taskId) => request(`/tasks/${taskId}`),
  createTask: (task) =>
    request("/tasks/create", { method: "POST", body: JSON.stringify(task) }),
  updateTask: (task) =>
    request("/tasks/update", { method: "PATCH", body: JSON.stringify(task) }),

  // Workspaces
  getWorkspaces: () => request("/workspaces"),
  getWorkspace: (workspaceId) => request(`/workspaces/${workspaceId}`),
  getWorkspaceArchive: () => request("/workspaces/archive"),
  createWorkspace: (workspace) =>
    request("/workspaces/create", { method: "POST", body: JSON.stringify(workspace) }),
  deleteWorkspace: (workspaceId) =>
    request(`/workspaces/${workspaceId}`, { method: "DELETE" }),

  // Activity
  getActivity: () => request("/activity"),

  // Architect
  architectChat: (message, conversationId) =>
    request("/architect/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId }),
    }),
  approveArchitecture: (conversationId) =>
    request("/architect/approve", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId }),
    }),

  logTrace: (message) =>
    fetch(`${getApiUrl()}/log_trace`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }).catch(() => {}),

  // Sandbox
  getSandbox: () => request("/sandbox"),
  updateSandboxSettings: (projectRoot) =>
    request("/sandbox/settings", {
      method: "PATCH",
      body: JSON.stringify({ project_root: projectRoot }),
    }),

  // System
  getSystemStatus: () => request("/system/status"),

  // Build Pipeline
  startBuild: (workspaceId) =>
    request("/build/start", { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) }),
  getBuildProgress: (workspaceId) =>
    request(`/build/progress/${workspaceId}`),
  cancelBuild: (workspaceId) =>
    request(`/build/cancel/${workspaceId}`, { method: "POST" }),
  getBuildReport: (workspaceId) =>
    request(`/build/report/${workspaceId}`),

  // Logs
  getLogs: (workspaceId, agent) => {
    const params = new URLSearchParams();
    if (agent) params.set("agent", agent);
    const qs = params.toString();
    return request(`/logs/${workspaceId}${qs ? `?${qs}` : ""}`);
  },

  // Sprint 4.5: Jobs
  getJobs: () => request("/jobs"),
  getJob: (jobId) => request(`/jobs/${jobId}`),
  cancelJob: (jobId) =>
    request(`/jobs/${jobId}/cancel`, { method: "POST" }),

  // Sprint 4.5: Runtimes
  getRuntimes: () => request("/runtimes"),
  getRuntime: (workspaceId) => request(`/runtimes/${workspaceId}`),
  stopRuntime: (workspaceId) =>
    request("/runtimes/stop", {
      method: "POST",
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),

  // Sprint 4.5: Timeline
  getTimeline: (limit = 100) => request(`/timeline?limit=${limit}`),
  // ── Sprint 5: Project Editing & Snapshots ──────────────────────────────
  analyzeProject: async (projectPath) => {
    const res = await fetch(`${API_URL}/project/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_path: projectPath }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Analysis failed");
    }
    return res.json();
  },

  getProjectContext: async (workspaceId) => {
    const res = await fetch(`${API_URL}/project/context/${workspaceId}`);
    return res.json();
  },

  updateProjectContext: async (workspaceId, data) => {
    const res = await fetch(`${API_URL}/project/context/${workspaceId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  createSnapshot: async (workspaceId, workspacePath, label = "") => {
    const res = await fetch(`${API_URL}/snapshots/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, workspace_path: workspacePath, label }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Snapshot failed");
    }
    return res.json();
  },

  listSnapshots: async (workspaceId, workspacePath = "") => {
    const res = await fetch(`${API_URL}/snapshots/${workspaceId}?workspace_path=${encodeURIComponent(workspacePath)}`);
    return res.json();
  },

  restoreSnapshot: async (workspaceId, workspacePath, snapshotId) => {
    const res = await fetch(`${API_URL}/snapshots/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, workspace_path: workspacePath, snapshot_id: snapshotId }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Restore failed");
    }
    return res.json();
  },

  compareSnapshot: async (workspaceId, snapshotId, workspacePath = "") => {
    const res = await fetch(`${API_URL}/snapshots/compare/${workspaceId}/${snapshotId}?workspace_path=${encodeURIComponent(workspacePath)}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Compare failed");
    }
    return res.json();
  },
};
