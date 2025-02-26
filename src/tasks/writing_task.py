from crewai import Task
from src.agents.writing_agent import WritingAgent

def create_writing_task(agent: WritingAgent, research_output: str) -> Task:
    return Task(
        description=f"Write a concise article based on this research\n\nUse this research to write your article: {research_output}",
        expected_output="A well-written article.",
        agent=agent.create()
    )
