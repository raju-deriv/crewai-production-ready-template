from crewai import Task
from agents.writing_agent import WritingAgent

def create_writing_task(agent: WritingAgent, research_output: str) -> Task:
    """Create a writing task based on research output."""
    return Task(
        description=f"Write a concise article based on this research: {research_output}",
        agent=agent.create(),
        expected_output="A well-written article."
    )