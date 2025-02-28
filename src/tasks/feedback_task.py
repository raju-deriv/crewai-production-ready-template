from crewai import Task
from src.agents.feedback_agent import FeedbackAgent

def create_feedback_task(agent: FeedbackAgent, user_id: str, channel_id: str, initial_message: str = None) -> Task:
    """
    Create a task for collecting feedback from users.
    
    Args:
        agent: The feedback agent to use
        user_id: ID of the user providing feedback
        channel_id: ID of the channel where feedback is being collected
        initial_message: Optional initial message from the user
        
    Returns:
        A Task object for collecting feedback
    """
    context = [
        f"User ID: {user_id}",
        f"Channel ID: {channel_id}"
    ]
    
    if initial_message:
        context.append(f"Initial message: {initial_message}")
    
    context.extend([
        "Collect feedback by asking a series of questions one at a time.",
        "Start by explaining the purpose of the feedback collection.",
        "Ask each question, acknowledge the response, then move to the next question.",
        "After collecting all feedback, save it to Google Sheets.",
        "Thank the user for their feedback."
    ])
    
    return Task(
        description=f"Collect feedback from the user\n\n{' '.join(context)}",
        expected_output="A complete feedback collection session with all questions answered and saved to Google Sheets",
        agent=agent.create()
    )
