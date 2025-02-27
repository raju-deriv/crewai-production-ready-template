import re
from typing import Optional

def format_slack_message(text: str, bold: bool = False, message_type: Optional[str] = None) -> str:
    """
    Format text for Slack mrkdwn compatibility with enhanced readability.
    
    Args:
        text: The text to format
        bold: Whether to apply bold formatting to the entire message
        message_type: The type of message (e.g., 'conversation', 'research', 'weather')
                     Used to determine the appropriate formatting style
    """
    # Convert Markdown-style **bold** to Slack *bold*
    formatted_text = text.replace("**", "*")
    
    # Apply bold to entire message if requested
    if bold and not formatted_text.startswith("*"):
        formatted_text = f"*{formatted_text}*"
    
    # Ensure Slack-compatible formatting
    lines = formatted_text.split("\n")
    formatted_lines = []
    
    # Use simpler formatting for conversation messages
    is_conversation = message_type == 'conversation'
    
    # Add a decorative header with color (except for conversation messages)
    if not is_conversation:
        formatted_lines.append(":zap: `Insights & Information` :bulb:")
        formatted_lines.append("")
    
    # Process the content
    in_list = False
    in_code_block = False
    section_title = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            # Add spacing between sections
            if formatted_lines and formatted_lines[-1] != "":
                formatted_lines.append("")
            continue
            
        # Detect section titles (lines ending with a colon)
        if line.endswith(":") and len(line) < 50 and not in_code_block:
            section_title = line
            # Add divider before new sections (except for the first one)
            if i > 1 and formatted_lines and formatted_lines[-1] != "":
                formatted_lines.append("")
            # Create a more visually striking section header
            emoji = ":mag:" # Default emoji
            
            # Choose appropriate emoji based on section title
            lower_title = section_title.lower()
            if "weather" in lower_title:
                emoji = ":partly_sunny:"
            elif "forecast" in lower_title:
                emoji = ":calendar:"
            elif "research" in lower_title or "analysis" in lower_title:
                emoji = ":microscope:"
            elif "summary" in lower_title:
                emoji = ":memo:"
            elif "conclusion" in lower_title:
                emoji = ":checkered_flag:"
            elif "recommendation" in lower_title:
                emoji = ":star:"
            elif "data" in lower_title or "statistic" in lower_title:
                emoji = ":bar_chart:"
            
            # Use block quote for section headers to add color
            formatted_lines.append(f"> {emoji} *{section_title}*")
            formatted_lines.append("")
            continue
            
        # Handle code blocks
        if line.startswith("```") or line.endswith("```"):
            in_code_block = not in_code_block
            formatted_lines.append(line)
            continue
            
        # Handle bullet points
        if line.startswith("- ") or line.startswith("* "):
            # Replace standard bullets with emoji bullets
            if not in_list:
                in_list = True
                if formatted_lines and formatted_lines[-1] != "":
                    formatted_lines.append("")
            
            # Use a variety of bullet point styles for visual interest
            bullet_styles = ["•", "◦", "◉", "○", "▪", "▫", "◆", "◇", "►", "▻"]
            bullet_index = len(formatted_lines) % len(bullet_styles)
            bullet_content = line[2:].strip()
            
            # Add some emphasis to important bullet points with color
            if any(keyword in bullet_content.lower() for keyword in ["important", "critical", "key", "main", "significant"]):
                formatted_lines.append(f"{bullet_styles[bullet_index]} `{bullet_content}`")
            else:
                formatted_lines.append(f"{bullet_styles[bullet_index]} {bullet_content}")
            continue
            
        # Handle numbered lists
        if re.match(r"^\d+\.\s", line.strip()):
            formatted_lines.append(line)
            continue
            
        # Enhanced weather information with more visually appealing formatting
        lower_line = line.lower()
        if "temperature:" in lower_line:
            temp_parts = line.split(":")
            if len(temp_parts) > 1:
                temp_value = temp_parts[1].strip()
                formatted_lines.append(f":thermometer: *Temperature*: `{temp_value}`")
            else:
                formatted_lines.append(f":thermometer: {line}")
        elif "humidity:" in lower_line:
            humid_parts = line.split(":")
            if len(humid_parts) > 1:
                humid_value = humid_parts[1].strip()
                formatted_lines.append(f":droplet: *Humidity*: `{humid_value}`")
            else:
                formatted_lines.append(f":droplet: {line}")
        elif "wind speed:" in lower_line:
            wind_parts = line.split(":")
            if len(wind_parts) > 1:
                wind_value = wind_parts[1].strip()
                formatted_lines.append(f":dash: *Wind Speed*: `{wind_value}`")
            else:
                formatted_lines.append(f":dash: {line}")
        elif "conditions:" in lower_line:
            cond_parts = line.split(":")
            if len(cond_parts) > 1:
                cond_value = cond_parts[1].strip()
                # Choose appropriate emoji based on weather condition
                cond_emoji = ":cloud:"
                if "sun" in cond_value.lower() or "clear" in cond_value.lower():
                    cond_emoji = ":sunny:"
                elif "rain" in cond_value.lower():
                    cond_emoji = ":rain_cloud:"
                elif "snow" in cond_value.lower():
                    cond_emoji = ":snowflake:"
                elif "cloud" in cond_value.lower() and "sun" in cond_value.lower():
                    cond_emoji = ":partly_sunny:"
                elif "thunder" in cond_value.lower() or "storm" in cond_value.lower():
                    cond_emoji = ":thunder_cloud_and_rain:"
                formatted_lines.append(f"{cond_emoji} *Conditions*: `{cond_value}`")
            else:
                formatted_lines.append(f":cloud: {line}")
        elif "forecast:" in lower_line or lower_line.endswith("forecast:"):
            # Use block quote for forecast headers to add color
            formatted_lines.append(f"> :calendar: *{line}*")
            formatted_lines.append("")
        elif "high:" in lower_line:
            high_parts = line.split(":")
            if len(high_parts) > 1:
                high_value = high_parts[1].strip()
                formatted_lines.append(f":arrow_up: *High*: `{high_value}`")
            else:
                formatted_lines.append(f":arrow_up: {line}")
        elif "low:" in lower_line:
            low_parts = line.split(":")
            if len(low_parts) > 1:
                low_value = low_parts[1].strip()
                formatted_lines.append(f":arrow_down: *Low*: `{low_value}`")
            else:
                formatted_lines.append(f":arrow_down: {line}")
        elif "chance of rain:" in lower_line:
            rain_parts = line.split(":")
            if len(rain_parts) > 1:
                rain_value = rain_parts[1].strip()
                formatted_lines.append(f":umbrella: *Chance of Rain*: `{rain_value}`")
            else:
                formatted_lines.append(f":umbrella: {line}")
        # Regular line
        else:
            formatted_lines.append(line)
            
        # Reset list state if line doesn't continue the list
        if in_list and not (line.startswith("- ") or line.startswith("* ")):
            in_list = False
    
    # Add a more visually appealing footer with color (except for conversation messages)
    formatted_lines.append("")
    if not is_conversation:
        formatted_lines.append("> :speech_balloon: _Questions? Clarifications? Just ask!_ :sparkles:")
    
    return "\n".join(formatted_lines)
