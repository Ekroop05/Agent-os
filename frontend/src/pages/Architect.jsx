import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { architectStore } from "../services/architectStore";

export default function Architect({ data, setData }) {
  const [, forceRender] = useState({});
  const [draft, setDraft] = useState("");
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    const unsub = architectStore.subscribe(() => forceRender({}));
    if (sessionStorage.getItem("agentos.architect.focus") === "true") {
      sessionStorage.removeItem("agentos.architect.focus");
      architectStore.reset();
    }
    inputRef.current?.focus();
    return unsub;
  }, []);

  const { conversationId, messages, status, isTyping, isApproving, approvalPhase, error } = architectStore;

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    if (!isApproving || !data || !data.activity) return;
    const lastActivity = data.activity[0];
    if (lastActivity) {
      if (lastActivity.event_type === "WORKSPACE_CREATED") {
        architectStore.setApprovalPhase("Generating Task Graph...");
      } else if (lastActivity.event_type === "TASK_CREATED") {
        architectStore.setApprovalPhase("Creating Tasks...");
      } else if (lastActivity.event_type === "BUILD_STARTED") {
        architectStore.setApprovalPhase("Starting Build...");
      }
    }
  }, [data?.activity, isApproving]);

  function sendMessage(event) {
    event.preventDefault();
    if (!draft.trim() || isTyping || isApproving) return;
    const msg = draft;
    setDraft("");
    architectStore.sendMessage(msg);
  }

  function approveProject() {
    architectStore.approveProject(setData);
  }

  function startNewConversation() {
    architectStore.reset();
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
            ref={inputRef}
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
            disabled={!status.approval_required || status.approved || isApproving}
            onClick={approveProject}
          >
            {status.approved ? "✓ Project Approved" : isApproving ? approvalPhase : "Approve Project"}
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
