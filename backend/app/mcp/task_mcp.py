from typing import Dict, Any, List

from app.core.event_bus import event_bus
from app.mcp.registry import register_tool
from app.schemas import Event, TaskCreate, TaskUpdate
from app.services.task_service import task_service

@register_tool("task", "create_task")
async def create_task(title: str, description: str, priority: str = "Medium", assigned_agent: str = "Unassigned") -> Dict[str, Any]:
    payload = TaskCreate(
        title=title,
        description=description,
        assigned_agent=assigned_agent,
        priority=priority
    )
    task = task_service.create(payload)
    await event_bus.publish(
        Event(type="TASK_CREATED", source=task.assigned_agent, message=f"Task created via MCP: {task.title}", payload=task.model_dump())
    )
    return task.model_dump()

@register_tool("task", "update_task")
async def update_task(task_id: str, **changes) -> Dict[str, Any]:
    payload = TaskUpdate(id=task_id, **changes)
    task = task_service.update(payload)
    event_type = "TASK_COMPLETED" if task.status == "Completed" else "TASK_STARTED"
    await event_bus.publish(
        Event(type=event_type, source=task.assigned_agent, message=f"Task updated via MCP: {task.title}", payload=task.model_dump())
    )
    return task.model_dump()

@register_tool("task", "assign_task")
async def assign_task(task_id: str, agent_name: str) -> Dict[str, Any]:
    return await update_task(task_id, assigned_agent=agent_name)

@register_tool("task", "complete_task")
async def complete_task(task_id: str) -> Dict[str, Any]:
    return await update_task(task_id, status="Completed")

@register_tool("task", "list_tasks")
def list_tasks() -> List[Dict[str, Any]]:
    tasks = task_service.list()
    return [t.model_dump() for t in tasks]

@register_tool("task", "get_task")
def get_task(task_id: str) -> Dict[str, Any]:
    task = task_service.get(task_id)
    return task.model_dump()
