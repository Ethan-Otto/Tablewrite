# Foundry UI Feedback Scripts

Development tools for collecting visual feedback on UI changes. **Not CI tests** - these are for interactive development.

## Prerequisites

- Foundry running at `http://localhost:30000`
- "TestingGamemaster" user exists (no password)
- Playwright installed: `pip install playwright && playwright install chromium`

## Quick Usage

```python
from foundry_helper import FoundrySession

with FoundrySession() as s:
    s.goto_tablewrite()
    s.send_message("/help")
    s.screenshot("/tmp/result.png")
```

## Common Patterns

### Screenshot after UI change
```python
from foundry_helper import quick_screenshot
quick_screenshot("/tmp/my_change.png")
```

### Test message rendering
```python
from foundry_helper import test_message
result = test_message("Create a goblin")
print(result['html'])  # Check HTML structure
print(result['text'])  # Check text content
```

### Debug CSS styling
```python
with FoundrySession() as s:
    s.goto_tablewrite()
    styles = s.get_element_styles('.tablewrite-input')
    print(f"Input height: {styles['height']}")
```

### Verify tab switching
```python
with FoundrySession() as s:
    result = s.check_tab_switching()
    assert result['tablewrite_visible']
    assert result['tablewrite_hidden']  # after switching to chat
```

### Non-headless for debugging
```python
with FoundrySession(headless=False) as s:
    s.goto_tablewrite()
    input("Press Enter when done inspecting...")
```

## Key Methods

| Method | Description |
|--------|-------------|
| `goto_tablewrite()` | Navigate to Tablewrite tab |
| `goto_chat()` | Navigate to native Chat tab |
| `send_message(text)` | Send message, wait for response |
| `screenshot(path)` | Save screenshot of sidebar |
| `get_message_html()` | Get latest response HTML |
| `get_message_text()` | Get latest response text |
| `get_element_styles(selector)` | Get computed CSS styles |
| `check_tab_switching()` | Verify tabs show/hide correctly |
