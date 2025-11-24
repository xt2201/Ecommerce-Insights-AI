"""Utility functions for loading prompts from markdown files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional


# Base directory for prompts - centralized in ai_server/prompts
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@lru_cache(maxsize=10)
def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt from a markdown file in the prompts directory.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        
    Returns:
        The content of the prompt file as a string
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        
    Example:
        >>> planning_prompt = load_prompt("planning_agent_prompt")
        >>> prompt = planning_prompt.format(query="Find laptops under $1000")
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    return prompt_path.read_text(encoding="utf-8")


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
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        
    Returns:
        Dictionary mapping section keys (lowercase, underscored) to content
    """
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
