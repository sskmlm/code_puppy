from pathlib import Path


def test_chat_template_includes_markdown_sanitization_guards():
    html = Path("code_puppy/api/templates/chat.html").read_text()

    assert "dompurify" in html.lower()
    assert "DOMPurify.sanitize" in html
    assert "escapeHtml(String(title))" in html
    assert "escapeHtml(String(description))" in html
    # Tool card text is assigned through textContent, not innerHTML.
    assert "const toolName = String(" in html
    assert "message.tool_name || message.tool" in html
    assert "nm.textContent = toolName" in html
    assert "escapeHtml(String(message.agent_name" in html
    assert "onclick=\"approvePermission" not in html
    assert "onclick=\"denyPermission" not in html


def test_permission_request_buttons_use_dom_event_handlers():
    html = Path("code_puppy/api/templates/chat.html").read_text()
    assert "approveBtn.addEventListener('click', () => approvePermission(requestId));" in html
    assert "denyBtn.addEventListener('click', () => denyPermission(requestId));" in html


def test_chat_template_uses_wss_fallback_aware_url_template():
    html = Path("code_puppy/api/templates/chat.html").read_text()
    # Ensure we still have explicit websocket URL handling in the template.
    assert "wsUrl" in html
    assert "encodeURIComponent(CONFIG.sessionId)" in html
