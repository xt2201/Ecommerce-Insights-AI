from typing import List, Dict, Any
from langchain_core.tools import BaseTool

def get_tool_definitions(tools: List[BaseTool]) -> List[Dict[str, Any]]:
    """
    Convert LangChain tools to a JSON-serializable definition format 
    compatible with the Manager Agent's prompt expectations.
    """
    definitions = []
    for tool in tools:
        # Simplify the parameters for the prompt
        # LangChain's tool.args is a dict of {arg_name: {type: ..., title: ...}}
        parameters = {}
        for name, info in tool.args.items():
            parameters[name] = {
                "type": info.get("type", "string"),
                "description": info.get("title", name) # Fallback to title/name
            }
            
        definitions.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters
        })
    return definitions
