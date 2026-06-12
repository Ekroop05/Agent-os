import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";

const initialMessages = [
  {
    role: "architect",
    content:
      "Hey there — I'm the Architect. Think of me as your technical co-founder.\n\nTell me what you want to build, and I'll shape it into a real architecture with tasks, tech stack, and a development plan.\n\nWhat's the idea?",
  },
];

export default function Architect({ setData }) {
  const [conversationId, setConversationId] = useState(() =>
    sessionStorage.getItem("agentos.architect.conversationId") || ""
  );
  const [messages, setMessages] = useState(() => {
    const saved = sessionStorage.getItem("agentos.architect.messages");
    return saved ? JSON.parse(saved) : initialMessages;
  });
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState(() => {
    const saved = sessionStorage.getItem("agentos.architect.status");
    return saved ? JSON.parse(saved) : {};
  });
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    sessionStorage.setItem("agentos.architect.messages", JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    sessionStorage.setItem("agentos.architect.status", JSON.stringify(status));
  }, [status]);

  useEffect(() => {
    if (conversationId) {
      sessionStorage.setItem("agentos.architect.conversationId", conversationId);
    }
  }, [conversationId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  async function sendMessage(event) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || isTyping) return;

    setDraft("");
    setError("");
    setMessages((current) => [...current, { role: "user", content: message }]);
    setIsTyping(true);

    try {
      const response = await api.architectChat(message, conversationId || undefined);
      setConversationId(response.conversation_id);
      setStatus(response);
      setMessages((current) => [...current, { role: "architect", content: response.reply }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsTyping(false);
    }
  }

  async function approveProject() {
    setError("");
    try {
      const response = await api.approveArchitecture(conversationId);
      setStatus((current) => ({
        ...current,
        approved: true,
        approval_required: false,
        current_phase: "Project Ready",
        confidence_score: 100,
      }));
      setMessages((current) => [
        ...current,
        {
          role: "architect",
          content: `Approved! Workspace **"${response.workspace.name}"** has been created with ${response.tasks.length} planning tasks.\n\nYou can now head to the Workspaces and Tasks pages to see everything. Let's build something great.`,
        },
      ]);
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
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function startNewConversation() {
    sessionStorage.removeItem("agentos.architect.conversationId");
    sessionStorage.removeItem("agentos.architect.messages");
    sessionStorage.removeItem("agentos.architect.status");
    setConversationId("");
    setMessages(initialMessages);
    setStatus({});
    setError("");
  }

  const architecture = status.architecture;
  const phase = status.current_phase || "Discovering Requirements";
  const progress = status.requirements_progress || 0;
  const confidence = status.confidence_score || 0;

  return (
    <div className="architect-page">
      <section className="chat-panel">
        <div className="chat-history">
          {messages.map((message, index) => (
            <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
              <span>{message.role === "user" ? "You" : "Architect"}</span>
              <p>{message.content}</p>
            </article>
          ))}
          {isTyping && (
            <article className="chat-message architect typing">
              <span>Architect</span>
              <p>Thinking…</p>
            </article>
          )}
          <div ref={scrollRef} />
        </div>

        {error && <div className="system-alert">{error}</div>}

        <form className="chat-composer" onSubmit={sendMessage}>
          <textarea
            aria-label="Message Architect"
            placeholder="Describe your project or answer the Architect's questions…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage(event);
              }
            }}
          />
          <button type="submit" disabled={isTyping}>Send</button>
        </form>
      </section>

      <aside className="project-state-panel">
        <div className="section-heading">
          <h2>Project State</h2>
          <span className={`phase-badge phase-${phaseClass(phase)}`}>{phase}</span>
        </div>

        <StateRow label="Project Name" value={status.project_name || "Pending…"} />
        <StateRow label="Current Phase" value={phase} />

        <div className="state-row">
          <span>Requirements</span>
          <div className="progress-bar-container">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }}>
              <span className="progress-label">{progress}%</span>
            </div>
          </div>
        </div>

        <div className="state-row">
          <span>Confidence</span>
          <div className="progress-bar-container confidence-bar">
            <div
              className={`progress-bar-fill ${confidence >= 75 ? "high" : confidence >= 40 ? "medium" : "low"}`}
              style={{ width: `${confidence}%` }}
            >
              <span className="progress-label">{confidence}%</span>
            </div>
          </div>
        </div>

        <StateRow label="Architecture" value={architecture ? "Generated ✓" : "Not yet generated"} />
        <StateRow
          label="Approval"
          value={status.approved ? "Approved ✓" : status.approval_required ? "Ready — Awaiting Your Approval" : "Not ready"}
        />

        {architecture && (
          <div className="architecture-summary">
            <h3>{architecture.project_name}</h3>
            <p>{architecture.architecture}</p>
            <h4>Tech Stack</h4>
            <ul>{toList(architecture.tech_stack).map((item) => <li key={item}>{item}</li>)}</ul>
            <h4>Components</h4>
            <ul>{toList(architecture.major_components).map((item) => <li key={item}>{item}</li>)}</ul>
            <h4>Task Breakdown ({toList(architecture.task_breakdown).length} tasks)</h4>
            <ul>{toList(architecture.task_breakdown).map((item) => <li key={item.title || item}>{item.title || item}</li>)}</ul>
          </div>
        )}

        <div className="architect-actions">
          <button
            className="approve-button"
            type="button"
            disabled={!status.approval_required || status.approved}
            onClick={approveProject}
          >
            {status.approved ? "✓ Project Approved" : "Approve Project"}
          </button>

          <button
            className="new-conversation-btn"
            type="button"
            onClick={startNewConversation}
          >
            New Conversation
          </button>
        </div>
      </aside>
    </div>
  );
}

function StateRow({ label, value }) {
  return (
    <div className="state-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function phaseClass(phase) {
  if (!phase) return "discovering";
  return phase.toLowerCase().replace(/\s+/g, "-");
}

function toList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function upsertById(items, item) {
  const itemId = item.id || item.workspace_id;
  return items.some((current) => (current.id || current.workspace_id) === itemId)
    ? items.map((current) => ((current.id || current.workspace_id) === itemId ? item : current))
    : [item, ...items];
}

function mergeMany(items, nextItems) {
  return nextItems.reduce((merged, item) => upsertById(merged, item), items);
}
