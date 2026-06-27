import { api } from "./api";

function upsertById(list, item) {
  const filtered = (list || []).filter((i) => i.id !== item.id);
  return [item, ...filtered];
}

function mergeMany(list, items) {
  const existingIds = new Set((list || []).map((i) => i.id));
  const newItems = (items || []).filter((i) => !existingIds.has(i.id));
  return [...newItems, ...(list || [])];
}

const initialMessages = [
  {
    role: "architect",
    content:
      "Hey there — I'm the Architect. Think of me as your technical co-founder.\n\nTell me what you want to build, and I'll shape it into a real architecture with tasks, tech stack, and a development plan.\n\nWhat's the idea?",
  },
];

class ArchitectStore {
  constructor() {
    this.conversationId = sessionStorage.getItem("agentos.architect.conversationId") || "";
    const savedMsg = sessionStorage.getItem("agentos.architect.messages");
    this.messages = savedMsg ? JSON.parse(savedMsg) : initialMessages;
    const savedStatus = sessionStorage.getItem("agentos.architect.status");
    this.status = savedStatus ? JSON.parse(savedStatus) : {};
    this.isTyping = false;
    this.isApproving = false;
    this.approvalPhase = "";
    this.error = "";
    this.listeners = new Set();
  }

  subscribe(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  notify() {
    sessionStorage.setItem("agentos.architect.messages", JSON.stringify(this.messages));
    sessionStorage.setItem("agentos.architect.status", JSON.stringify(this.status));
    if (this.conversationId) {
      sessionStorage.setItem("agentos.architect.conversationId", this.conversationId);
    }
    this.listeners.forEach((fn) => fn());
  }

  reset() {
    sessionStorage.removeItem("agentos.architect.conversationId");
    sessionStorage.removeItem("agentos.architect.messages");
    sessionStorage.removeItem("agentos.architect.status");
    this.conversationId = "";
    this.messages = initialMessages;
    this.status = {};
    this.isTyping = false;
    this.isApproving = false;
    this.approvalPhase = "";
    this.error = "";
    this.notify();
  }

  async sendMessage(draft) {
    const message = draft.trim();
    if (!message || this.isTyping || this.isApproving) return;

    this.error = "";
    this.messages = [...this.messages, { role: "user", content: message }];
    this.isTyping = true;
    this.notify();

    try {
      const response = await api.architectChat(message, this.conversationId || undefined);
      this.conversationId = response.conversation_id;
      this.status = response;
      this.messages = [...this.messages, { role: "architect", content: response.reply }];
    } catch (requestError) {
      this.error = requestError.message;
    } finally {
      this.isTyping = false;
      this.notify();
    }
  }

  async approveProject(setData) {
    api.logTrace("BUTTON_CLICKED");
    api.logTrace("API_REQUEST_SENT");
    this.isApproving = true;
    this.approvalPhase = "Approving Project...";
    this.error = "";
    this.notify();

    try {
      const response = await api.approveArchitecture(this.conversationId);
      api.logTrace("API_RESPONSE_RECEIVED");
      this.status = {
        ...this.status,
        approved: true,
        approval_required: false,
        current_phase: "Project Ready",
        confidence_score: 100,
      };
      this.messages = [
        ...this.messages,
        {
          role: "architect",
          content: `Approved! Workspace **"${response.workspace.name}"** has been created with ${response.tasks.length} planning tasks.\n\nYou can now head to the Workspaces and Tasks pages to see everything. Let's build something great.`,
        },
      ];
      if (setData) {
        setData((current) => ({
          ...current,
          workspaces: upsertById(current.workspaces, response.workspace),
          tasks: mergeMany(current.tasks, response.tasks),
          sandbox: current.sandbox
            ? {
                ...current.sandbox,
                workspace_mappings: upsertById(current.sandbox.workspace_mappings, {
                  workspace_id: response.workspace.id,
                  id: response.workspace.id,
                  name: response.workspace.name,
                  path: response.workspace.path,
                }),
              }
            : current.sandbox,
        }));
      }
    } catch (requestError) {
      api.logTrace("API_RESPONSE_ERROR");
      this.error = requestError.message;
    } finally {
      this.isApproving = false;
      this.notify();
    }
  }

  setApprovalPhase(phase) {
    if (this.approvalPhase !== phase) {
      this.approvalPhase = phase;
      this.notify();
    }
  }
}

export const architectStore = new ArchitectStore();
