# -*- coding: utf-8 -*-
"""
AI Snapshot Generator for browser automation.

Generates accessibility-tree based snapshots that are optimized for LLM consumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


@dataclass
class RefInfo:
    """Information about a referenced element."""
    role: str
    name: str | None = None
    nth: int | None = None
    selector: str | None = None


@dataclass
class AISnapshot:
    """Result of AI snapshot generation."""
    snapshot: str
    refs: dict[str, RefInfo]
    truncated: bool = False
    element_count: int = 0


class AISnapshotGenerator:
    """
    Generates AI-friendly page snapshots using accessibility tree.
    
    The snapshot format is optimized for LLM consumption:
    - Hierarchical structure with indentation
    - Element references for precise interaction
    - Selector hints for fallback interaction
    """
    
    MAX_CHARS = 50000
    MAX_ELEMENTS = 500
    
    async def generate(self, page: Page) -> AISnapshot:
        """
        Generate an AI snapshot from a Playwright page.
        
        Args:
            page: Playwright page object
            
        Returns:
            AISnapshot with structured content and element references
        """
        accessibility_tree = await page.accessibility.snapshot()
        
        if not accessibility_tree:
            return AISnapshot(
                snapshot="(Empty page - no accessibility tree)",
                refs={},
                truncated=False,
                element_count=0,
            )
        
        snapshot_lines, refs = self._format_tree(accessibility_tree)
        
        snapshot = "\n".join(snapshot_lines)
        truncated = len(snapshot) > self.MAX_CHARS
        
        if truncated:
            snapshot = snapshot[:self.MAX_CHARS] + "\n\n[...TRUNCATED - page too large]"
        
        return AISnapshot(
            snapshot=snapshot,
            refs=refs,
            truncated=truncated,
            element_count=len(refs),
        )
    
    def _format_tree(
        self,
        node: dict,
        depth: int = 0,
        refs: dict | None = None,
        counter: list | None = None,
    ) -> tuple[list[str], dict]:
        """
        Recursively format accessibility tree nodes.
        
        Args:
            node: Accessibility tree node
            depth: Current depth for indentation
            refs: Accumulated refs dictionary
            counter: Element counter
            
        Returns:
            Tuple of (formatted lines, refs dict)
        """
        if refs is None:
            refs = {}
        if counter is None:
            counter = [0]
        
        lines = []
        indent = "  " * depth
        
        role = node.get("role", "unknown")
        name = node.get("name", "")
        
        if role == "generic" and not name and not node.get("children"):
            return lines, refs
        
        counter[0] += 1
        ref_key = f"ref{counter[0]}"
        
        selector_hint = self._generate_selector_hint(node)
        
        refs[ref_key] = RefInfo(
            role=role,
            name=name if name else None,
            selector=selector_hint,
        )
        
        if name:
            display_name = name[:100] + "..." if len(name) > 100 else name
            lines.append(f"{indent}- {role} \"{display_name}\" [ref={ref_key}]")
        else:
            lines.append(f"{indent}- {role} [ref={ref_key}]")
        
        for child in node.get("children", []):
            child_lines, _ = self._format_tree(child, depth + 1, refs, counter)
            lines.extend(child_lines)
        
        return lines, refs
    
    def _generate_selector_hint(self, node: dict) -> str | None:
        """
        Generate a CSS selector hint for the node.
        
        Priority:
        1. id attribute
        2. aria-label attribute
        3. placeholder attribute
        4. role + name combination
        """
        if node.get("id"):
            return f"#{node['id']}"
        
        if node.get("aria-label"):
            return f"[aria-label=\"{node['aria-label']}\"]"
        
        if node.get("placeholder"):
            return f"[placeholder=\"{node['placeholder']}\"]"
        
        role = node.get("role", "")
        name = node.get("name", "")
        if role and name:
            escaped_name = name.replace('"', '\\"')[:50]
            return f"{role}: \"{escaped_name}\""
        
        return None
