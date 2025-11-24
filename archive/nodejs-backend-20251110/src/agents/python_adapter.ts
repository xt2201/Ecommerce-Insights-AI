/**
 * Python Adapter - Calls Python LangGraph agents via main.py
 */
import { spawn } from 'child_process';
import { join } from 'path';
import type { AgentState } from '../types.js';

const PYTHON_TIMEOUT_MS = 60000; // 60 seconds timeout
const PROJECT_ROOT = join(process.cwd(), '..');

export async function runPythonWorkflow(userQuery: string): Promise<AgentState> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const mainScript = join(PROJECT_ROOT, 'main.py');
    
    console.log(`[PythonAdapter] Running: ${pythonPath} ${mainScript} --json`);
    console.log(`[PythonAdapter] Query: ${userQuery}`);
    
    const pythonProcess = spawn(pythonPath, [mainScript, userQuery, '--json'], {
      cwd: PROJECT_ROOT,
      env: process.env,
    });

    let stdout = '';
    let stderr = '';
    let timedOut = false;

    // Set timeout
    const timeout = setTimeout(() => {
      timedOut = true;
      pythonProcess.kill();
      reject(new Error(`Python process timed out after ${PYTHON_TIMEOUT_MS}ms`));
    }, PYTHON_TIMEOUT_MS);

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      clearTimeout(timeout);
      
      if (timedOut) return; // Already rejected

      if (code !== 0) {
        console.error(`[PythonAdapter] Process exited with code ${code}`);
        console.error(`[PythonAdapter] stderr: ${stderr}`);
        return reject(new Error(`Python process failed with exit code ${code}: ${stderr}`));
      }

      try {
        // Find JSON output (skip any text before the first '{')
        const trimmed = stdout.trim();
        const jsonStart = trimmed.indexOf('{');
        
        if (jsonStart === -1) {
          console.error(`[PythonAdapter] No JSON found in output`);
          console.error(`[PythonAdapter] stdout: ${trimmed}`);
          return reject(new Error('No JSON output from Python process'));
        }

        const jsonOutput = trimmed.substring(jsonStart);
        const pythonResult = JSON.parse(jsonOutput);
        
        // Convert Python output to AgentState format
        const state: AgentState = {
          userQuery: userQuery,
          response: pythonResult,
          debugNotes: pythonResult.debug_notes || [],
        };

        console.log(`[PythonAdapter] Success! Response has summary: ${!!pythonResult.summary}`);
        resolve(state);
      } catch (error: any) {
        console.error(`[PythonAdapter] Failed to parse JSON: ${error.message}`);
        console.error(`[PythonAdapter] stdout: ${stdout}`);
        reject(new Error(`Failed to parse Python output: ${error.message}`));
      }
    });

    pythonProcess.on('error', (error) => {
      clearTimeout(timeout);
      console.error(`[PythonAdapter] Process error: ${error.message}`);
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}
