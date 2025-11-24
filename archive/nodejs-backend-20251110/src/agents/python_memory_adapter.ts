/**
 * Python Memory Adapter - Calls Python LangGraph agents with memory support
 */
import { spawn } from 'child_process';
import { join } from 'path';

const PYTHON_TIMEOUT_MS = 60000; // 60 seconds timeout
const PROJECT_ROOT = join(process.cwd(), '..');

export interface SessionResponse {
  response: string;
  session_id: string;
  products_found: number;
  top_recommendation?: string;
  is_followup: boolean;
}

export interface SessionInfo {
  session_id: string;
  user_id?: string;
  created_at: string;
  expires_at: string;
  conversation_history: ConversationTurn[];
  user_preferences: any;
}

export interface ConversationTurn {
  user_query: string;
  timestamp: string;
  search_plan?: any;
  products_found: number;
  top_recommendation?: string;
}

/**
 * Run shopping query with memory support
 */
export async function runPythonWorkflowWithMemory(
  userQuery: string,
  sessionId?: string,
  userId?: string
): Promise<SessionResponse> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const mainScript = join(PROJECT_ROOT, 'main_with_memory.py');
    
    // Build command arguments
    const args = [mainScript, userQuery, '--json'];
    if (sessionId) {
      args.push('--session-id', sessionId);
    }
    if (userId) {
      args.push('--user-id', userId);
    }
    
    console.log(`[MemoryAdapter] Running: ${pythonPath} ${args.join(' ')}`);
    console.log(`[MemoryAdapter] Query: ${userQuery}`);
    
    const pythonProcess = spawn(pythonPath, args, {
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
        console.error(`[MemoryAdapter] Process exited with code ${code}`);
        console.error(`[MemoryAdapter] stderr: ${stderr}`);
        return reject(new Error(`Python process failed with exit code ${code}: ${stderr}`));
      }

      try {
        // Find JSON output (skip any text before the first '{')
        const trimmed = stdout.trim();
        const jsonStart = trimmed.indexOf('{');
        
        if (jsonStart === -1) {
          console.error(`[MemoryAdapter] No JSON found in output`);
          console.error(`[MemoryAdapter] stdout: ${trimmed}`);
          return reject(new Error('No JSON output from Python process'));
        }

        const jsonOutput = trimmed.substring(jsonStart);
        const result = JSON.parse(jsonOutput);
        
        console.log(`[MemoryAdapter] Success! Session: ${result.session_id}`);
        resolve(result as SessionResponse);
      } catch (error: any) {
        console.error(`[MemoryAdapter] Failed to parse JSON: ${error.message}`);
        console.error(`[MemoryAdapter] stdout: ${stdout}`);
        reject(new Error(`Failed to parse Python output: ${error.message}`));
      }
    });

    pythonProcess.on('error', (error) => {
      clearTimeout(timeout);
      console.error(`[MemoryAdapter] Process error: ${error.message}`);
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

/**
 * Create a new session
 */
export async function createSession(userId?: string): Promise<{ session_id: string }> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const scriptPath = join(PROJECT_ROOT, 'scripts/session_manager.py');
    
    const args = [scriptPath, 'create'];
    if (userId) {
      args.push('--user-id', userId);
    }
    
    console.log(`[MemoryAdapter] Creating session: ${args.join(' ')}`);
    
    const pythonProcess = spawn(pythonPath, args, {
      cwd: PROJECT_ROOT,
      env: process.env,
    });

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
        console.error(`[MemoryAdapter] Create session failed: ${stderr}`);
        return reject(new Error(`Failed to create session: ${stderr}`));
      }

      try {
        const result = JSON.parse(stdout.trim());
        resolve(result);
      } catch (error: any) {
        reject(new Error(`Failed to parse session creation output: ${error.message}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

/**
 * Get session info
 */
export async function getSession(sessionId: string): Promise<SessionInfo> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const scriptPath = join(PROJECT_ROOT, 'scripts/session_manager.py');
    
    const args = [scriptPath, 'get', '--session-id', sessionId];
    
    console.log(`[MemoryAdapter] Getting session: ${sessionId}`);
    
    const pythonProcess = spawn(pythonPath, args, {
      cwd: PROJECT_ROOT,
      env: process.env,
    });

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
        console.error(`[MemoryAdapter] Get session failed: ${stderr}`);
        return reject(new Error(`Session not found: ${sessionId}`));
      }

      try {
        const result = JSON.parse(stdout.trim());
        resolve(result);
      } catch (error: any) {
        reject(new Error(`Failed to parse session info: ${error.message}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

/**
 * Delete session
 */
export async function deleteSession(sessionId: string): Promise<{ success: boolean }> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const scriptPath = join(PROJECT_ROOT, 'scripts/session_manager.py');
    
    const args = [scriptPath, 'delete', '--session-id', sessionId];
    
    console.log(`[MemoryAdapter] Deleting session: ${sessionId}`);
    
    const pythonProcess = spawn(pythonPath, args, {
      cwd: PROJECT_ROOT,
      env: process.env,
    });

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
        console.error(`[MemoryAdapter] Delete session failed: ${stderr}`);
        return reject(new Error(`Failed to delete session: ${stderr}`));
      }

      resolve({ success: true });
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

/**
 * Get conversation history for a session
 */
export async function getConversationHistory(sessionId: string): Promise<ConversationTurn[]> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || 'python';
    const scriptPath = join(PROJECT_ROOT, 'scripts/session_manager.py');
    
    const args = [scriptPath, 'history', '--session-id', sessionId];
    
    console.log(`[MemoryAdapter] Getting conversation history: ${sessionId}`);
    
    const pythonProcess = spawn(pythonPath, args, {
      cwd: PROJECT_ROOT,
      env: process.env,
    });

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
        console.error(`[MemoryAdapter] Get history failed: ${stderr}`);
        return reject(new Error(`Failed to get conversation history: ${stderr}`));
      }

      try {
        const result = JSON.parse(stdout.trim());
        resolve(result.conversation_history || []);
      } catch (error: any) {
        reject(new Error(`Failed to parse conversation history: ${error.message}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

