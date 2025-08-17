# Nexus CLI Architecture

This document explains the architecture and design of Nexus CLI, a local-first 5-agent development stack.

## Overview

Nexus CLI is designed as a file-based, agent-driven task management and development system. It uses a clean separation of concerns with minimal external dependencies, emphasizing reliability and human-readable data formats.

## Core Principles

- **Local-first**: All data stored locally in human-readable formats
- **File-based**: No external databases; uses filesystem as the primary data store
- **Agent-driven**: Specialized agents handle different aspects of development
- **Extensible**: Modular design allows for easy addition of new providers and agents
- **Observable**: Rich console output and markdown-based activity tracking

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nexus CLI System                        │
├─────────────────────────────────────────────────────────────────┤
│  Discord Bot    │  File Watcher   │  Obsidian Vault Integration │
├─────────────────┼─────────────────┼─────────────────────────────┤
│                      Orchestrator                               │
├─────────────────────────────────────────────────────────────────┤
│                     Provider Router                             │
├─────────────────────────────────────────────────────────────────┤
│  Claude Code  │  Codex CLI  │  DeepSeek  │  OpenRouter  │  Qwen │
├─────────────────────────────────────────────────────────────────┤
│                      Task Queue System                          │
├─────────────────────────────────────────────────────────────────┤
│   Inbox    │   Backlog   │   Sprint   │   Done   │   Archive    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Task Queue System (`core/queue.py`, `core/task.py`)

The foundation of the system is a file-based task queue with four states:

- **Inbox**: New tasks waiting for initial processing
- **Backlog**: Scoped and prioritized tasks ready for planning
- **Sprint**: Active tasks being worked on
- **Done**: Completed tasks with full history

#### Task Model

Tasks are stored as markdown files with YAML front matter:

```yaml
---
id: task_123
title: "Implement user authentication"
status: "sprint"
priority: "high"
tags: ["feature", "security"]
assigned_agent: "senior_dev"
acceptance_criteria:
  - "User can register with email/password"
  - "Secure password hashing implemented"
  - "Session management working"
created_at: "2024-01-15T10:30:00"
updated_at: "2024-01-15T15:45:00"
---

# Implement user authentication

Create a secure authentication system for the application...

## Activity

- **2024-01-15 10:30:00** [communications] created from user idea
- **2024-01-15 11:00:00** [project_manager] scoped and assigned to senior_dev
- **2024-01-15 15:45:00** [senior_dev] started implementation
```

### 2. Agent System

Five specialized agents handle different aspects of development:

#### Communications Agent (`agents/communications/main.py`)
- Converts ideas and feedback into structured task cards
- Updates project roadmap
- Handles user input processing

#### Project Manager Agent (`agents/project_manager/main.py`)
- Scopes tasks with acceptance criteria
- Sets priorities and assigns agents
- Manages sprint planning

#### Senior Developer Agent (`agents/senior_dev/main.py`)
- Handles complex architectural tasks
- Breaks down large tasks into subtasks
- Reviews junior developer work

#### Junior Developer Agent (`agents/junior_dev/main.py`)
- Implements functions and features
- Writes unit tests
- Handles straightforward development tasks

#### Release QA Agent (`agents/release_qa/main.py`)
- Creates comprehensive test plans
- Generates release documentation
- Manages release processes

### 3. Orchestrator (`core/orchestrator.py`)

The orchestrator coordinates the entire system:

- **File Watching**: Monitors `tasks/inbox/` for new files
- **Task Routing**: Routes tasks to appropriate agents
- **State Management**: Manages task transitions between queues
- **Agent Coordination**: Ensures proper workflow between agents

#### Workflow

```
1. New file in inbox → Task promotion to backlog
2. Backlog task → Project Manager scoping
3. Scoped task → Sprint planning
4. Sprint task → Agent assignment and work
5. Completed work → QA and done queue
```

### 4. Provider System (`connectors/providers/`)

A modular provider system supports multiple AI services with fallback logic:

#### Base Provider (`connectors/providers/base.py`)
Abstract interface defining the provider contract:

```python
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
```

#### Provider Implementations
- **Claude Code Provider**: Uses Claude Code CLI
- **Codex CLI Provider**: Uses GitHub Codex CLI
- **DeepSeek Provider**: HTTP API integration
- **OpenRouter Provider**: HTTP API integration
- **Qwen Provider**: HTTP API integration

#### Router (`core/router.py`)

The router manages provider selection with fallback logic:

1. Check role configuration for preferred providers
2. Respect `USE_PAID_MODELS` environment setting
3. Try providers in order until success
4. Track usage and budgets

### 5. Configuration System (`core/config.py`)

Hierarchical configuration with environment variable expansion:

#### Settings (`config/settings.toml`)
```toml
[general]
project_name = "Nexus CLI"

[discord]
token = "${DISCORD_BOT_TOKEN}"

[vault]
obsidian_path = "${OBSIDIAN_VAULT_PATH}"
```

#### Roles (`config/roles.yaml`)
```yaml
roles:
  senior_dev:
    model: "claude-3.5-sonnet"
    providers: ["claude_code", "openrouter"]
    budgets:
      monthly_limit: 200.0
```

