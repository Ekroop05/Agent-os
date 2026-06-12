class PlannerAgent:
    def plan(self, goal: str) -> list[str]:
        return [
            f"Understand goal: {goal}",
            "Break work into tasks",
            "Assign tasks to available agents",
        ]
