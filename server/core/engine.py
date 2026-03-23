"""
Dione AI — Core Orchestration Engine (ReAct Loop)

The engine implements the Reason-Act-Observe cycle:
1. User sends a message
2. Context is enriched (RAG + Knowledge Graph + Sentiment)
3. LLM reasons and outputs a structured tool call (or final answer)
4. Tool call is validated by the Safety Kernel
5. Plugin executes the tool
6. Result is fed back as an Observation
7. Loop continues until task is complete
"""

import json
import asyncio
from typing import Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from server.config import get_settings
from server.core.context import ContextManager
from server.core.safety import SafetyKernel
from server.plugins.permissions import PermissionManager


class EngineState(Enum):
    """Current state of the engine's ReAct loop."""
    IDLE = "idle"
    REASONING = "reasoning"
    ACTING = "acting"
    OBSERVING = "observing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ToolCall:
    """A structured tool call produced by the LLM."""
    tool: str           # e.g., "WhatsAppPlugin.fetch_media"
    params: dict        # e.g., {"file_type": "pdf", "limit": 1}
    reasoning: str = "" # The LLM's reasoning for this call


@dataclass
class Observation:
    """Result of a tool execution, fed back to the LLM."""
    tool: str
    success: bool
    result: str
    error: Optional[str] = None


@dataclass
class EngineStep:
    """A single step in the ReAct loop."""
    step_number: int
    state: EngineState
    thought: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    observation: Optional[Observation] = None
    final_answer: Optional[str] = None


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    role: str       # "user", "assistant", "system", "observation"
    content: str
    metadata: dict = field(default_factory=dict)