#### Models (`config/models.yaml`)
```yaml
models:
  claude-3.5-sonnet:
    provider_name: "claude_code"
    cost_per_1k_tokens: 0.003
    is_paid: true
```

### 6. External Integrations

#### Discord Bot (`connectors/discord/bot.py`)

Provides chat interface with three main commands:

- `/idea <text>`: Creates new tasks from ideas
- `/feedback <text>`: Processes user feedback
- `/status`: Shows system status and queue counts

#### Obsidian Vault Integration (`connectors/vault/fs.py`)

Synchronizes project data with Obsidian vault:

- Task files organized by status
- Release documentation
- Roadmap and architecture docs
- Feedback collection

```
Obsidian Vault/
└── Nexus CLI/
    ├── Tasks/
    │   ├── Inbox/
    │   ├── Backlog/
    │   ├── Sprint/
    │   └── Done/
    ├── Documentation/
    ├── Releases/
    └── Feedback/
```

## Data Flow

### Task Creation Flow

```
User Input (Discord/File) 
    ↓
Communications Agent
    ↓
tasks/inbox/task_123.md
    ↓
File Watcher (Orchestrator)
    ↓
Project Manager Agent
    ↓
tasks/backlog/task_123.md
    ↓
Sprint Planning
    ↓
tasks/sprint/task_123.md
    ↓
Development Agent
    ↓
tasks/done/task_123.md
```

### Provider Selection Flow

```
Agent Request
    ↓
Router (check role config)
    ↓
Try Provider 1 (check availability)
    ↓ (if fails)
Try Provider 2 (check availability)
    ↓ (if fails)
Try Provider 3...
    ↓
Return Response or Error
```

## File System Layout

```
nexus-cli/
├── agents/                     # Agent implementations
│   ├── communications/
│   ├── project_manager/
│   ├── senior_dev/
│   ├── junior_dev/
│   └── release_qa/
├── config/                     # Configuration files
│   ├── settings.toml
│   ├── roles.yaml
│   └── models.yaml
├── connectors/                 # External integrations
│   ├── discord/
│   ├── providers/
│   └── vault/
├── core/                       # Core system components
│   ├── config.py
│   ├── orchestrator.py
│   ├── queue.py
│   ├── router.py
│   └── task.py
├── tasks/                      # Task queue directories
│   ├── inbox/
│   ├── backlog/
│   ├── sprint/
│   └── done/
├── docs/                       # Documentation
├── releases/                   # Release documentation
├── utils/                      # Utility functions
├── tests/                      # Test suite
└── vault/                      # Local vault for feedback
```

## Security Considerations

### API Key Management
- All API keys stored in environment variables
- No credentials in configuration files or logs
- Support for `.env` file with clear documentation

### Input Validation
- Task content sanitized before processing
- File path validation to prevent traversal attacks
- Discord input validation and rate limiting

### Provider Security
- Each provider runs in isolated context
- Timeout handling for provider requests
- Error handling prevents information leakage

## Performance Characteristics

### File System Performance
- Optimized for small to medium task volumes (< 10,000 tasks)
- Efficient directory scanning with glob patterns
- Minimal file I/O through caching

### Memory Usage
- Low memory footprint (~50MB base)
- Task objects loaded on-demand
- Provider connection pooling

### Scalability Limits
- File system-based: suitable for single-user/small team
- Provider rate limits managed automatically
- Concurrent task processing limited by agent design

## Extension Points

### Adding New Providers
1. Implement `BaseProvider` interface
2. Add provider class to `connectors/providers/`
3. Update router provider mapping
4. Configure in `models.yaml`

### Adding New Agents
1. Create agent directory under `agents/`
2. Implement main agent logic
3. Add role configuration to `roles.yaml`
4. Update orchestrator routing if needed

### Adding New Integrations
1. Create connector under `connectors/`
2. Implement integration logic
3. Add configuration to `settings.toml`
4. Update orchestrator if automatic sync needed

## Error Handling

### Provider Failures
- Automatic fallback to next provider in chain
- Graceful degradation when all providers fail
- User notification through rich console output

### File System Errors
- Robust file handling with proper exception catching
- Automatic directory creation
- Backup and recovery procedures

### Agent Failures
- Task remains in current state if agent fails
- Error logging with context
- Manual recovery procedures documented

## Monitoring and Debugging

### Logging
- Rich console output with color coding
- Structured activity logging in task files
- Optional file-based logging

### Task Tracking
- Complete audit trail in task activity logs
- Queue state transitions tracked
- Agent processing history maintained

### System Status
- Real-time queue counts
- Provider availability monitoring
- Discord status command for quick overview

## Testing Strategy

### Unit Tests
- Core functionality (queue operations, task models)
- Provider implementations
- Configuration loading

### Integration Tests
- End-to-end task workflows
- Provider fallback logic
- File system operations

### Manual Testing
- Discord bot commands
- File watching behavior
- Agent coordination

## Future Enhancements

### Planned Features
- Web UI for task management
- Advanced analytics and reporting
- Real-time collaboration features
- Mobile app integration

### Scalability Improvements
- Database backend option
- Distributed agent processing
- Cloud provider integrations

### AI Enhancements
- Better task breakdown algorithms
- Automated code review
- Intelligent priority assignment

---

This architecture provides a solid foundation for the Nexus CLI system while maintaining flexibility for future enhancements and modifications.