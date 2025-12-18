/**
 * Shared utility for Thought Process event rendering
 * Used by both ChatMessage and ThoughtProcessSidebar
 */

import type { StreamEvent } from '../hooks/useStreamingSearch';

export interface EventNodeInfo {
  icon: string;
  label: string;
  color?: string;
}

/**
 * Get display info for a Thought Process event
 * Returns icon and Vietnamese label based on node name
 * Returns null if node should be filtered out (no match found)
 */
export function getEventNodeInfo(event: StreamEvent): EventNodeInfo | null {
  // Handle progress events
  if (event.type === 'progress') {
    const icon = event.icon || '⚙️';
    const nodeName = event.node || '';
    
    if (!nodeName && event.icon === undefined) {
      return null;
    }
    
    return {
      icon,
      label: nodeName,
      color: event.color
    };
  }
  
  // Handle node_output events
  if (event.type === 'node_output') {
    const icon = '⚙️';  // node_output doesn't have icon property
    const nodeName = event.node || '';
    
    if (!nodeName) {
      return null;
    }
    
    return {
      icon,
      label: nodeName,
      color: undefined
    };
  }
  
  return null;
}

/**
 * Check if an event should be displayed in Thought Process
 */
export function shouldDisplayEvent(event: StreamEvent): boolean {
  // Only show progress and node_output events
  if (event.type !== 'progress' && event.type !== 'node_output') {
    return false;
  }
  
  // Filter out events without node info
  return getEventNodeInfo(event) !== null;
}
