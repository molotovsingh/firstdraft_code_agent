# Codex Configuration

This directory contains workspace-level configuration for Codex CLI.

## Configuration Options

The `config.json` file supports the following options:

### reasoning
**Type**: `string`
**Values**: `"low"`, `"medium"`, `"high"`
**Default**: `"medium"`
**Current**: `"high"`

Controls the reasoning level for AI responses:
- `"low"`: Minimal reasoning, fastest responses
- `"medium"`: Balanced reasoning and performance
- `"high"`: Detailed reasoning with step-by-step explanations

### Example Configuration

```
{
  "reasoning": "high"
}
```

## Usage

This configuration is automatically applied when running Codex CLI commands from this workspace or any subdirectory. The settings override user-level defaults but can be overridden by command-line flags.

## Priority Order

1. Command-line flags (highest priority)
2. Workspace config (`.codex/config.json`)
3. User config (`~/.codex/config.json`)
4. System defaults (lowest priority)

## Additional Options

Future versions may support additional configuration options such as:
- `model`: Specify the AI model to use
- `temperature`: Control response creativity
- `max_tokens`: Limit response length
- `timeout`: Set request timeout
- `api_key`: Override API key (not recommended for version control)

## Notes

- This configuration is version-controlled and shared with the repository
- Sensitive settings like API keys should not be stored here
- The `.codex/` directory is tracked by git to ensure consistent behavior across team members
