import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import database
from tools import AVAILABLE_TOOLS

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def load_system_prompt():
    prompt_parts = []
    prompt_dir = "prompts"
    prompt_files = ['identity.md', 'soul.md', 'skills.md', 'knowledge.md', 'agent.md']
    for file_name in prompt_files:
        path = os.path.join(prompt_dir, file_name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    prompt_parts.append(f"--- {file_name.upper()} ---\n{content}\n")
    return "\n".join(prompt_parts)

generation_config = {
    "temperature": 0.7,
    "response_mime_type": "application/json",
}

def process_message(user_message):
    try:
        model_name = database.get_setting("active_model", "gemini-3.1-flash-lite-preview")
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=load_system_prompt()
        )
        
        # Build chat context
        history = database.get_recent_chat(limit=5)
        
        # For Gemini, role must be 'user' or 'model'
        # Convert our history formats
        formatted_history = []
        for msg in history:
            role = 'user' if msg['role'] == 'user' else 'model'
            formatted_history.append({"role": role, "parts": [msg['content']]})
            
        # Append current message
        formatted_history.append({"role": "user", "parts": [user_message]})
        database.save_chat("user", user_message)
        
        response = model.generate_content(formatted_history)
        
        parsed = json.loads(response.text)
        
        final_reply = ""
        
        if parsed.get("requires_tool") and parsed.get("tool_name"):
            tool_name = parsed["tool_name"]
            if tool_name in AVAILABLE_TOOLS:
                tool_func = AVAILABLE_TOOLS[tool_name]
                kwargs = parsed.get("data", {})
                tool_result = tool_func(**kwargs)
                final_reply = tool_result
            else:
                final_reply = f"Error: Tool {tool_name} is not implemented yet."
        elif parsed.get("intent") == "chat":
            final_reply = parsed.get("data", {}).get("reply", "I'm not sure how to respond to that.")
        elif parsed.get("intent") == "email" and parsed.get("action") == "draft":
            purpose = parsed.get("data", {}).get("purpose", "General")
            msg = parsed.get("data", {}).get("message", "")
            final_reply = AVAILABLE_TOOLS["email_draft"](purpose, msg)
        elif parsed.get("intent") == "todo" and parsed.get("action") == "read":
            final_reply = AVAILABLE_TOOLS["todo_list"]()
        else:
            final_reply = "I understood your request but I don't have the required tool set up yet."
            
        database.save_chat("model", final_reply)
        return final_reply
            
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"
