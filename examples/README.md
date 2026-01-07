# Examples

## Chat with Memory

Interactive chatbot with memory management.

**Run:**
```bash
python examples/sage_chat.py
```

**Configure your LLM** in `sage_chat.py`:

```python
PIPELINE_CONFIG = {
    "api_key": "your-api-key",
    "base_url": "http://your-llm-endpoint/v1",
    "model_name": "your-model-name",
    # ... other settings
}
```
