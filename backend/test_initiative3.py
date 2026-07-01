import pytest
import os
import json
from unittest.mock import patch, MagicMock

from app.schemas import Task, Workspace
from app.services.builder_intelligence import builder_intelligence
from app.services.builder_service import builder_service

class MockTask:
    def __init__(self, metadata=None):
        self.title = "Create Button Component"
        self.description = "Build a reusable Button component."
        self.engineering_metadata = metadata or {}
        self.acceptance_criteria = ["Must be clickable"]


def test_context_retrieval_with_metadata(tmp_path):
    # Setup mock workspace files
    workspace_path = str(tmp_path)
    os.makedirs(os.path.join(workspace_path, "src", "components"))
    
    file_path = os.path.join(workspace_path, "src", "components", "Card.jsx")
    with open(file_path, "w") as f:
        f.write("export const Card = () => <div>Card</div>;")
        
    metadata = {
        "expected_files": {
            "read": ["src/components/Card.jsx"]
        }
    }
    task = MockTask(metadata)
    
    context = builder_intelligence.retrieve_context(task, workspace_path)
    
    assert "RELEVANT EXISTING FILES:" in context
    assert "src/components/Card.jsx" in context
    assert "export const Card" in context


def test_context_retrieval_fallback(tmp_path):
    # No metadata
    task = MockTask()
    workspace_path = str(tmp_path)
    
    context = builder_intelligence.retrieve_context(task, workspace_path)
    
    assert "EXISTING STRUCTURE:" in context
    assert "RELEVANT EXISTING FILES:" not in context


def test_prompt_assembly():
    task = MockTask({
        "engineering_standards": ["Use functional components"],
        "required_deliverables": ["src/components/Button.jsx"]
    })
    
    class MockWorkspace:
        name = "Test Project"
        
    prompt = builder_intelligence.assemble_prompt(
        task=task,
        workspace=MockWorkspace(),
        architecture={"tech_stack": ["React"]},
        spec={"frontend": "React", "theme_context": {"color_palette": "Blue"}},
        retrieved_context="Mock Context"
    )
    
    assert "Test Project" in prompt
    assert "Use functional components" in prompt
    assert "src/components/Button.jsx" in prompt
    assert "Must be clickable" in prompt
    assert "Mock Context" in prompt


def test_validation_missing_deliverable():
    # Setup test to ensure _validate_build_output catches missing deliverables
    task = MockTask({
        "required_deliverables": ["Button.jsx"]
    })
    
    # We output "Card.jsx", so "Button.jsx" is missing
    output_files = ["/fake/path/Card.jsx"]
    
    errors = builder_service._validate_build_output("/fake/path", output_files, task)
    assert any("Missing required deliverable" in e for e in errors)


def test_validation_empty_file(tmp_path):
    # Create an empty file
    file_path = os.path.join(str(tmp_path), "Empty.jsx")
    open(file_path, "w").close()
    
    errors = builder_service._validate_build_output(str(tmp_path), [file_path], MockTask())
    assert len(errors) == 1
    assert "Empty file: Empty.jsx" in errors[0]
