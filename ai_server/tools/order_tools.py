from __future__ import annotations

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Mock Order Database
MOCK_ORDERS = {
    "ORD-123": {"status": "Shipped", "delivery_date": "2025-12-10", "items": ["Gaming Laptop"]},
    "ORD-456": {"status": "Processing", "delivery_date": "TBD", "items": ["Wireless Mouse"]},
    "ORD-789": {"status": "Delivered", "delivery_date": "2025-12-01", "items": ["HDMI Cable"]},
}


@tool
def lookup_order_tool(order_id: str) -> str:
    """
    Check the status of an order by Order ID.
    Use this when the user asks about their order status or tracking.
    
    Args:
        order_id: The order ID to look up (e.g., ORD-123)
    """
    order = MOCK_ORDERS.get(order_id.upper())
    if not order:
        return f"Order '{order_id}' not found. Please check the Order ID."
        
    return (
        f"Order {order_id}:\n"
        f"- Status: {order['status']}\n"
        f"- Estimated Delivery: {order['delivery_date']}\n"
        f"- Items: {', '.join(order['items'])}"
    )


# Export LangChain tools list
ORDER_TOOLS = [lookup_order_tool]

