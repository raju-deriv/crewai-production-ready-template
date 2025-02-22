from crewai import Crew, Process
from src.config.settings import Settings
from src.agents.research_agent import ResearchAgent
from src.agents.writing_agent import WritingAgent
from src.tasks.research_task import create_research_task
from src.tasks.writing_task import create_writing_task
from src.crew.base_crew import BaseCrew

class ResearchWritingCrew(BaseCrew):
    """Crew for research and writing tasks."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.research_agent = ResearchAgent(settings)
        self.writing_agent = WritingAgent(settings)

    def create_crew(self, inputs: dict[str, str]) -> Crew:
        topic = inputs.get("topic", "")
        research_task = create_research_task(self.research_agent, topic)
        writing_task = create_writing_task(self.writing_agent, "{result of research task}")
        return Crew(
            agents=[self.research_agent.create(), self.writing_agent.create()],
            tasks=[research_task, writing_task],
            process=Process.sequential,
            verbose=True
        )