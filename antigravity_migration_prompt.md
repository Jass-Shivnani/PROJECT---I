# Antigravity Master Prompt: Safe Upgrade & File Integration Runbook for Dione AI

Copy and paste the entire prompt below into **Antigravity** (alongside the extracted `dione-autonomous-agent-upgraded.zip` folder or inside your existing `dione` workspace). It instructs the agent to apply every upgrade deterministically while preserving your `.env` secrets, local knowledge graph, memory databases, and native Windows binaries.

## Prompt to Paste into Antigravity

You are upgrading the **Dione AI** sovereign desktop & multi-service agent project in-place from the upgraded archive (`dione-autonomous-agent-upgraded.zip`). Your top priority is **100% project integrity**: you must apply all backend, integration, and frontend upgrades without breaking existing native binaries, user data, or environment credentials.

### 1. Golden Integrity Rules (Strict Guardrails)

1. **Never Overwrite User Data or Auth State:** Do NOT delete or overwrite `data/knowledge/graph.json`, `data/social/dossiers.json`, `data/memory/`, `data/vectors/`, `data/credentials/`, or `data/whatsapp_auth/`.

2. **Never Touch Native CUA / Win32 Binaries:** Leave `cua-driver.exe`, `cua-driver-uia.exe`, `cua_driver_sdk.dll`, `cua-cursor-theme.exe`, and `server/bin/*.exe` intact.

3. **Preserve Existing API Keys in `.env`:** Do NOT overwrite `.env` with `.env.example`. Instead, preserve the user's existing `DIONE_LLM_API_KEY`, `DIONE_TELEGRAM_BOT_TOKEN`, and other secrets while stripping trailing inline `# comments` from unquoted values and setting `DIONE_LLM_MODEL=gemini-3.5-flash-lite`.

4. **Enforce `AGENTS.md` Zero-Mock Policy:** Do not introduce mock returns, placeholder stubs, or hardcoded user paths (`C:\Users\...`). Keep all 124+ Python modules and 24 React TypeScript modules syntactically valid.

### 2. Exact File Placement & Action Matrix

Apply the files from the upgraded package into the active project root according to this exact manifest:

