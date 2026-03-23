"""
Dione AI — Hook Lifecycle System

Manages the execution of lifecycle hooks with priority ordering
and merge strategies. Inspired by OpenClaw's typed hook system.

Hook execution:
  - Void hooks (ON_*): run in parallel, fire-and-forget
  - Result hooks (BEFORE_*, AFTER_*): run sequentially by priority
  - Merge strategies determine how multiple handler results combine
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Optional
from loguru import logger

from server.plugins.types import (
    HookEvent, HookContext, HookRegistration,
    MergeStrategy, HOOK_MERGE_STRATEGIES,
)


class HookRunner:
    """
    Manages hook registration and execution with priority and merge strategies.
    
    Usage:
        runner = HookRunner()
        runner.register(HookEvent.BEFORE_CHAT, handler, "my_plugin", priority=50)
        result = await runner.run(HookEvent.BEFORE_CHAT, context)
    """
    
    def __init__(self):
        self._hooks: dict[HookEvent, list[HookRegistration]] = defaultdict(list)
        self._execution_log: list[dict] = []
    
    def register(
        self,
        event: HookEvent,
        handler: Any,
        plugin_id: str,
        priority: int = 100,
    ) -> None:
        """Register a hook handler for an event."""
        registration = HookRegistration(
            event=event,
            handler=handler,
            plugin_id=plugin_id,
            priority=priority,
        )
        self._hooks[event].append(registration)
        # Keep sorted by priority (lower = runs first)
        self._hooks[event].sort(key=lambda h: h.priority)
        logger.debug(f"Hook registered: {event.value} by {plugin_id} (priority={priority})")
    
    def unregister(self, event: HookEvent, plugin_id: str) -> int:
        """Remove all hooks for a plugin on a given event. Returns count removed."""
        before = len(self._hooks[event])
        self._hooks[event] = [
            h for h in self._hooks[event] if h.plugin_id != plugin_id
        ]
        removed = before - len(self._hooks[event])
        if removed:
            logger.debug(f"Unregistered {removed} hooks for {plugin_id} on {event.value}")
        return removed
    
    def unregister_plugin(self, plugin_id: str) -> int:
        """Remove all hooks for a plugin across all events."""
        total = 0
        for event in HookEvent:
            total += self.unregister(event, plugin_id)
        return total
    
    async def run(
        self,
        event: HookEvent,
        context: HookContext,
    ) -> Any:
        """
        Execute all hooks for an event with the appropriate merge strategy.
        
        Returns:
            Merged result based on the event's merge strategy,
            or None if no handlers are registered.
        """
        handlers = [h for h in self._hooks.get(event, []) if h.enabled]
        if not handlers:
            return None
        
        strategy = HOOK_MERGE_STRATEGIES.get(event, MergeStrategy.ALL_RESULTS)
        
        # Void events (ON_*) → fire all in parallel
        if event.value.startswith("on_"):
            await self._run_parallel(handlers, context, event)
            return None
        
        # Result events → run sequentially with merge
        return await self._run_sequential(handlers, context, event, strategy)
    
    async def _run_parallel(
        self,
        handlers: list[HookRegistration],
        context: HookContext,
        event: HookEvent,
    ) -> None:
        """Run void hooks in parallel (fire-and-forget)."""
        tasks = []
        for reg in handlers:
            tasks.append(self._safe_execute(reg, context, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_sequential(
        self,
        handlers: list[HookRegistration],
        context: HookContext,
        event: HookEvent,
        strategy: MergeStrategy,
    ) -> Any:
        """Run result hooks sequentially and merge results."""
        results = []
        
        for reg in handlers:
            result = await self._safe_execute(reg, context, event)
            if result is not None:
                results.append(result)
                
                # Short-circuit for FIRST_WINS
                if strategy == MergeStrategy.FIRST_WINS:
                    return result
                
                # Short-circuit for ANY_BLOCKS
                if strategy == MergeStrategy.ANY_BLOCKS:
                    if isinstance(result, dict) and result.get("blocked"):
                        return result
        
        if not results:
            return None
        
        return self._merge_results(results, strategy)
    
    async def _safe_execute(
        self,
        reg: HookRegistration,
        context: HookContext,
        event: HookEvent,
    ) -> Any:
        """Execute a single hook handler with error handling."""
        try:
            if asyncio.iscoroutinefunction(reg.handler):
                result = await reg.handler(context)
            else:
                result = reg.handler(context)
            
            self._execution_log.append({
                "event": event.value,
                "plugin_id": reg.plugin_id,
                "success": True,
                "timestamp": context.timestamp.isoformat(),
            })
            return result
            
        except Exception as e:
            logger.error(
                f"Hook {event.value} from {reg.plugin_id} failed: {e}"
            )
            self._execution_log.append({
                "event": event.value,
                "plugin_id": reg.plugin_id,
                "success": False,
                "error": str(e),
                "timestamp": context.timestamp.isoformat(),
            })
            return None
    
    def _merge_results(self, results: list, strategy: MergeStrategy) -> Any:
        """Merge multiple hook results based on strategy."""
        if strategy == MergeStrategy.FIRST_WINS:
            return results[0] if results else None
        
        if strategy == MergeStrategy.LAST_WINS:
            return results[-1] if results else None
        
        if strategy == MergeStrategy.CONCATENATE:
            return "\n".join(str(r) for r in results if r)
        
        if strategy == MergeStrategy.MERGE_DICTS:
            merged = {}
            for r in results:
                if isinstance(r, dict):
                    merged = self._deep_merge(merged, r)
            return merged
        
        if strategy == MergeStrategy.ALL_RESULTS:
            return results
        
        if strategy == MergeStrategy.ANY_BLOCKS:
            for r in results:
                if isinstance(r, dict) and r.get("blocked"):
                    return r
            return results[-1] if results else None
        
        return results
    
    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        merged = base.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = HookRunner._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def get_registered_hooks(self) -> dict[str, list[dict]]:
        """Get a summary of all registered hooks."""
        summary = {}
        for event, registrations in self._hooks.items():
            if registrations:
                summary[event.value] = [
                    {
                        "plugin_id": r.plugin_id,
                        "priority": r.priority,
                        "enabled": r.enabled,
                    }
                    for r in registrations
                ]
        return summary
    
    def get_execution_log(self, limit: int = 50) -> list[dict]:
        """Get recent hook execution log entries."""
        return self._execution_log[-limit:]
    
    @property
    def total_hooks(self) -> int:
        """Total number of registered hooks."""
        return sum(len(handlers) for handlers in self._hooks.values())
