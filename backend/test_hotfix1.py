import pytest
import json
from unittest.mock import patch

from app.extractors.requirement_extractor import requirement_extractor
from app.services.architect_service import architect_service

def test_edge_cases_no_false_positives():
    state = {}
    # Edge case 1: "application" should not match "cat" (Pets / Animals)
    updates = requirement_extractor.extract("I want to build a saas application.", state)
    assert updates.get("theme") is None
    
    # Edge case 2: "category" should not match "cat" (Pets / Animals)
    updates = requirement_extractor.extract("A system to sort by category.", state)
    assert updates.get("theme") is None

    # Edge case 3: "competitor" should not match "pet" (Pets / Animals)
    updates = requirement_extractor.extract("A competitor analysis tool.", state)
    assert updates.get("theme") is None

    # Edge case 4: "communicate" should not match "cat" (Pets / Animals)
    updates = requirement_extractor.extract("An app to communicate with friends.", state)
    assert updates.get("theme") is None

    # Edge case 5: "catalog" should not match "cat" (Pets / Animals)
    updates = requirement_extractor.extract("A product catalog.", state)
    assert updates.get("theme") is None

    # Edge case 6: "pedagogical" should not match "dog" (Pets / Animals)
    updates = requirement_extractor.extract("A pedagogical tool for students.", state)
    assert updates.get("theme") is None


def test_regression_coffee_shop():
    updates = requirement_extractor.extract("I want a website for my local coffee shop.", {})
    assert updates.get("project_type") == "Website"

def test_regression_netflix():
    updates = requirement_extractor.extract("A movie streaming platform like netflix where you watch videos.", {})
    assert updates.get("project_type") == "Platform"
    assert "Video / Streaming" in updates.get("core_features", [])

def test_regression_hospital():
    updates = requirement_extractor.extract("A medical portal for a hospital with patient login.", {})
    assert updates.get("project_type") == "Portal"
    assert updates.get("theme") == "Healthcare"
    assert updates.get("target_users") == "Healthcare Users"
    assert updates.get("authentication") is True

def test_regression_bank():
    updates = requirement_extractor.extract("A banking dashboard for finance.", {})
    assert updates.get("project_type") == "Dashboard"
    assert updates.get("theme") == "Finance"

def test_regression_crm():
    updates = requirement_extractor.extract("A CRM system to manage clients.", {})
    assert updates.get("project_type") == "CRM System"
    assert updates.get("purpose") == "Management"
    assert updates.get("target_users") == "Clients"

def test_regression_inventory_system():
    updates = requirement_extractor.extract("An inventory management system.", {})
    assert updates.get("project_type") is None # 'system' alone does not map to a project type
    assert updates.get("purpose") == "Management"

def test_regression_portfolio():
    updates = requirement_extractor.extract("My personal portfolio website to showcase my art.", {})
    assert updates.get("project_type") == "Portfolio Website"
    assert updates.get("purpose") == "Personal Showcase"
    assert updates.get("theme") == "Art / Gallery"

def test_regression_flowdesk_ai():
    # The original problematic prompt
    prompt = "I want to build a modern AI-native project management platform called FlowDesk AI. The goal is to create a premium SaaS application that helps teams manage projects, tasks, documents, and AI-assisted workflows."
    updates = requirement_extractor.extract(prompt, {})
    
    assert updates.get("project_name") == "Flowdesk Ai"
    assert updates.get("project_type") == "Web Application" # SaaS -> Web App via inference or map
    assert updates.get("theme") is None # Should NOT be Pets / Animals anymore!
    assert updates.get("purpose") == "Management"

def test_regression_weather_app():
    updates = requirement_extractor.extract("A mobile app for weather.", {})
    assert updates.get("project_type") == "Mobile Application"

def test_regression_gaming_platform():
    updates = requirement_extractor.extract("An esports gaming platform for players.", {})
    assert updates.get("project_type") == "Platform"
    assert updates.get("theme") == "Gaming / Esports"
    assert updates.get("target_users") == "Gamers"


@patch("app.services.architect_service.generate_response")
def test_architect_service_fallback_retry(mock_generate_response):
    # Mock LLM to always throw an exception to test retry and fallback
    import requests
    mock_generate_response.side_effect = requests.exceptions.Timeout("API timed out")
    
    from app.state.project_state import project_state_manager
    state = project_state_manager.get_or_create("test-123")
    state.update({
        "project_type": "Web Application",
        "purpose": "Management",
        "requirements_progress": 0,
        "current_phase": "REQUIREMENT_DISCOVERY"
    })
    
    # This should trigger retries and then call the fallback
    reply = architect_service._conversational_reply(state)
    
    # Since LLM_RETRY_COUNT = 2, it should attempt 3 times (1 initial + 2 retries)
    assert mock_generate_response.call_count == 3
    
    # Fallback response should be used
    assert "I couldn't confidently determine every project detail automatically." in reply
    assert "Let's clarify a few things before continuing." in reply

@patch("app.services.architect_service.generate_response")
def test_architect_service_architecture_fallback(mock_generate_response):
    # Mock LLM to throw exception
    import requests
    mock_generate_response.side_effect = requests.exceptions.ConnectionError("Connection Failed")
    
    from app.state.project_state import project_state_manager
    state = project_state_manager.get_or_create("test-124")
    state.update({
        "project_name": "Test Project",
        "project_type": "Web Application",
        "theme": "Technology"
    })
    
    arch = architect_service._generate_architecture(state)
    assert mock_generate_response.call_count == 3
    
    assert arch.get("project_name") == "Test Project"
    assert len(arch.get("task_breakdown")) > 0
    assert "Frontend Application Shell" in arch.get("major_components", [])
