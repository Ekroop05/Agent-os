import traceback
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import ArchitectApprovalRequest
from app.state.project_state import project_state_manager

client = TestClient(app)

# 1. Create a dummy state in the project_state_manager
state = project_state_manager.get_or_create("test_conv_123")
state["architecture_generated"] = True
state["architecture"] = {
    "project_name": "TestProject",
    "architecture": "Test arch",
    "task_breakdown": [
        {"title": "Build frontend shell", "description": "...", "priority": "High"}
    ]
}
state["spec"] = {
    "project_name": "TestProject",
    "theme": "Technology",
    "required_features": []
}

# 2. Call the endpoint
try:
    response = client.post("/architect/approve", json={"conversation_id": "test_conv_123"})
    print("STATUS:", response.status_code)
    import json
    with open("approve_response.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f, indent=2)
    print("Saved response to approve_response.json")
except Exception as e:
    print("EXCEPTION CAUGHT!")
    traceback.print_exc()
