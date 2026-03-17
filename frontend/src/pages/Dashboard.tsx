import { useEffect, useState } from "react";
import { StatCard } from "@/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import { api, StatsResponse, ScenarioResponse } from "@/lib/api";
import { Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [recentScenarios, setRecentScenarios] = useState<ScenarioResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiConnected, setApiConnected] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Check API health
      await api.healthCheck();
      setApiConnected(true);

      // Fetch stats and recent scenarios
      const [statsData, scenariosData] = await Promise.all([
        api.getStats(),
        api.listScenarios(5, 0),
      ]);

      setStats(statsData);
      setRecentScenarios(scenariosData.scenarios);
    } catch (error) {
      setApiConnected(false);
      toast.error("Backend not connected", {
        description: "Start the API server: cd ~/clawd/projects/scenario-generator && python api.py",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleQuickGenerate = async (template: string) => {
    try {
      const result = await api.generate({
        weather: template === "weather" ? "rainy" : "clear",
        time_of_day: "noon",
        road_type: template === "highway" ? "highway" : "urban",
        edge_case: template === "urban" ? "pedestrian" : "none",
        traffic_density: 50,
        ego_speed: template === "highway" ? 100 : 50,
      });
      toast.success("Scenario generated!", { description: result.filename });
      fetchData(); // Refresh list
    } catch (error) {
      toast.error("Generation failed");
    }
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2">
          <Badge variant={apiConnected ? "default" : "destructive"}>
            {apiConnected ? "🟢 API Connected" : "🔴 API Offline"}
          </Badge>
          <Button variant="ghost" size="icon" onClick={fetchData}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard value={stats?.total_scenarios ?? 0} label="Scenarios Generated" />
            <StatCard value={stats?.scenarios_today ?? 0} label="Generated Today" />
            <StatCard
              value={Object.keys(stats?.weather_coverage ?? {}).length}
              label="Weather Types Covered"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">⚡ Quick Generate</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={() => handleQuickGenerate("highway")}
                disabled={!apiConnected}
              >
                🛣️ Highway Test
              </Button>
              <Button
                variant="outline"
                onClick={() => handleQuickGenerate("urban")}
                disabled={!apiConnected}
              >
                🏙️ Urban Test
              </Button>
              <Button
                variant="outline"
                onClick={() => handleQuickGenerate("weather")}
                disabled={!apiConnected}
              >
                🌧️ Weather Test
              </Button>
              <Button variant="outline" onClick={() => navigate("/builder")}>
                🎲 Custom Scenario
              </Button>
              <Button onClick={() => navigate("/ai-generate")}>✨ AI Generate</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">📊 Recent Scenarios</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {recentScenarios.length === 0 ? (
                <div className="text-center text-muted-foreground py-4">
                  No scenarios yet. Generate your first one!
                </div>
              ) : (
                recentScenarios.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between py-2 px-3 rounded-md bg-secondary/50 cursor-pointer hover:bg-secondary/70"
                    onClick={() => window.open(api.getDownloadUrl(s.id), "_blank")}
                  >
                    <span className="font-mono text-sm">{s.filename}</span>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={s.valid ? "default" : "secondary"}
                        className={
                          s.valid
                            ? "bg-success text-success-foreground"
                            : "bg-warning text-warning-foreground"
                        }
                      >
                        {s.valid ? "✅ Valid" : "⚠️ Invalid"}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(s.created_at)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
