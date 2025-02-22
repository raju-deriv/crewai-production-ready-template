from crewai import Task
from src.agents.research_agent import ResearchAgent

def create_research_task(agent: ResearchAgent, topic: str) -> Task:
    return Task(
        description=f"Research the topic: {topic}",
        agent=agent.create(),
        expected_output="A detailed summary of the research findings."
    )