def format_slack_message(text: str, bold: bool = False) -> str:
    """Format text for Slack mrkdwn compatibility."""
    # Convert Markdown-style **bold** to Slack *bold*
    formatted_text = text.replace("**", "*")
    
    # Apply bold to entire message if requested
    if bold and not formatted_text.startswith("*"):
        formatted_text = f"*{formatted_text}*"
    
    # Ensure Slack-compatible formatting
    lines = formatted_text.split("\n")
    formatted_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # Bold the first line as a header if not already formatted
        if i == 0 and not line.startswith("*"):
            formatted_lines.append(f"*Response*\n{line}")
        else:
            formatted_lines.append(line)
    
    return "\n".join(formatted_lines)