class DioneEngine:
    """
    The Dione Orchestration Engine.
    
    Implements the ReAct (Reason + Act) loop that connects
    the local LLM to the plugin system through structured
    tool calls.
    """

    MAX_STEPS = 10  # Maximum ReAct iterations before forcing a stop

    def __init__(self):
        self.settings = get_settings()
        self.state = EngineState.IDLE
        self.context_manager = ContextManager()
        self.safety_kernel = SafetyKernel()
        self.permission_manager = PermissionManager()
        
        # These will be injected after initialization
        self._llm_adapter = None
        self._plugin_registry = None
        self._knowledge_graph = None
        self._sentiment_engine = None
        self._memory_manager = None
        self._profile_manager = None
        self._personality_engine = None
        self._heartbeat = None
        self._ui_builder = None

        self._conversation_history: list[ConversationMessage] = []
        self._current_steps: list[EngineStep] = []

        logger.info("🌙 Dione Engine initialized")

    # ------------------------------------------------------------------
    # Dependency injection
    # ------------------------------------------------------------------

    def set_llm(self, llm_adapter):
        """Inject the LLM adapter."""
        self._llm_adapter = llm_adapter
        logger.info(f"LLM adapter set: {llm_adapter.__class__.__name__}")

    def set_plugins(self, plugin_registry):
        """Inject the plugin registry."""
        self._plugin_registry = plugin_registry
        logger.info(f"Plugin registry set: {len(plugin_registry.tools)} tools loaded")

    def set_knowledge_graph(self, knowledge_graph):
        """Inject the knowledge graph."""
        self._knowledge_graph = knowledge_graph
        logger.info("Knowledge graph connected")

    def set_sentiment_engine(self, sentiment_engine):
        """Inject the sentiment engine."""
        self._sentiment_engine = sentiment_engine
        logger.info("Sentiment engine connected")

    def set_memory_manager(self, memory_manager):
        """Inject the memory manager."""
        self._memory_manager = memory_manager
        logger.info("Memory manager connected")

    def set_profile_manager(self, profile_manager):
        """Inject the user profile manager."""
        self._profile_manager = profile_manager
        logger.info(f"Profile manager connected — user: {profile_manager.profile.name}")

    def set_personality_engine(self, personality_engine):
        """Inject the personality engine."""
        self._personality_engine = personality_engine
        logger.info(f"Personality engine connected — mood: {personality_engine.mood.label}")

    def set_heartbeat(self, heartbeat):
        """Inject the heartbeat scheduler."""
        self._heartbeat = heartbeat
        logger.info("Heartbeat scheduler connected")

    def set_ui_builder(self, ui_builder):
        """Inject the UI directive builder."""
        self._ui_builder = ui_builder
        logger.info("UI directive builder connected")

    # ------------------------------------------------------------------
    # System prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """Build the system prompt with available tools, personality, and context."""
        tools_schema = []
        if self._plugin_registry:
            tools_schema = self._plugin_registry.get_tools_schema()

        tools_json = json.dumps(tools_schema, indent=2)

        # Personality directive — how Dione should behave for this user
        personality_directive = ""
        if self._profile_manager:
            personality_directive = self._profile_manager.get_personality_directive()
        
        # Mood directive — emotional tone for this interaction
        mood_directive = ""
        if self._personality_engine:
            mood_directive = self._personality_engine.get_mood_directive()

        # User context from profile
        user_context = ""
        if self._profile_manager:
            user_context = self._profile_manager.profile.to_context_string()

        # Proactive context — upcoming habits/patterns
        proactive_context = ""
        if self._heartbeat:
            proactive_context = self._heartbeat.get_proactive_context()

        # Emotional context from recent interactions
        emotional_context = ""
        if self._personality_engine:
            emotional_context = self._personality_engine.get_emotional_context()

        sections = [
            personality_directive or "You are Dione, a local AI assistant that can take actions on the user's computer.",
        ]

        if mood_directive:
            sections.append(f"\n## Current Mood\n{mood_directive}")

        if user_context:
            sections.append(f"\n## User Profile\n{user_context}")

        if emotional_context:
            sections.append(f"\n## Emotional Context\n{emotional_context}")

        if proactive_context:
            sections.append(f"\n## Proactive Awareness\n{proactive_context}")

        sections.append(f"""
## Available Tools

{tools_json}

## How to respond:

### When you need to use a tool:
Respond with a JSON object in this exact format:
```json
{{"thought": "your reasoning about what to do", "tool": "PluginName.method_name", "params": {{"key": "value"}}}}
```

### When you have the final answer:
Respond with a JSON object:
```json
{{"thought": "reasoning", "final_answer": "your response to the user"}}
```

## Rules:
1. ALWAYS respond with valid JSON. No other text.
2. Use tools to gather information and take actions.
3. After each tool result, reason about the next step.
4. If a tool fails, try an alternative approach.
5. If a task requires multiple steps, execute them one at a time.
6. NEVER make up tool names. Only use tools from the list above.
7. For destructive actions (delete, send, execute), explain what you're about to do.
8. Be concise in your final answers.
""")

        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Core ReAct Loop
    # ------------------------------------------------------------------

    async def process_message(self, user_message: str) -> AsyncGenerator[EngineStep, None]:
        """
        Process a user message through the ReAct loop.
        
        Yields EngineStep objects as the loop progresses,
        allowing real-time streaming to the client.
        """
        if not self._llm_adapter:
            raise RuntimeError("LLM adapter not set. Call set_llm() first.")

        self.state = EngineState.REASONING
        logger.info(f"Processing: {user_message[:100]}...")

        # Add user message to conversation history
        self._conversation_history.append(
            ConversationMessage(role="user", content=user_message)
        )

        # Step 1: Analyze sentiment of the user message
        sentiment_context = ""
        sentiment_label = "neutral"
        sentiment_urgency = 0.5
        if self._sentiment_engine and self.settings.sentiment.enabled:
            sentiment = await self._sentiment_engine.analyze(user_message)
            sentiment_label = sentiment.label
            sentiment_urgency = sentiment.urgency
            sentiment_context = f"\n[Sentiment: {sentiment.label}, urgency={sentiment.urgency:.2f}]"
            logger.debug(f"Sentiment: {sentiment}")

        # Step 1b: Personality reactions — Dione's emotional heartbeat
        if self._personality_engine:
            self._personality_engine.react_to_sentiment(sentiment_label, sentiment_urgency)
            self._personality_engine.react_to_time_of_day()
            self._personality_engine.remember_interaction(
                sentiment_label, user_message
            )

        # Step 1c: Learn about the user from this message
        if self._profile_manager:
            await self._profile_manager.learn_from_message(user_message, "user")

        # Step 2: Query knowledge graph for relevant context
        knowledge_context = ""
        if self._knowledge_graph:
            kg_results = await self._knowledge_graph.query_relevant(user_message)
            if kg_results:
                knowledge_context = f"\n[Knowledge Context: {kg_results}]"

        # Step 3: Retrieve relevant memories (RAG)
        memory_context = ""
        if self._memory_manager:
            memories = await self._memory_manager.recall(user_message)
            if memories:
                memory_context = f"\n[Relevant Memories: {memories}]"

        # Build enriched context
        enriched_message = f"{user_message}{sentiment_context}{knowledge_context}{memory_context}"

        # Step 4: Enter the ReAct loop
        step_number = 0
        self._current_steps = []

        while step_number < self.MAX_STEPS:
            step_number += 1
            self.state = EngineState.REASONING

            # Build messages for LLM
            messages = self._build_llm_messages(enriched_message)

            # Call LLM
            logger.debug(f"Step {step_number}: Calling LLM...")
            from server.llm.adapter import LLMRequest, LLMMessage
            llm_request = LLMRequest(
                messages=[LLMMessage(role=m["role"], content=m["content"]) for m in messages],
                temperature=self.settings.llm.temperature,
                max_tokens=self.settings.llm.max_tokens,
            )
            try:
                llm_resp = await self._llm_adapter.generate(llm_request)
                llm_response = llm_resp.content
            except Exception as llm_err:
                logger.error(f"LLM call failed at step {step_number}: {llm_err}")
                error_step = EngineStep(
                    step_number=step_number,
                    state=EngineState.ERROR,
                    final_answer=f"I'm having trouble reaching my language model right now. Error: {llm_err}",
                )
                self._current_steps.append(error_step)
                self.state = EngineState.ERROR
                yield error_step
                return

            # Parse the LLM response
            parsed = self._parse_llm_response(llm_response)

            if parsed is None:
                # LLM gave unparseable output — treat as final answer
                step = EngineStep(
                    step_number=step_number,
                    state=EngineState.COMPLETE,
                    final_answer=llm_response,
                )
                self._current_steps.append(step)
                yield step
                break

            # Check if this is a final answer
            if "final_answer" in parsed:
                step = EngineStep(
                    step_number=step_number,
                    state=EngineState.COMPLETE,
                    thought=parsed.get("thought", ""),
                    final_answer=parsed["final_answer"],
                )
                self._current_steps.append(step)
                
                # Store assistant response in conversation history
                self._conversation_history.append(
                    ConversationMessage(
                        role="assistant",
                        content=parsed["final_answer"]
                    )
                )

                # Update knowledge graph with new information
                if self._knowledge_graph:
                    await self._knowledge_graph.extract_and_store(
                        user_message, parsed["final_answer"]
                    )

                # Store in memory
                if self._memory_manager:
                    await self._memory_manager.add_turn(
                        "assistant", parsed["final_answer"]
                    )

                self.state = EngineState.COMPLETE
                yield step
                break

            # This is a tool call
            tool_call = ToolCall(
                tool=parsed.get("tool", ""),
                params=parsed.get("params", {}),
                reasoning=parsed.get("thought", ""),
            )

            # Validate through safety kernel
            self.state = EngineState.ACTING
            safety_check = self.safety_kernel.validate_tool_call(tool_call)

            if not safety_check.allowed:
                if safety_check.needs_confirmation:
                    # Yield a step asking for user confirmation
                    step = EngineStep(
                        step_number=step_number,
                        state=EngineState.AWAITING_CONFIRMATION,
                        thought=tool_call.reasoning,
                        tool_call=tool_call,
                    )
                    self._current_steps.append(step)
                    yield step
                    # TODO: Wait for user confirmation via WebSocket
                    continue
                else:
                    # Blocked entirely
                    observation = Observation(
                        tool=tool_call.tool,
                        success=False,
                        result="",
                        error=f"Blocked by safety kernel: {safety_check.reason}",
                    )
                    self._add_observation_to_history(observation)
                    step = EngineStep(
                        step_number=step_number,
                        state=EngineState.OBSERVING,
                        thought=tool_call.reasoning,
                        tool_call=tool_call,
                        observation=observation,
                    )
                    self._current_steps.append(step)
                    yield step
                    continue

            # Execute the tool
            logger.info(f"Executing tool: {tool_call.tool}")
            observation = await self._execute_tool(tool_call)

            # Personality reacts to tool result
            if self._personality_engine:
                self._personality_engine.react_to_tool_result(
                    observation.success, tool_call.tool
                )
            # Track tool usage in profile
            if self._profile_manager:
                self._profile_manager.record_tool_use(tool_call.tool)

            # Feed observation back into conversation
            self.state = EngineState.OBSERVING
            self._add_observation_to_history(observation)

            step = EngineStep(
                step_number=step_number,
                state=EngineState.OBSERVING,
                thought=tool_call.reasoning,
                tool_call=tool_call,
                observation=observation,
            )
            self._current_steps.append(step)
            yield step

        else:
            # Max steps exceeded
            step = EngineStep(
                step_number=step_number,
                state=EngineState.ERROR,
                final_answer="I wasn't able to complete this task within the step limit. Could you break it into smaller steps?",
            )
            self._current_steps.append(step)
            self.state = EngineState.ERROR
            yield step

        self.state = EngineState.IDLE

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_llm_messages(self, enriched_message: str) -> list[dict]:
        """Build the message list for the LLM."""
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        for msg in self._conversation_history:
            if msg.role == "observation":
                messages.append({
                    "role": "user",
                    "content": f"[Tool Result]: {msg.content}",
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        return messages

    def _parse_llm_response(self, response: str) -> Optional[dict]:
        """Parse the LLM's JSON response."""
        try:
            # Try direct JSON parse
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object in the response
        json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse LLM response as JSON: {response[:200]}")
        return None

    async def _execute_tool(self, tool_call: ToolCall) -> Observation:
        """Execute a tool call through the plugin registry."""
        if not self._plugin_registry:
            return Observation(
                tool=tool_call.tool,
                success=False,
                result="",
                error="No plugin registry available",
            )

        try:
            result = await self._plugin_registry.execute(
                tool_call.tool, tool_call.params
            )
            return Observation(
                tool=tool_call.tool,
                success=True,
                result=str(result),
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return Observation(
                tool=tool_call.tool,
                success=False,
                result="",
                error=str(e),
            )

    def _add_observation_to_history(self, observation: Observation):
        """Add a tool observation to the conversation history."""
        if observation.success:
            content = f"Tool '{observation.tool}' succeeded: {observation.result}"
        else:
            content = f"Tool '{observation.tool}' failed: {observation.error}"

        self._conversation_history.append(
            ConversationMessage(role="observation", content=content)
        )

    def reset_conversation(self):
        """Clear conversation history and start fresh."""
        self._conversation_history.clear()
        self._current_steps.clear()
        self.state = EngineState.IDLE
        logger.info("Conversation reset")

    def get_ui_directives(self, response_text: str, tools_used: list[str]) -> dict:
        """
        Generate UI directives to accompany a response.
        
        Returns a dict with theme + components that the Flutter app renders.
        """
        if not self._ui_builder:
            return {}

        mood_label = "balanced"
        if self._personality_engine:
            mood_label = self._personality_engine.mood.label

        profession = "unknown"
        if self._profile_manager:
            profession = self._profile_manager.profile.profession

        # Build theme
        theme = self._ui_builder.build_theme(mood_label, profession)

        # Build response components
        components = self._ui_builder.build_response_components(
            response_text=response_text,
            tools_used=tools_used,
            mood_label=mood_label,
        )

        return {
            "theme": theme.to_dict(),
            "components": [c.to_dict() for c in components],
            "mood": self._personality_engine.mood.to_dict() if self._personality_engine else {},
        }

    def get_alive_state(self) -> dict:
        """
        Get Dione's current 'alive' state — mood, profile awareness, etc.
        
        Used by the Flutter app to render the ambient experience.
        """
        state = {
            "engine_state": self.state.value,
            "conversation_length": len(self._conversation_history),
        }

        if self._personality_engine:
            pe = self._personality_engine
            state["mood"] = pe.mood.to_dict()
            state["greeting"] = pe.get_greeting_style()

        if self._profile_manager:
            p = self._profile_manager.profile
            state["user"] = {
                "name": p.name,
                "profession": p.profession,
                "expertise": p.expertise_level,
                "interests": p.interests[:5],
                "total_messages": p.total_messages,
            }

        if self._ui_builder and self._personality_engine:
            mood = self._personality_engine.mood.label
            profession = self._profile_manager.profile.profession if self._profile_manager else "unknown"
            theme = self._ui_builder.build_theme(mood, profession)
            state["theme"] = theme.to_dict()

        return state
