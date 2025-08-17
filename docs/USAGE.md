# Nexus CLI Usage Guide

## Discord Bot Setup

### Prerequisites

1. **Enable Developer Mode in Discord**
   - Go to Discord Settings (⚙️) → Advanced → Enable "Developer Mode"
   - This allows you to right-click on servers and channels to copy their IDs

2. **Create a Discord Application**
   - Visit [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name (e.g., "Nexus CLI")
   - Note down the **Application ID** from the General Information tab

3. **Create a Bot**
   - Go to the "Bot" tab in your application
   - Click "Add Bot" 
   - Copy the **Bot Token** (keep this secret!)
   - Enable "Message Content Intent" under Privileged Gateway Intents

4. **Invite Bot to Server**
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot` and `applications.commands`
   - Select bot permissions: `Send Messages`, `Use Slash Commands`, `Manage Webhooks`
   - Use the generated URL to invite the bot to your server

### Configuration

#### Required Environment Variables

Create a `.env` file (copy from `.env.example`) and configure:

```bash
# Required: Bot authentication
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_APP_ID=your_application_id_here

# Required: Server and channel configuration  
DISCORD_GUILD_ID=123456789012345678
DISCORD_COMMANDS_CHANNEL_ID=123456789012345678
DISCORD_UPDATES_CHANNEL_ID=123456789012345678

# Optional: Agent persona webhooks
COMMUNICATIONS_WEBHOOK_URL=https://discord.com/api/webhooks/...
PM_WEBHOOK_URL=https://discord.com/api/webhooks/...
SD_WEBHOOK_URL=https://discord.com/api/webhooks/...
JD_WEBHOOK_URL=https://discord.com/api/webhooks/...
RQE_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### Getting Discord IDs

1. **Guild (Server) ID**: Right-click your server name → "Copy Server ID"

2. **Channel IDs**: Right-click the channel → "Copy Channel ID"
   - `DISCORD_COMMANDS_CHANNEL_ID`: Channel where users can run `/idea`, `/feedback`, `/status`
   - `DISCORD_UPDATES_CHANNEL_ID`: Channel where agents post updates about tasks and releases

#### Optional: Agent Webhooks

For better agent personas (custom usernames/avatars), create webhooks:

1. Right-click your updates channel → "Edit Channel" → "Integrations" → "Webhooks"
2. Click "New Webhook"
3. Set name (e.g., "Communications Agent") and optionally upload an avatar
4. Copy the webhook URL
5. Add to your `.env` file

**Agent Webhook Mapping:**
- `COMMUNICATIONS_WEBHOOK_URL` → Communications Agent (📢)
- `PM_WEBHOOK_URL` → Project Manager (📋)  
- `SD_WEBHOOK_URL` → Senior Developer (👨‍💻)
- `JD_WEBHOOK_URL` → Junior Developer (👩‍💻)
- `RQE_WEBHOOK_URL` → Release QA (🔍)

If webhooks aren't configured, agents will post as the bot with prefixes like `[Communications Agent]`.

### Minimal Configuration Example

```toml
# config/settings.toml
[discord]
bot_token = "${DISCORD_BOT_TOKEN}"
app_id = "${DISCORD_APP_ID}"
guild_id = "123456789012345678"
commands_channel_id = "123456789012345678"  
updates_channel_id = "987654321098765432"

[discord.webhooks]
communications = "${COMMUNICATIONS_WEBHOOK_URL}"
# ... other webhooks optional
```

## Discord Commands

### `/idea <text>`
Submit a new development idea that gets converted into a task.

**Example:**
```
/idea Add dark mode toggle to the settings page
```

**Behavior:**
- Creates a task file in `tasks/inbox/`
- Replies ephemerally "Idea captured" with task ID
- Posts update in updates channel about new idea
- Only works in the configured commands channel and guild

### `/feedback <text>`
Submit feedback about the system.

**Example:**
```
/feedback The task creation process could be faster
```

**Behavior:**
- Saves feedback to `vault/inbox/feedback/`
- May create a task if feedback is substantial
- Replies ephemerally confirming receipt
- Only works in the configured commands channel and guild

### `/status`
Get current system status including task queue counts.

**Example:**
```
/status
```

**Behavior:**
- Shows queue counts (inbox, backlog, sprint, done)
- Shows orchestrator and provider status
- Replies ephemerally with status information
- Only works in the configured commands channel and guild

## Command Restrictions

- Commands **only work in the configured guild and commands channel**
- Commands from other servers or channels are rejected with an error message
- All command responses are ephemeral (only visible to the user who ran them)

## Agent Updates

Agents post updates to the updates channel when:
- New ideas are received (Communications Agent)
- Tasks are completed (various agents)
- Releases are created (Release QA Agent)
- Important system events occur

## Troubleshooting

### Bot Not Responding
1. Check bot token is correct and bot is online
2. Verify guild_id and channel IDs are correct (numbers, not names)
3. Ensure bot has proper permissions in the channels
4. Check logs with `make bot`

### Commands Not Appearing
1. Guild-scoped commands may take a few minutes to appear
2. Restart Discord client to refresh command cache
3. Check that app_id and guild_id are configured correctly

### Webhook Failures
1. Webhook URLs expire if the webhook is deleted
2. Webhooks must be in the same server as the bot
3. Bot will fallback to normal messages if webhooks fail

### Permission Issues
1. Bot needs "Send Messages" and "Use Slash Commands" permissions
2. For webhooks: bot needs "Manage Webhooks" permission
3. Channels must allow the bot to read and send messages

## Testing Setup

Run the test command to verify configuration:

```bash
make bot test
```

This will check:
- Bot token configuration
- Guild and channel ID configuration  
- Webhook configuration status
- Overall setup completeness