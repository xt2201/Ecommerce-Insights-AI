"""Utility functions for loading prompts from markdown and YAML files."""

from __future__ import annotations

import yaml
from functools import lru_cache
from pathlib import Path
from typing import Optional


# Base directory for prompts - centralized in ai_server/prompts
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@lru_cache(maxsize=10)
def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt from a markdown file in the prompts directory.
    Automatically injects 'system_identity.md' if {{SYSTEM_IDENTITY}} placeholder is present,
    or prepends it to 'System Prompt' sections.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        
    Returns:
        The content of the prompt file as a string
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    content = prompt_path.read_text(encoding="utf-8")
    
    # Mixin Injection: System Identity
    # We try to load the identity file. If it exists, we inject it.
    identity_path = PROMPTS_DIR / "system_identity.md"
    if identity_path.exists():
        identity_content = identity_path.read_text(encoding="utf-8")
        
        # Strategy 1: Explicit Placeholder
        if "{{SYSTEM_IDENTITY}}" in content:
            content = content.replace("{{SYSTEM_IDENTITY}}", identity_content)
            
        # Strategy 2: Implicit Prepend to System Prompt sections
        # This is a heuristic to ensure identity is present even if not explicitly requested
        # We look for "## System Prompt" and inject the identity after it
        elif "## System Prompt" in content and "XT AI Shopping Assistant" not in content:
            # Only inject if not already present (to avoid double injection if file was manually updated)
            content = content.replace("## System Prompt", f"## System Prompt\n\n{identity_content}\n")
            
    return content


def get_prompt_section(prompt_content: str, section_name: str) -> Optional[str]:
    """
    Extract a specific section from a prompt file.
    
    Sections are delimited by "## {section_name}" headers.
    
    Args:
        prompt_content: The full prompt content
        section_name: Name of the section to extract (without ##)
        
    Returns:
        The section content, or None if not found
        
    Example:
        >>> content = load_prompt("response_agent_prompt")
        >>> intro = get_prompt_section(content, "Template: Giới thiệu khi có câu truy vấn")
    """
    lines = prompt_content.split("\n")
    section_lines = []
    in_section = False
    
    for line in lines:
        if line.startswith(f"## {section_name}"):
            in_section = True
            continue
        elif line.startswith("## ") and in_section:
            # Found the next section, stop
            break
        elif in_section:
            section_lines.append(line)
    
    if not section_lines:
        return None
    
    # Remove leading/trailing empty lines and horizontal rules
    content = "\n".join(section_lines).strip()
    content = content.replace("---", "").strip()
    return content if content else None


def load_prompts_as_dict(prompt_name: str) -> dict[str, str]:
    """
    Load all sections from a prompt file into a dictionary.
    Supports both YAML (.yaml) and Markdown (.md) formats.
    YAML files are preferred if they exist.
    
    Args:
        prompt_name: Name of the prompt file (without extension)
        
    Returns:
        Dictionary mapping section keys to content
    """
    # Try YAML first (preferred for new agentic prompts)
    yaml_path = PROMPTS_DIR / f"{prompt_name}.yaml"
    if yaml_path.exists():
        with open(yaml_path, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
            return prompts if prompts else {}
    
    # Fallback to Markdown
    content = load_prompt(prompt_name)
    prompts = {}
    current_key = None
    current_content = []
    
    for line in content.split("\n"):
        if line.startswith("## "):
            if current_key:
                prompts[current_key] = "\n".join(current_content).strip()
            current_key = line.replace("## ", "").strip().lower().replace(" ", "_")
            current_content = []
        else:
            current_content.append(line)
            
    if current_key:
        prompts[current_key] = "\n".join(current_content).strip()
        
    return prompts


def clear_prompt_cache():
    """Clear the prompt cache. Useful for development/testing."""
    load_prompt.cache_clear()