| Action | Relative Path from Project Root | Architectural Purpose & Integrity Check | 
| ----- | ----- | ----- | 
| **DELETE** | `server/plugins/integrations.py` | Removes legacy monolithic file that was shadowed by the `server/plugins/integrations/` package. | 
| **CREATE** | `server/plugins/integrations/google_oauth.py` | Unified Google OAuth2 SSO manager (`gmail`, `calendar`, `drive`, `photos` scopes + auto-refresh). | 
| **CREATE** | `server/bin/dione_research_benchmark.py` | Zero-mock empirical benchmark & telemetry suite for the research paper. | 
| **CREATE** | `docs/dione_research_paper.tex` | Self-contained LaTeX academic research paper (`lualatex`-verified). | 
| **CREATE** | `docs/dione_research_paper.pdf` | Compiled 7-page academic research paper PDF. | 
| **UPDATE** | `server/plugins/integrations/base.py` | Updates `CredentialVault` to check `data/credentials/{id}.json`, `google_unified.json`, and legacy `data/integrations/`. | 
| **UPDATE** | `server/plugins/integrations/google_mail.py` | Adds dual Unified Google OAuth2 (Gmail API v1) + IMAP/SMTP App Password support and contact resolution. | 
| **UPDATE** | `server/plugins/integrations/google_calendar.py` | Fixes missing `timedelta` import and implements live Google Calendar v3 (`list_events`, `create_event`, `delete_event`). | 
| **UPDATE** | `server/plugins/integrations/google_drive.py` | Fixes `timedelta`/`io` imports, exports Docs/Sheets/Slides text, and adds `upload_file`. | 
| **UPDATE** | `server/plugins/integrations/google_photos.py` | Fixes `timedelta` import and implements Google Photos Library v1 API (`search_photos`, `get_memories`). | 
| **UPDATE** | `server/plugins/integrations/slack.py` | Adds `#channel-name` to ID resolution (`conversations.list`), `slack_channels`, `slack_send`, and `slack_read`. | 
| **UPDATE** | `server/plugins/integrations/instagram.py` | Fixes `IntegrationCredentials(integration_id=...)` bug and wires `instagram_profile` and `instagram_posts`. | 
| **UPDATE** | `server/plugins/integrations/whatsapp.py` | Resolves contact names to phone numbers via `SocialIntelligenceEngine` before calling Baileys bridge. | 
| **UPDATE** | `server/plugins/integrations/registry.py` | Adds `connect_google_unified()`, `initialize_saved_connections()`, complete `_dispatch_tool()` for all 8 services, and `get_dione_tools_map()` with sorted `inspect.Signature` parameters. | 
| **UPDATE** | `server/plugins/builtin/email_plugin.py` | Connects `EmailPlugin` to `CredentialVault` and `GoogleMailIntegration` (OAuth2 + SMTP + browser fallback). | 
| **UPDATE** | `server/plugins/registry.py` | Adds `list_tools()` and `get_tool()` required by `/api/plugins/*`. | 
| **UPDATE** | `server/config/settings.py` | Sets default backend to `gemini` and default model to `gemini-3.5-flash-lite`. | 
| **UPDATE** | `server/llm/failover.py` | Implements Google AI Studio Free-Tier & AI Pro Trial failover chain (`gemini-3.5-flash-lite` $\to$ `gemini-3.1-flash-lite` $\to$ `gemini-2.5-flash-lite` $\to$ `gemini-3.8-flash` $\to$ `gemini-2.5-flash` $\to$ `gemini-2.5-pro`). | 
| **UPDATE** | `server/llm/gemini.py` | Aligns fallback model list with valid Google AI Studio free-tier models. | 
| **UPDATE** | `server/core/safety.py` | Implements Intent-Aware 5-Tier Poset Permission Lattice (`allowed=False, needs_confirmation=True` on Tier 4) and blocks unprompted indirect-injection sends. | 
| **UPDATE** | `server/core/engine.py` | Resets `loop_detector` per turn, merges all 24 integration tools + `plan_task_workflow` into `_prepare_callable_tools()`, fixes `RuntimeEvent(sender="SafetyKernel")`, and wires `failover_manager`. | 
| **UPDATE** | `server/core/orchestrator.py` | Adds `set_integrations()`, updates `infer_agent_role()` for all 8 services, and passes `model_override`. | 
| **UPDATE** | `server/core/runtime/computer_use.py` | Guards `ctypes.windll` for cross-platform import safety. | 
| **UPDATE** | `server/knowledge/graph.py` | Adds `save()`, `get_statistics()`, `get_entities_by_type()`, `get_connections()`, and `search_entities()`. | 
| **UPDATE** | `server/memory/manager.py` | Upgrades `recall()` with lexical keyword boosting and MMR-style diversity deduplication. | 
| **UPDATE** | `server/api/app.py` | Calls `await integrations.initialize_saved_connections()` and `engine.set_integrations(integrations)` on startup. | 
| **UPDATE** | `server/api/routes/integrations.py` | Adds `POST /api/integrations/google/connect`, `/verify-all`, and `/execute-tool`. | 
| **UPDATE** | `server/api/routes/knowledge.py` | Fixes `kg.graph` attribute access, `await kg.query_relevant()`, and entity/relation creation. | 
| **UPDATE** | `server/api/routes/plugins.py` | Exposes both built-in plugin tools and integration tools without `AttributeError`. | 
| **UPDATE** | `server/api/routes/chat.py` | Removes duplicate `memory.add_turn("user", ...)` and wires WebSocket confirmation approval (`engine.approve_action`). | 
| **UPDATE** | `server/api/routes/channels.py` | Passes persistent `conversation_id="whatsapp_..."` and removes duplicate memory turn recording. | 
| **UPDATE** | `server/api/routes/ag_ui.py` | Passes `input_data.parameters.get("model")` as `model_override` to `stream_orchestrated_goal`. | 
| **UPDATE** | `server/telegram/__init__.py` | Passes persistent `conversation_id=f"telegram_{chat_id}"` to `engine.process_message()`. | 
| **UPDATE** | `client/src/services/api.ts` | Adds `model` parameter to `runAgUiAgentStream` and adds REST helpers for `fetchIntegrations`, `connectUnifiedGoogle`, `connectIntegration`, `disconnectIntegration`, `syncIntegration`, and `fetchWhatsAppQr`. | 
| **UPDATE** | `client/src/services/toolActionResolver.tsx` | Adds semantic UI badges and titles for `plan_task_workflow`, Gmail, Calendar, Drive, Photos, WhatsApp, Telegram, Slack, and Instagram tools. | 
| **UPDATE** | `client/src/components/ChatHeader.tsx` | Updates header model selector with AI Studio Free-Tier & AI Pro Trial models. | 
| **UPDATE** | `client/src/components/SettingsModal.tsx` | Adds the **Integrations (8)** tab with 1-click Unified Google OAuth2 SSO, credential forms, WhatsApp QR display, and live status controls. | 
| **UPDATE** | `client/src/App.tsx` | Passes `activeModel` into `runAgUiAgentStream`. | 

