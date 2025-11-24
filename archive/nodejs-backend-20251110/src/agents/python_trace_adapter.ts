/**
 * Python trace adapter for monitoring agent execution.
 * Bridges TypeScript backend with Python TraceManager via CLI.
 */

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface ExecutionStep {
  step_id: string;
  step_type: string;
  agent_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  duration?: number;
  input_data?: any;
  output_data?: any;
  token_usage?: TokenUsage;
  error?: string;
  parent_step_id?: string;
}

interface ExecutionTrace {
  trace_id: string;
  user_query: string;
  session_id?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  total_duration?: number;
  steps: ExecutionStep[];
  total_tokens?: TokenUsage;
  metadata?: Record<string, any>;
}

interface AgentNode {
  name: string;
  type: string;
  description: string;
  provider: string;
  model: string;
  temperature: number;
  max_tokens: number;
  inputs: string[];
  outputs: string[];
  tools: string[];
  prompts: string[];
}

interface AgentEdge {
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

interface AgentArchitecture {
  name: string;
  description: string;
  version: string;
  nodes: AgentNode[];
  edges: AgentEdge[];
  entry_point: string;
  exit_points: string[];
  metadata: Record<string, any>;
}

/**
 * Execute Python trace script command.
 */
function executePythonCommand(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonPath = '/opt/miniconda3/bin/python';
    const scriptPath = path.join(__dirname, '../../../scripts/trace_server.py');

    const pythonProcess = spawn(pythonPath, [scriptPath, ...args]);

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python process exited with code ${code}: ${stderr}`));
        return;
      }

      try {
        const result = JSON.parse(stdout);
        if (result.success) {
          resolve(result);
        } else {
          reject(new Error(result.error || 'Unknown error'));
        }
      } catch (error) {
        reject(new Error(`Failed to parse Python output: ${error}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });
  });
}

/**
 * List recent execution traces.
 */
export async function listTraces(
  limit: number = 50,
  sessionId?: string
): Promise<ExecutionTrace[]> {
  const args = ['list', '--limit', limit.toString()];
  if (sessionId) {
    args.push('--session-id', sessionId);
  }

  const result = await executePythonCommand(args);
  return result.traces || [];
}

/**
 * Get specific trace with all steps.
 */
export async function getTrace(traceId: string): Promise<ExecutionTrace | null> {
  const result = await executePythonCommand(['get', traceId]);
  return result.trace || null;
}

/**
 * Get steps for a specific trace.
 */
export async function getTraceSteps(traceId: string): Promise<ExecutionStep[]> {
  const result = await executePythonCommand(['steps', traceId]);
  return result.steps || [];
}

/**
 * Get agent architecture information.
 */
export async function getAgentArchitecture(): Promise<AgentArchitecture> {
  const result = await executePythonCommand(['architecture']);
  return result.architecture;
}

/**
 * Get agent statistics.
 */
export async function getAgentStatistics(): Promise<any> {
  const result = await executePythonCommand(['stats']);
  return result.statistics;
}
