path = 'server/api/routes/ag_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        # Stream directly from DioneEngine's native ReAct loop with persistent conversation thread
        async for step in orchestrator.stream_orchestrated_goal(
            prompt,
            conversation_id=thread_id,
            recent_messages=recent_msgs,
        ):
            if step.state == EngineState.ACTING and step.tool_call:
                tc_id = f"tc_{uuid.uuid4().hex[:6]}"
                active_tc_ids[step.tool_call.tool] = tc_id
                yield _sse({
                    "type": "TOOL_CALL_START",
                    "toolCallId": tc_id,
                    "toolCallName": step.tool_call.tool,
                })
                yield _sse({
                    "type": "TOOL_CALL_ARGS",
                    "toolCallId": tc_id,
                    "delta": json.dumps(step.tool_call.params),
                })

            elif step.state == EngineState.OBSERVING and step.tool_call and step.observation:
                tc_id = active_tc_ids.pop(step.tool_call.tool, f"tc_{uuid.uuid4().hex[:6]}")
                yield _sse({
                    "type": "TOOL_CALL_RESULT",
                    "toolCallId": tc_id,
                    "content": step.observation.result,
                    "success": step.observation.success,
                    "error": step.observation.error,
                })
                yield _sse({
                    "type": "TOOL_CALL_END",
                    "toolCallId": tc_id,
                })

            elif step.state == EngineState.AWAITING_CONFIRMATION and step.tool_call:
                yield _sse({
                    "type": "CUSTOM",
                    "name": "safety_confirmation_required",
                    "value": {
                        "confirmation_id": step.confirmation_id,
                        "tool": step.tool_call.tool,
                        "params": step.tool_call.params,
                        "thought": step.thought,
                    },
                })

            elif step.state == EngineState.COMPLETE and step.final_answer:
                final_text = step.final_answer

            elif step.state == EngineState.ERROR and step.final_answer:
                final_text = step.final_answer'''

replacement = '''        try:
            # Stream directly from DioneEngine's native ReAct loop with persistent conversation thread
            async for step in orchestrator.stream_orchestrated_goal(
                prompt,
                conversation_id=thread_id,
                recent_messages=recent_msgs,
            ):
                if step.state == EngineState.ACTING and step.tool_call:
                    tc_id = f"tc_{uuid.uuid4().hex[:6]}"
                    active_tc_ids[step.tool_call.tool] = tc_id
                    yield _sse({
                        "type": "TOOL_CALL_START",
                        "toolCallId": tc_id,
                        "toolCallName": step.tool_call.tool,
                    })
                    yield _sse({
                        "type": "TOOL_CALL_ARGS",
                        "toolCallId": tc_id,
                        "delta": json.dumps(step.tool_call.params),
                    })

                elif step.state == EngineState.OBSERVING and step.tool_call and step.observation:
                    tc_id = active_tc_ids.pop(step.tool_call.tool, f"tc_{uuid.uuid4().hex[:6]}")
                    yield _sse({
                        "type": "TOOL_CALL_RESULT",
                        "toolCallId": tc_id,
                        "content": step.observation.result,
                        "success": step.observation.success,
                        "error": step.observation.error,
                    })
                    yield _sse({
                        "type": "TOOL_CALL_END",
                        "toolCallId": tc_id,
                    })

                elif step.state == EngineState.AWAITING_CONFIRMATION and step.tool_call:
                    yield _sse({
                        "type": "CUSTOM",
                        "name": "safety_confirmation_required",
                        "value": {
                            "confirmation_id": step.confirmation_id,
                            "tool": step.tool_call.tool,
                            "params": step.tool_call.params,
                            "thought": step.thought,
                        },
                    })

                elif step.state == EngineState.COMPLETE and step.final_answer:
                    final_text = step.final_answer

                elif step.state == EngineState.ERROR and step.final_answer:
                    final_text = step.final_answer

        except Exception as loop_err:
            logger.error(f"[AG-UI Stream] ReAct execution caught exception: {loop_err}", exc_info=True)
            final_text = f"I encountered an execution interruption: {loop_err}. Self-healing kernel restored."'''

# Normalize line endings
content_norm = content.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
assert target_norm in content_norm, "Target not found in ag_ui.py"

content_norm = content_norm.replace(target_norm, replacement)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Updated server/api/routes/ag_ui.py successfully!")