### 3. Step-by-Step Execution Protocol for Antigravity

Execute the following 5 steps sequentially in the terminal and verify each step succeeds before moving to the next:

#### Step 1: Pre-Flight Backup of User State

Before modifying any files, create a timestamped backup of `.env` and `data/`:

```
New-Item -ItemType Directory -Force -Path ".\backup_pre_upgrade"
if (Test-Path ".\.env") { Copy-Item ".\.env" ".\backup_pre_upgrade\.env.bak" -Force }
if (Test-Path ".\data") { Copy-Item ".\data" ".\backup_pre_upgrade\data_backup" -Recurse -Force }

```

#### Step 2: Remove Shadowed Legacy File & Copy Upgraded Source Files

1. Delete `server\plugins\integrations.py` if it exists so Python cleanly resolves the `server\plugins\integrations\` package:

```
if (Test-Path ".\server\plugins\integrations.py") { Remove-Item ".\server\plugins\integrations.py" -Force }

```

2. Copy the `server/`, `client/src/`, and `docs/` directories from the extracted `dione-autonomous-agent-upgraded/dione/` folder into the workspace root (do **not** overwrite `.env` or `data/`).

#### Step 3: Sanitize `.env` Without Losing Existing Secrets

Run this Python snippet to strip trailing inline `# comments` from `.env` values while preserving all existing API keys:

```
python -c "import re; from pathlib import Path; p = Path('.env'); lines = p.read_text(encoding='utf-8').splitlines() if p.exists() else []; out = []; [out.append(f'{k.strip()}={re.sub(r\"\s+#.*$\", \"\", v).strip()}') if (line.strip() and not line.strip().startswith('#') and '=' in line and (k := line.split('=',1)[0]) and (v := line.split('=',1)[1]) is not None) else out.append(line) for line in lines]; p.write_text('\n'.join(out) + '\n', encoding='utf-8') if p.exists() else None; print('Sanitized .env successfully')"

```

#### Step 4: Verify Backend Compilation, Tool Signatures & Empirical Benchmarks

Run these two verification commands to confirm zero syntax errors, zero `inspect.Signature` ordering errors, and 100% safety/knapsack/graph health:

```
python -c "import py_compile, glob; files = glob.glob('server/**/*.py', recursive=True); [py_compile.compile(f, doraise=True) for f in files]; print(f'Compiled {len(files)} Python modules cleanly!')"
python server/bin/dione_research_benchmark.py --output data/benchmark_results.json

```

#### Step 5: Rebuild the React Frontend Bundle (`client/dist`)

Compile the updated TypeScript/React components (`SettingsModal.tsx`, `ChatHeader.tsx`, `App.tsx`, `api.ts`, `toolActionResolver.tsx`) so FastAPI serves the updated UI on port `8900`:

```
cd client
npm install
npm run build
cd ..

```

Once all 5 steps pass with zero errors, report the summary of updated modules and benchmark output.