from typing import Dict, Any, List, Optional
import structlog
import json
from langchain.tools import Tool
import gspread
from google.oauth2.service_account import Credentials
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class FeedbackTool:
    """Tool for collecting feedback and saving it to Google Sheets."""
    
    # Define the standard feedback questions
    DEFAULT_QUESTIONS = [
        {"question": "On a scale of 1-10, how would you rate your overall experience?", "category": "satisfaction"},
        {"question": "What aspects did you find most helpful or enjoyable?", "category": "positive"},
        {"question": "What aspects could be improved?", "category": "improvement"},
        {"question": "Do you have any additional comments or suggestions?", "category": "general"}
    ]
    
    def __init__(self, settings: Settings = None):
        """Initialize the feedback tool with settings."""
        self._settings = settings
        self.sheets_enabled = False
        self.sheets_client = None
        self.spreadsheet = None
        self.worksheet = None
        
        # Create a LangChain Tool for use with CrewAI
        self.name = "feedback_tool"
        self.description = """
        Use this tool to collect feedback from users through a structured series of questions
        and save the collected feedback to Google Sheets. The tool can:
        1. Start a new feedback collection session
        2. Process a user's response to a feedback question
        3. Save completed feedback to Google Sheets
        
        The feedback collection process typically involves asking a series of questions about:
        - Overall satisfaction with the product/service
        - Specific aspects that worked well
        - Areas for improvement
        - Additional comments or suggestions
        
        You should guide the user through this process conversationally, asking one question at a time
        and acknowledging their responses before moving to the next question.
        """
        
        # Set up Google Sheets if settings are provided
        if settings:
            self._setup_google_sheets()
    
    def __call__(self):
        """Make the tool callable to satisfy LangChain's requirements."""
        return Tool(
            name=self.name,
            description=self.description,
            func=self.run
        )
        
    def _setup_google_sheets(self):
        """Set up Google Sheets connection if credentials are available."""
        try:
            # Check if Google Sheets credentials are configured
            if hasattr(self._settings, 'google_sheets_credentials_file') and self._settings.google_sheets_credentials_file:
                # Define the scopes
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                
                # Load credentials from the service account file
                creds = Credentials.from_service_account_file(
                    self._settings.google_sheets_credentials_file, 
                    scopes=scopes
                )
                
                # Create a client to interact with Google Sheets API
                self.sheets_client = gspread.authorize(creds)
                
                # Get the spreadsheet by ID or create it if it doesn't exist
                if hasattr(self._settings, 'feedback_spreadsheet_id') and self._settings.feedback_spreadsheet_id:
                    try:
                        self.spreadsheet = self.sheets_client.open_by_key(self._settings.feedback_spreadsheet_id)
                        logger.info("Connected to existing feedback spreadsheet")
                    except gspread.exceptions.SpreadsheetNotFound:
                        logger.warning("Feedback spreadsheet not found, creating a new one")
                        self.spreadsheet = self.sheets_client.create("Feedback Collection")
                        # Share with the service account email
                        if hasattr(self._settings, 'google_service_account_email'):
                            self.spreadsheet.share(
                                self._settings.google_service_account_email, 
                                perm_type='user', 
                                role='writer'
                            )
                else:
                    logger.warning("No feedback spreadsheet ID configured, creating a new one")
                    self.spreadsheet = self.sheets_client.create("Feedback Collection")
                
                # Ensure the worksheet exists
                try:
                    self.worksheet = self.spreadsheet.worksheet("Feedback")
                except gspread.exceptions.WorksheetNotFound:
                    self.worksheet = self.spreadsheet.add_worksheet(
                        title="Feedback", 
                        rows=1000, 
                        cols=20
                    )
                    # Set up headers
                    headers = ["Timestamp", "User ID", "Channel ID", "Question Category", "Question", "Answer"]
                    self.worksheet.append_row(headers)
                
                logger.info("Google Sheets integration set up successfully")
                self.sheets_enabled = True
            else:
                logger.warning("Google Sheets credentials not configured, feedback will be logged but not saved to sheets")
                self.sheets_enabled = False
        except Exception as e:
            logger.error("Failed to set up Google Sheets integration", error=str(e), exc_info=True)
            self.sheets_enabled = False
    
    def run(self, input_str: str) -> str:
        """Run the feedback tool with the specified input string."""
        try:
            # Parse the input string as JSON
            input_data = json.loads(input_str)
            
            action = input_data.get("action")
            user_id = input_data.get("user_id")
            channel_id = input_data.get("channel_id")
            message = input_data.get("message")
            current_question_index = input_data.get("current_question_index")
            collected_feedback = input_data.get("collected_feedback")
            custom_questions = input_data.get("custom_questions")
            
            # Validate required parameters
            if not action or not user_id or not channel_id:
                return json.dumps({
                    "status": "error",
                    "error": "Missing required parameters: action, user_id, and channel_id are required"
                })
            
            # Use custom questions if provided, otherwise use default questions
            questions = custom_questions if custom_questions else self.DEFAULT_QUESTIONS
            
            if action == "start_feedback":
                # Start a new feedback collection session
                result = {
                    "status": "started",
                    "next_question": questions[0]["question"],
                    "next_question_index": 0,
                    "total_questions": len(questions),
                    "collected_feedback": []
                }
                
            elif action == "process_response":
                if current_question_index is None or collected_feedback is None or message is None:
                    return json.dumps({
                        "status": "error",
                        "error": "Missing required parameters for process_response action"
                    })
                
                # Process the user's response to the current question
                current_question = questions[current_question_index]
                
                # Add the response to collected feedback
                feedback_item = {
                    "question": current_question["question"],
                    "answer": message,
                    "category": current_question["category"]
                }
                
                updated_feedback = collected_feedback + [feedback_item]
                
                # Check if we have more questions
                next_question_index = current_question_index + 1
                if next_question_index < len(questions):
                    # More questions to ask
                    result = {
                        "status": "in_progress",
                        "next_question": questions[next_question_index]["question"],
                        "next_question_index": next_question_index,
                        "total_questions": len(questions),
                        "collected_feedback": updated_feedback
                    }
                else:
                    # All questions answered
                    result = {
                        "status": "completed",
                        "collected_feedback": updated_feedback
                    }
                    
            elif action == "save_feedback":
                if collected_feedback is None:
                    return json.dumps({
                        "status": "error",
                        "error": "Missing required parameters for save_feedback action"
                    })
                
                # Save the collected feedback to Google Sheets
                if self.sheets_enabled:
                    from datetime import datetime
                    timestamp = datetime.now().isoformat()
                    
                    # Prepare rows to append
                    rows = []
                    for item in collected_feedback:
                        row = [
                            timestamp,
                            user_id,
                            channel_id,
                            item["category"],
                            item["question"],
                            item["answer"]
                        ]
                        rows.append(row)
                    
                    # Append to the worksheet
                    for row in rows:
                        self.worksheet.append_row(row)
                    
                    logger.info("Saved feedback to Google Sheets", 
                               user_id=user_id, 
                               items_count=len(collected_feedback))
                    
                    result = {
                        "status": "saved",
                        "message": "Feedback successfully saved to Google Sheets",
                        "saved_items": len(collected_feedback)
                    }
                else:
                    # Log the feedback if Google Sheets is not enabled
                    logger.info("Feedback collected but not saved to Google Sheets (not configured)", 
                               user_id=user_id,
                               feedback=collected_feedback)
                    
                    result = {
                        "status": "logged",
                        "message": "Feedback logged but not saved to Google Sheets (not configured)",
                        "collected_feedback": collected_feedback
                    }
            else:
                result = {
                    "status": "error",
                    "error": f"Unknown action: {action}"
                }
                
            return json.dumps(result)
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON input", input=input_str)
            return json.dumps({
                "status": "error",
                "error": "Invalid JSON input"
            })
        except Exception as e:
            logger.error("Error in feedback tool", error=str(e), exc_info=True)
            return json.dumps({
                "status": "error",
                "error": str(e)
            })
