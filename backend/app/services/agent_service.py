from __future__ import annotations

from fastapi import HTTPException

from app.schemas import Agent, AgentCreate


class AgentService:
    def __init__(self):
        self.agents: dict[str, Agent] = {
            "head-agent": Agent(
                id="head-agent",
                name="Head Agent",
                role="Planner and orchestrator",
                status="Running",
                model="Qwen3 14B",
                current_task="Decomposing workspace generation pipeline",
                uptime="04:18:22",
                memory_usage=71,
            ),
            "builder-agent": Agent(
                id="builder-agent",
                name="Builder Agent",
                role="Code generation worker",
                status="Paused",
                model="Qwen2.5-Coder 7B",
                current_task="Waiting for implementation ticket",
                uptime="02:41:09",
                memory_usage=48,
            ),
            "security-agent": Agent(
                id="security-agent",
                name="Security Agent",
                role="Security and review worker",
                status="Idle",
                model="Qwen2.5-Coder 7B",
                current_task="Monitoring review queue",
                uptime="01:17:46",
                memory_usage=29,
            ),
        }

    def list(self) -> list[Agent]:
        return list(self.agents.values())

    def get(self, agent_id: str) -> Agent:
        agent = self.agents.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    def create(self, payload: AgentCreate) -> Agent:
        agent_id = payload.name.lower().replace(" ", "-")
        agent = Agent(
            id=agent_id,
            name=payload.name,
            role=payload.role,
            status="Idle",
            model=payload.model,
            current_task=payload.current_task,
            uptime="00:00:00",
            memory_usage=0,
        )
        self.agents[agent_id] = agent
        return agent

    def update(self, agent_id: str, **changes) -> Agent:
        agent = self.get(agent_id)
        updated = agent.model_copy(update={key: value for key, value in changes.items() if value is not None})
        self.agents[agent_id] = updated
        return updated

    def delete(self, agent_id: str) -> None:
        self.get(agent_id)
        del self.agents[agent_id]


agent_service = AgentService()
