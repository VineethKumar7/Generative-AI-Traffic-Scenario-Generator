/**
 * API Client for Scenario Generator Backend
 */

const API_BASE = 'http://localhost:8000';

export interface GenerateRequest {
  weather: string;
  time_of_day: string;
  road_type: string;
  edge_case: string;
  traffic_density: number;
  ego_speed: number;
  name?: string;
}

export interface AIGenerateRequest {
  prompt: string;
}

export interface BatchGenerateRequest {
  count: number;
  template?: string;
  include_all_weather?: boolean;
  include_all_times?: boolean;
  include_all_edge_cases?: boolean;
}

export interface ScenarioResponse {
  id: string;
  filename: string;
  path: string;
  weather: string;
  time_of_day: string;
  edge_case: string;
  ego_speed: number;
  created_at: string;
  valid: boolean;
}

export interface StatsResponse {
  total_scenarios: number;
  scenarios_today: number;
  weather_coverage: Record<string, number>;
  edge_case_coverage: Record<string, number>;
}

export interface ScenarioListResponse {
  scenarios: ScenarioResponse[];
  total: number;
}

class ScenarioAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    return this.fetch('/');
  }

  // Get dashboard stats
  async getStats(): Promise<StatsResponse> {
    return this.fetch('/api/stats');
  }

  // Generate single scenario
  async generate(request: GenerateRequest): Promise<ScenarioResponse> {
    return this.fetch('/api/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Generate from AI prompt
  async generateFromPrompt(prompt: string): Promise<ScenarioResponse> {
    return this.fetch('/api/generate/ai', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  }

  // Generate batch
  async generateBatch(request: BatchGenerateRequest): Promise<{
    generated: number;
    scenarios: ScenarioResponse[];
  }> {
    return this.fetch('/api/generate/batch', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // List scenarios
  async listScenarios(limit = 50, offset = 0): Promise<ScenarioListResponse> {
    return this.fetch(`/api/scenarios?limit=${limit}&offset=${offset}`);
  }

  // Get scenario details
  async getScenario(id: string): Promise<ScenarioResponse & { content: string }> {
    return this.fetch(`/api/scenarios/${id}`);
  }

  // Delete scenario
  async deleteScenario(id: string): Promise<{ deleted: string }> {
    return this.fetch(`/api/scenarios/${id}`, {
      method: 'DELETE',
    });
  }

  // Get download URL
  getDownloadUrl(id: string): string {
    return `${this.baseUrl}/api/scenarios/${id}/download`;
  }

  // List templates
  async listTemplates(): Promise<{
    templates: Array<{
      id: string;
      description: string;
      road_network: string;
      speed_range: [number, number];
    }>;
  }> {
    return this.fetch('/api/templates');
  }

  // List options
  async listOptions(): Promise<{
    weather: string[];
    time_of_day: string[];
    traffic_density: string[];
    edge_cases: string[];
  }> {
    return this.fetch('/api/options');
  }

  // CARLA Integration
  async getCarlaStatus(): Promise<{ available: boolean; connected: boolean; host: string; port: number }> {
    return this.fetch('/api/carla/status');
  }

  async connectCarla(): Promise<{ connected: boolean; message: string }> {
    return this.fetch('/api/carla/connect', { method: 'POST' });
  }

  async disconnectCarla(): Promise<{ connected: boolean; message: string }> {
    return this.fetch('/api/carla/disconnect', { method: 'POST' });
  }

  async runScenario(scenarioId: string): Promise<{ 
    started: boolean; 
    scenario_id: string;
    message: string;
  }> {
    return this.fetch(`/api/carla/run/${scenarioId}`, { method: 'POST' });
  }

  async getRunStatus(): Promise<{
    running: boolean;
    scenario_id: string | null;
    elapsed_seconds: number;
    result: {
      success: boolean;
      duration: number;
      collisions: number;
      error?: string;
    } | null;
    error: string | null;
  }> {
    return this.fetch('/api/carla/run/status');
  }

  async startCamera(cameraType: string = 'chase'): Promise<{ started: boolean }> {
    return this.fetch(`/api/carla/camera/start?camera_type=${cameraType}`, { method: 'POST' });
  }

  async stopCamera(): Promise<{ stopped: boolean }> {
    return this.fetch('/api/carla/camera/stop', { method: 'POST' });
  }

  async getCameraFrame(): Promise<{ frame: string } | null> {
    try {
      return await this.fetch('/api/carla/camera/frame');
    } catch {
      return null;
    }
  }

  async stopScenario(): Promise<{ stopped: boolean; message: string }> {
    return this.fetch('/api/carla/stop', { method: 'POST' });
  }
}

// Export singleton instance
export const api = new ScenarioAPI();

export default api;
