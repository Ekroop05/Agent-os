from typing import Any, Callable, Dict

class MCPRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.namespaces: Dict[str, list[str]] = {}

    def register(self, namespace: str, name: str, func: Callable):
        tool_id = f"{namespace}:{name}"
        self.tools[tool_id] = func
        if namespace not in self.namespaces:
            self.namespaces[namespace] = []
        self.namespaces[namespace].append(tool_id)

    async def execute(self, agent_role: str, namespace: str, tool_name: str, params: dict) -> dict:
        tool_id = f"{namespace}:{tool_name}"
        
        if tool_id not in self.tools:
            return {"error": f"Tool {tool_id} not found."}

        # Check permissions
        if not self._check_permission(agent_role, namespace, tool_name):
            return {"error": f"Agent with role '{agent_role}' is not permitted to use {tool_id}."}

        try:
            import asyncio
            func = self.tools[tool_id]
            if asyncio.iscoroutinefunction(func):
                result = await func(**params)
            else:
                result = func(**params)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_permission(self, role: str, namespace: str, tool_name: str) -> bool:
        if role == "Head Agent":
            return namespace in ["project", "task"]
        elif role == "Builder Agent":
            if namespace == "project":
                return tool_name in ["list_projects", "get_project", "get_project_path"]
            return namespace in ["file", "terminal", "task"]
        elif role == "Security Agent":
            if namespace == "project":
                return tool_name in ["list_projects", "get_project", "get_project_path"]
            if namespace == "terminal":
                # Audit commands only (assuming git status, git log might fall under git, 
                # but maybe things like npm audit if we map it)
                # Currently only Git MCP is allowed, not Terminal MCP generally for Security.
                return False 
            return namespace in ["file", "task", "git"]
        return False

mcp_registry = MCPRegistry()

def register_tool(namespace: str, name: str):
    def decorator(func: Callable):
        mcp_registry.register(namespace, name, func)
        return func
    return decorator
