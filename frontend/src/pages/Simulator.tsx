import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CarlaViewer } from "@/components/CarlaViewer";
import { ScenarioPreview } from "@/components/ScenarioPreview";
import { api, ScenarioResponse } from "@/lib/api";
import { toast } from "sonner";
import {
  Play,
  Square,
  Wifi,
  WifiOff,
  FileVideo,
  BarChart3,
  Grid3X3,
  Download,
  RefreshCw,
  Eye,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";

type ViewState = "select" | "preview" | "running" | "results";

interface TestResult {
  scenario: ScenarioResponse;
  passed: boolean;
  duration: number;
  collisions: number;
  minTTC: number;
  events: { time: number; type: string; description: string }[];
}

export default function Simulator() {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [viewState, setViewState] = useState<ViewState>("select");
  const [scenarios, setScenarios] = useState<ScenarioResponse[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioResponse | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [batchProgress, setBatchProgress] = useState(0);
  const [batchResults, setBatchResults] = useState<TestResult[]>([]);

  // Auto-connect on mount if previously connected
  useEffect(() => {
    fetchScenarios();
    
    // Check if we should auto-connect
    const autoConnect = localStorage.getItem('carla_autoconnect');
    if (autoConnect === 'true') {
      checkAndConnect();
    }
  }, []);

  const checkAndConnect = async () => {
    try {
      setConnecting(true);
      const status = await api.getCarlaStatus();
      if (status.available) {
        if (!status.connected) {
          await api.connectCarla();
        }
        setConnected(true);
        localStorage.setItem('carla_autoconnect', 'true');
      }
    } catch {
      localStorage.removeItem('carla_autoconnect');
    } finally {
      setConnecting(false);
    }
  };

  const fetchScenarios = async () => {
    try {
      const data = await api.listScenarios(20, 0);
      setScenarios(data.scenarios);
    } catch {
      // API might not be running
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    try {
      await api.connectCarla();
      setConnected(true);
      localStorage.setItem('carla_autoconnect', 'true');
      toast.success("Connected to CARLA", {
        description: "CARLA server at localhost:2000",
      });
    } catch (e) {
      toast.error("Failed to connect", {
        description: e instanceof Error ? e.message : "CARLA server not available",
      });
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await api.disconnectCarla();
    } catch {
      // Ignore disconnect errors
    }
    setConnected(false);
    setViewState("select");
    localStorage.removeItem('carla_autoconnect');
    toast.info("Disconnected from CARLA");
  };

  const handleSelectScenario = (scenario: ScenarioResponse) => {
    setSelectedScenario(scenario);
    setViewState("preview");
  };

  const handleRunTest = () => {
    if (!selectedScenario) return;
    setViewState("running");
    
    // Simulate test completion after 5 seconds
    setTimeout(() => {
      setTestResult({
        scenario: selectedScenario,
        passed: Math.random() > 0.2,
        duration: 30,
        collisions: Math.random() > 0.8 ? 1 : 0,
        minTTC: 1.5 + Math.random() * 2,
        events: [
          { time: 0, type: "start", description: "Scenario started" },
          { time: 12, type: "pedestrian", description: "Pedestrian detected" },
          { time: 15, type: "brake", description: "Emergency brake applied" },
          { time: 18, type: "stop", description: "Vehicle stopped safely" },
          { time: 30, type: "end", description: "Scenario completed" },
        ],
      });
      setViewState("results");
    }, 5000);
  };

  const handleRunBatch = () => {
    setBatchMode(true);
    setBatchProgress(0);
    setBatchResults([]);

    let progress = 0;
    const interval = setInterval(() => {
      progress += 5;
      setBatchProgress(progress);

      if (progress % 25 === 0 && scenarios[Math.floor(progress / 25) - 1]) {
        const s = scenarios[Math.floor(progress / 25) - 1];
        setBatchResults((prev) => [
          ...prev,
          {
            scenario: s,
            passed: Math.random() > 0.15,
            duration: 30,
            collisions: Math.random() > 0.85 ? 1 : 0,
            minTTC: 1.5 + Math.random() * 2,
            events: [],
          },
        ]);
      }

      if (progress >= 100) {
        clearInterval(interval);
        toast.success("Batch test complete!");
      }
    }, 200);
  };

  const handleBack = () => {
    setViewState("select");
    setSelectedScenario(null);
    setTestResult(null);
  };

  // Render different views based on state
  return (
    <div className="space-y-6">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">🎮 Simulator</h1>
        <div className="flex items-center gap-2">
          <Badge
            variant={connected ? "default" : "secondary"}
            className={connected ? "bg-green-500" : ""}
          >
            {connected ? (
              <>
                <Wifi className="h-3 w-3 mr-1" /> CARLA Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 mr-1" /> Not Connected
              </>
            )}
          </Badge>
          {!connected ? (
            <Button size="sm" onClick={handleConnect} disabled={connecting}>
              {connecting ? "Connecting..." : "Connect"}
            </Button>
          ) : (
            <Button size="sm" variant="outline" onClick={handleDisconnect}>
              Disconnect
            </Button>
          )}
        </div>
      </div>

      {/* VIEW: Select Scenario */}
      {viewState === "select" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Scenario List */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <FileVideo className="h-5 w-5" />
                  Select Scenario to Run
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={fetchScenarios}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {scenarios.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileVideo className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No scenarios found</p>
                  <p className="text-sm">Generate some scenarios first!</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {scenarios.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => connected && handleSelectScenario(s)}
                      className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                        connected
                          ? "cursor-pointer hover:bg-accent hover:border-primary"
                          : "opacity-50 cursor-not-allowed"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className="text-2xl flex-shrink-0">
                          {s.weather === "rainy" ? "🌧️" : s.weather === "foggy" ? "🌫️" : s.weather === "snowy" ? "🌨️" : "☀️"}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-mono text-sm truncate" title={s.filename}>{s.filename}</div>
                          <div className="text-xs text-muted-foreground truncate">
                            {s.weather} • {s.time_of_day} • {s.edge_case}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Badge variant="outline" className="whitespace-nowrap">{s.ego_speed} km/h</Badge>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Grid3X3 className="h-5 w-5" />
                  Batch Run
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Run all {scenarios.length} scenarios automatically
                </p>
                <Button
                  className="w-full"
                  onClick={handleRunBatch}
                  disabled={!connected || scenarios.length === 0 || batchMode}
                >
                  <Play className="h-4 w-4 mr-2" />
                  Run All Scenarios
                </Button>

                {batchMode && (
                  <div className="space-y-2">
                    <Progress value={batchProgress} />
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>{Math.round(batchProgress)}%</span>
                      <span>
                        {batchResults.filter((r) => r.passed).length} passed,{" "}
                        {batchResults.filter((r) => !r.passed).length} failed
                      </span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {!connected && (
              <Card className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-950/20">
                <CardContent className="py-4">
                  <p className="text-sm text-yellow-700 dark:text-yellow-400">
                    ⚠️ Connect to CARLA server to run simulations
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* VIEW: Preview */}
      {viewState === "preview" && selectedScenario && (
        <ScenarioPreview
          scenario={selectedScenario}
          onBack={handleBack}
          onRunTest={handleRunTest}
        />
      )}

      {/* VIEW: Running */}
      {viewState === "running" && selectedScenario && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              Running: <span className="font-mono">{selectedScenario.filename}</span>
            </h2>
            <Badge className="bg-red-500 animate-pulse">🔴 LIVE</Badge>
          </div>

          <CarlaViewer
            scenarioName={selectedScenario.filename}
            isConnected={connected}
            isRunning={true}
            onStop={() => setViewState("select")}
          />
        </div>
      )}

      {/* VIEW: Results */}
      {viewState === "results" && testResult && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              {testResult.passed ? (
                <CheckCircle className="h-6 w-6 text-green-500" />
              ) : (
                <XCircle className="h-6 w-6 text-red-500" />
              )}
              Results: {testResult.scenario.filename}
            </h2>
            <Badge className={testResult.passed ? "bg-green-500" : "bg-red-500"}>
              {testResult.passed ? "✅ PASSED" : "❌ FAILED"}
            </Badge>
          </div>

          {/* Result Summary */}
          <Card className={testResult.passed ? "border-green-500/30" : "border-red-500/30"}>
            <CardContent className="py-6">
              <div className="grid grid-cols-4 gap-6 text-center">
                <div>
                  <div className="text-3xl font-bold">{testResult.collisions}</div>
                  <div className="text-muted-foreground">Collisions</div>
                </div>
                <div>
                  <div className="text-3xl font-bold">0</div>
                  <div className="text-muted-foreground">Lane Departures</div>
                </div>
                <div>
                  <div className="text-3xl font-bold">{testResult.minTTC.toFixed(1)}s</div>
                  <div className="text-muted-foreground">Min TTC</div>
                </div>
                <div>
                  <div className="text-3xl font-bold">100%</div>
                  <div className="text-muted-foreground">Completed</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Replay Video Placeholder */}
          <Card>
            <CardHeader>
              <CardTitle>📹 Replay</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
                <div className="text-center text-white">
                  <Play className="h-16 w-16 mx-auto mb-2 opacity-50" />
                  <p className="text-sm opacity-70">Click to replay scenario</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Event Timeline */}
          <Card>
            <CardHeader>
              <CardTitle>📊 Event Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                {/* Timeline bar */}
                <div className="absolute top-0 left-6 bottom-0 w-0.5 bg-border" />

                <div className="space-y-4">
                  {testResult.events.map((event, i) => (
                    <div key={i} className="flex items-start gap-4 relative">
                      <div
                        className={`w-3 h-3 rounded-full border-2 bg-background z-10 ${
                          event.type === "start"
                            ? "border-green-500"
                            : event.type === "end"
                            ? "border-blue-500"
                            : "border-yellow-500"
                        }`}
                      />
                      <div className="flex-1 pb-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{event.description}</span>
                          <Badge variant="outline" className="text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            {event.time}s
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleBack}>
              ← Back to Scenarios
            </Button>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Download Video
            </Button>
            <Button variant="outline">
              <BarChart3 className="h-4 w-4 mr-2" />
              Full Report
            </Button>
            <Button onClick={handleRunTest}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Run Again
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
