"""
Celery worker for the Agent Manager.
"""

import os
from celery import Celery

# Get Redis URL from environment variable or use default
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "agent_manager",
    broker=redis_url,
    backend=redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def deploy_agent(agent_id):
    """Deploy an agent."""
    # This is a placeholder for the actual deployment logic
    print(f"Deploying agent {agent_id}")
    return {"status": "success", "agent_id": agent_id}


@celery_app.task
def stop_agent(agent_id):
    """Stop an agent."""
    # This is a placeholder for the actual stop logic
    print(f"Stopping agent {agent_id}")
    return {"status": "success", "agent_id": agent_id}


@celery_app.task
def delete_agent(agent_id):
    """Delete an agent."""
    # This is a placeholder for the actual deletion logic
    print(f"Deleting agent {agent_id}")
    return {"status": "success", "agent_id": agent_id}
