import database
import requests
import json
import os
import smtplib
import subprocess
import psutil
from email.message import EmailMessage
from duckduckgo_search import DDGS
from datetime import datetime

def memory_create(key="none", value="", category="general"):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memories (key, value, category) VALUES (?, ?, ?)", (key, value, category))
    conn.commit()
    conn.close()
    return f"Saved: {value}"

def memory_search(query=""):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM memories WHERE key LIKE ? OR value LIKE ? OR category LIKE ?", 
                   (f"%{query}%", f"%{query}%", f"%{query}%"))
    results = cursor.fetchall()
    conn.close()
    if not results:
        return "I couldn't find any memories matching that."
    return "I found these memories:\n" + "\n".join([row['value'] for row in results])

def todo_create(title, due_date=None, priority='normal'):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (title, due_date, priority) VALUES (?, ?, ?)", (title, due_date, priority))
    conn.commit()
    conn.close()
    return f"Added task: {title}"

def todo_list():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, due_date, priority FROM todos WHERE status='pending'")
    results = cursor.fetchall()
    conn.close()
    if not results:
        return "You have no pending tasks."
    res = f"You have {len(results)} pending tasks:\n"
    for i, row in enumerate(results, 1):
        res += f"{i}. {row['title']}"
        if row['due_date']:
            res += f" (Due: {row['due_date']})"
        res += "\n"
    return res

def todo_complete(title_query):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM todos WHERE title LIKE ? AND status='pending'", (f"%{title_query}%",))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE todos SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?", (row['id'],))
        conn.commit()
        conn.close()
        return f"Marked task as completed: {row['title']}"
    conn.close()
    return f"Could not find pending task matching: {title_query}"

def reminder_create(title, remind_at, repeat_rule=None):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders (title, remind_at, repeat_rule) VALUES (?, ?, ?)", (title, remind_at, repeat_rule))
    conn.commit()
    conn.close()
    return f"Reminder set: {title} at {remind_at}"

def website_check(url):
    if not url.startswith("http"):
        url = "https://" + url
    
    try:
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        response_time = int(response.elapsed.total_seconds() * 1000)
        is_online = 200 <= status_code < 400
        
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO website_checks (url, status_code, response_time_ms, result) VALUES (?, ?, ?, ?)",
            (url, status_code, response_time, "Online" if is_online else "Offline")
        )
        conn.commit()
        conn.close()
        
        res = f"Website status for {url}:\n"
        res += f"- Online: {'Yes' if is_online else 'No'}\n"
        res += f"- Status: {status_code}\n"
        res += f"- Response time: {response_time} ms"
        return res
    except Exception as e:
        return f"Failed to check website {url}: {str(e)}"

def email_draft(purpose="email", message=""):
    return f"Subject: {purpose.title()}\n\nHi,\n\n{message}\n\nRegards,\nMohan"

def knowledge_create(title, content, tags=""):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO knowledge_base (title, content, tags) VALUES (?, ?, ?)", (title, content, tags))
    conn.commit()
    conn.close()
    return f"Saved to knowledge base:\nTitle: {title}\nTags: {tags}"

def knowledge_search(query):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, content FROM knowledge_base WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?", 
                   (f"%{query}%", f"%{query}%", f"%{query}%"))
    results = cursor.fetchall()
    conn.close()
    if not results:
        return "Nothing found in knowledge base."
    res = "Found in knowledge base:\n\n"
    for row in results:
        res += f"**{row['title']}**\n{row['content']}\n\n"
    return res.strip()

def web_search(query):
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No web search results found."
        res = "Web Search Results:\n"
        for r in results:
            res += f"- **{r['title']}**: {r['body']}\n"
        return res
    except Exception as e:
        return f"Web search failed: {str(e)}"

def expense_add(amount, category="general", description=""):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)", (amount, category, description))
    conn.commit()
    conn.close()
    return f"Added expense: ${amount} for {category} ({description})"

def expense_summary(month=None):
    conn = database.get_connection()
    cursor = conn.cursor()
    if month:
        cursor.execute("SELECT SUM(amount) as total FROM expenses WHERE strftime('%Y-%m', created_at) = ?", (month,))
    else:
        cursor.execute("SELECT SUM(amount) as total FROM expenses")
    row = cursor.fetchone()
    conn.close()
    total = row['total'] if row['total'] else 0
    return f"Total expenses: ${total:.2f}"

def email_send(to_email, subject, body):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 587))
    
    if not user or not password:
        return "Email credentials not configured in .env."
        
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = to_email
        
        s = smtplib.SMTP(server, port)
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
        s.quit()
        return f"Email successfully sent to {to_email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

def server_status():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        res = "💻 **Server Status**\n"
        res += f"- **CPU Usage:** {cpu}%\n"
        res += f"- **RAM Usage:** {ram.percent}% ({ram.used // (1024**3)}GB / {ram.total // (1024**3)}GB)\n"
        res += f"- **Disk Usage:** {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        return res
    except Exception as e:
        return f"Failed to get server status: {str(e)}"

def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout if result.stdout else result.stderr
        
        if not output:
            return f"Command executed successfully (no output).\nExit code: {result.returncode}"
            
        if len(output) > 2000:
            output = output[:2000] + "\n...[truncated]"
            
        return f"💻 **Command Output** (Exit: {result.returncode}):\n```\n{output}\n```"
    except subprocess.TimeoutExpired:
        return "Command timed out after 15 seconds."
    except Exception as e:
        return f"Failed to execute command: {str(e)}"

# Create dictionary of available tools
AVAILABLE_TOOLS = {
    "memory_create": memory_create,
    "memory_search": memory_search,
    "todo_create": todo_create,
    "todo_list": todo_list,
    "todo_complete": todo_complete,
    "reminder_create": reminder_create,
    "website_check": website_check,
    "email_draft": email_draft,
    "email_send": email_send,
    "knowledge_create": knowledge_create,
    "knowledge_search": knowledge_search,
    "web_search": web_search,
    "expense_add": expense_add,
    "expense_summary": expense_summary,
    "server_status": server_status,
    "execute_command": execute_command,
}
