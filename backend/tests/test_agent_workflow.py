#!/usr/bin/env python
"""
Test script for Warder agent workflow:
1. Create a user
2. Login to get an auth token
3. Use the token to create an agent
4. Send a chat message to that agent
"""

import requests
import json
import time
import uuid
import os
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000/api"
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "Password123",
    "first_name": "Test",
    "last_name": "User",
}


def print_separator(title: str) -> None:
    """Print a separator with a title."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    files: Optional[Dict[str, Any]] = None,
    allow_redirects: bool = True,
) -> requests.Response:
    """Make a request to the API."""
    url = f"{BASE_URL}/{endpoint}"

    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)

    if method.lower() == "get":
        response = requests.get(
            url, headers=default_headers, allow_redirects=allow_redirects
        )
    elif method.lower() == "post":
        if files:
            # Don't include Content-Type for multipart/form-data
            if "Content-Type" in default_headers:
                del default_headers["Content-Type"]
            response = requests.post(
                url,
                headers=default_headers,
                data=data,
                files=files,
                allow_redirects=allow_redirects,
            )
        else:
            response = requests.post(
                url,
                headers=default_headers,
                data=json.dumps(data) if data else None,
                allow_redirects=allow_redirects,
            )
    elif method.lower() == "put":
        response = requests.put(
            url,
            headers=default_headers,
            data=json.dumps(data) if data else None,
            allow_redirects=allow_redirects,
        )
    elif method.lower() == "delete":
        response = requests.delete(
            url, headers=default_headers, allow_redirects=allow_redirects
        )
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response


def create_user() -> bool:
    """Create a test user."""
    print_separator("Creating User")

    # Check if user already exists
    response = make_request(
        "post",
        "auth/login",
        {"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )

    if response.status_code == 200:
        print("User already exists, skipping creation")
        return True

    # Create user
    response = make_request("post", "auth/register", TEST_USER)

    if response.status_code == 201:
        print(f"User created successfully: {response.json()}")
        return True
    else:
        print(f"Failed to create user: {response.status_code} - {response.text}")
        return False


def login() -> Optional[str]:
    """Login and get access token."""
    print_separator("Logging In")

    # For login endpoint, we need to use form data
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        print(f"Login successful, got access token")
        return access_token
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None


def get_user_id(access_token: str) -> Optional[str]:
    """Get the user ID from the /me endpoint."""
    print_separator("Getting User ID")

    headers = {"Authorization": f"Bearer {access_token}"}
    response = make_request("get", "users/me", headers=headers)

    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data.get("id")
        print(f"Got user ID: {user_id}")
        return user_id
    else:
        print(f"Failed to get user ID: {response.status_code} - {response.text}")
        return None


def create_agent(access_token: str, user_id: str) -> Optional[str]:
    """Create a new agent."""
    print_separator("Creating Agent")

    agent_data = {
        "name": f"Test Agent {uuid.uuid4().hex[:8]}",
        "description": "A test agent for RAG functionality",
        "type": "rag",
        "user_id": user_id,
        "knowledge_base": {
            "type": "vector",
            "config": {"collection_name": f"test_collection_{uuid.uuid4().hex[:8]}"},
        },
    }

    headers = {"Authorization": f"Bearer {access_token}"}
    # First try without following redirects
    response = make_request(
        "post", "agents", agent_data, headers, allow_redirects=False
    )

    # Handle redirect manually if needed
    if response.status_code == 307:
        redirect_url = response.headers.get("Location")
        print(f"Following redirect to: {redirect_url}")
        if redirect_url:
            # Extract the endpoint from the full URL
            if redirect_url.startswith(BASE_URL):
                redirect_endpoint = redirect_url[len(BASE_URL):].lstrip("/")
            else:
                redirect_endpoint = redirect_url

            # Make a new request to the redirect URL
            response = make_request("post", redirect_endpoint, agent_data, headers)

    if response.status_code == 201:
        agent_data = response.json()
        agent_id = agent_data.get("id")
        print(f"Agent created successfully: {agent_id}")
        print(f"Agent details: {json.dumps(agent_data, indent=2)}")
        return agent_id
    else:
        print(f"Failed to create agent: {response.status_code} - {response.text}")
        return None


def wait_for_agent_ready(
    access_token: str, agent_id: str, max_attempts: int = 30
) -> bool:
    """Wait for the agent to be ready."""
    print_separator("Waiting for Agent to be Ready")

    headers = {"Authorization": f"Bearer {access_token}"}

    for attempt in range(max_attempts):
        response = make_request("get", f"agents/{agent_id}", headers=headers)

        if response.status_code == 200:
            agent_data = response.json()
            status = agent_data.get("status")
            container_status = agent_data.get("container_status")
            container_id = agent_data.get("container_id")

            print(
                f"Attempt {attempt + 1}/{max_attempts}: Agent status: {status}, Container status: {container_status}"
            )

            # Check container logs if container is running but agent is not ready
            if container_status == "running" and status != "ready" and attempt > 0 and attempt % 5 == 0:
                print("Container is running but agent is not ready. Checking container logs...")
                logs_response = make_request(
                    "get", f"agents/{agent_id}/logs?lines=50", headers=headers
                )
                if logs_response.status_code == 200:
                    logs = logs_response.json()
                    print(f"Container logs:\n{logs.get('logs', 'No logs available')}")
                else:
                    print(f"Failed to get container logs: {logs_response.status_code} - {logs_response.text}")

            # For testing purposes, consider a container with running status as ready
            # This is because the Agno library might not be available in the container
            # but we still want to test the agent workflow
            if (status == "ready" or status == "active") and container_status == "running":
                print(f"Agent is considered ready for testing! (Status: {status}, Container: {container_status})")
                return True
        else:
            print(
                f"Failed to get agent status: {response.status_code} - {response.text}"
            )

        print("Waiting 5 seconds before checking again...")
        time.sleep(5)

    print("Timed out waiting for agent to be ready")
    
    # Get final container logs if available
    print("Getting final container logs...")
    logs_response = make_request("get", f"agents/{agent_id}/logs?lines=100", headers=headers)
    if logs_response.status_code == 200:
        logs = logs_response.json()
        print(f"Final container logs:\n{logs.get('logs', 'No logs available')}")
    
    return False


def chat_with_agent(access_token: str, agent_id: str) -> bool:
    """Send a chat message to the agent."""
    print_separator("Chatting with Agent")

    chat_data = {"query": "What can you tell me about this knowledge base?"}

    headers = {"Authorization": f"Bearer {access_token}"}
    response = make_request("post", f"agents/{agent_id}/chat", chat_data, headers)

    if response.status_code == 200:
        chat_response = response.json()
        print(f"Chat response: {json.dumps(chat_response, indent=2)}")
        
        # Check if the response contains the expected fallback format
        if "response" in chat_response and chat_response["response"].startswith("Echo:"):
            print("Agent is in fallback mode and responding correctly!")
        else:
            print("Agent responded but not in fallback mode.")
            
        return True
    else:
        print(
            f"Failed to chat with agent using /chat: {response.status_code} - {response.text}"
        )

        # Try the /query endpoint as fallback
        print("Trying /query endpoint as fallback...")
        response = make_request("post", f"agents/{agent_id}/query", chat_data, headers)

        if response.status_code == 200:
            chat_response = response.json()
            print(f"Query response: {json.dumps(chat_response, indent=2)}")
            
            # Check if the response contains the expected fallback format
            if "response" in chat_response and chat_response["response"].startswith("Echo:"):
                print("Agent is in fallback mode and responding correctly through query endpoint!")
            else:
                print("Agent responded through query endpoint but not in fallback mode.")
                
            return True
        else:
            print(f"Failed to query agent: {response.status_code} - {response.text}")
            return False


def main():
    """Run the focused test workflow for agent creation and chat."""
    print_separator("Starting Focused Test Workflow")

    # Create user
    # if not create_user():
    #     print("Failed to create user. Exiting.")
    #     return

    # Step 1: Login with existing user
    print("Logging in with existing user (testuser)...")
    access_token = login()
    if not access_token:
        print("Login failed. Exiting.")
        return

    print(f"Successfully logged in. Access token: {access_token[:10]}...")

    # Step 2: Get user ID
    print("Getting current user ID...")
    user_id = get_user_id(access_token)
    if not user_id:
        print("Failed to get user ID. Exiting.")
        return

    print(f"Current user ID: {user_id}")

    # Step 3: Create agent
    print("Creating agent...")
    agent_id = create_agent(access_token, user_id)
    if not agent_id:
        print("Failed to create agent. Exiting.")
        return

    print(f"Successfully created agent with ID: {agent_id}")
    
    # Step 3.5: Get agent details and check container status
    print("Getting agent details...")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = make_request("get", f"agents/{agent_id}", headers=headers)
    
    if response.status_code == 200:
        agent_data = response.json()
        container_id = agent_data.get("container_id")
        container_status = agent_data.get("container_status")
        print(f"Agent container ID: {container_id}")
        print(f"Agent container status: {container_status}")
        
        # Check container logs immediately
        print("Checking container logs...")
        logs_response = make_request("get", f"agents/{agent_id}/logs?lines=100", headers=headers)
        if logs_response.status_code == 200:
            logs = logs_response.json()
            print(f"Container logs:\n{logs.get('logs', 'No logs available')}")
        else:
            print(f"Failed to get container logs: {logs_response.status_code} - {logs_response.text}")
    else:
        print(f"Failed to get agent details: {response.status_code} - {response.text}")

    # Step 4: Wait for agent to be ready
    print("Waiting for agent to be ready...")
    if not wait_for_agent_ready(access_token, agent_id):
        print("Agent failed to become ready. Continuing anyway...")
    else:
        print("Agent is ready!")

    # Step 5: Chat with agent
    print("Sending chat message to agent...")
    chat_with_agent(access_token, agent_id)

    print_separator("Test Workflow Completed")


if __name__ == "__main__":
    main()
