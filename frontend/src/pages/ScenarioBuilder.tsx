import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";

const weatherOptions = [
  { id: "clear", emoji: "☀️", label: "Clear" },
  { id: "cloudy", emoji: "☁️", label: "Cloudy" },
  { id: "rainy", emoji: "🌧️", label: "Rainy" },
  { id: "foggy", emoji: "🌫️", label: "Foggy" },
  { id: "snowy", emoji: "❄️", label: "Snowy" },
];

const timeOptions = [
  { id: "dawn", emoji: "🌅", label: "Dawn" },
  { id: "morning", emoji: "🌞", label: "Morning" },
  { id: "noon", emoji: "☀️", label: "Noon" },
  { id: "afternoon", emoji: "🌤️", label: "Afternoon" },
  { id: "evening", emoji: "🌆", label: "Evening" },
  { id: "night", emoji: "🌙", label: "Night" },
];

const roadTypes = [
  { id: "highway", label: "Highway" },
  { id: "urban", label: "Urban" },
  { id: "rural", label: "Rural" },
];

const edgeCases = [
  { id: "pedestrian", emoji: "🚶", label: "Pedestrian Cross" },
  { id: "cutin", emoji: "🚗", label: "Cut-In" },
  { id: "ebrake", emoji: "🛑", label: "Emergency Brake" },
  { id: "cyclist", emoji: "🚴", label: "Cyclist" },
  { id: "lanechange", emoji: "🔀", label: "Lane Change" },
  { id: "cutout", emoji: "⬅️", label: "Cut-Out" },
  { id: "animal", emoji: "🦌", label: "Animal Crossing" },
  { id: "none", emoji: "❌", label: "None (Normal)" },
];

function OptionButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
        selected
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-card text-foreground hover:bg-accent"
      }`}
    >
      {children}
    </button>
  );
}

export default function ScenarioBuilder() {
  const [weather, setWeather] = useState("cloudy");
  const [time, setTime] = useState("noon");
  const [road, setRoad] = useState("urban");
  const [edgeCase, setEdgeCase] = useState("pedestrian");
  const [traffic, setTraffic] = useState([50]);
  const [speed, setSpeed] = useState([60]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<string | null>(null);

  const trafficLabel =
    traffic[0] < 25 ? "Empty" : traffic[0] < 50 ? "Light" : traffic[0] < 75 ? "Moderate" : "Rush";

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const result = await api.generate({
        weather,
        time_of_day: time,
        road_type: road,
        edge_case: edgeCase,
        traffic_density: traffic[0],
        ego_speed: speed[0],
      });

      setLastGenerated(result.filename);
      toast.success("Scenario generated!", {
        description: result.filename,
        action: {
          label: "Download",
          onClick: () => window.open(api.getDownloadUrl(result.id), "_blank"),
        },
      });
    } catch (error) {
      toast.error("Generation failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const weatherObj = weatherOptions.find((w) => w.id === weather);
  const timeObj = timeOptions.find((t) => t.id === time);
  const edgeObj = edgeCases.find((e) => e.id === edgeCase);

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">Scenario Builder</h1>

      <Card>
        <CardHeader>
          <CardTitle>🌤️ Environment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-2 block">Weather</label>
            <div className="flex flex-wrap gap-2">
              {weatherOptions.map((w) => (
                <OptionButton key={w.id} selected={weather === w.id} onClick={() => setWeather(w.id)}>
                  {w.emoji} {w.label}
                </OptionButton>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-2 block">Time of Day</label>
            <div className="flex flex-wrap gap-2">
              {timeOptions.map((t) => (
                <OptionButton key={t.id} selected={time === t.id} onClick={() => setTime(t.id)}>
                  {t.emoji} {t.label}
                </OptionButton>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>🛣️ Road & Traffic</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-2 block">Road Type</label>
            <div className="flex gap-2">
              {roadTypes.map((r) => (
                <OptionButton key={r.id} selected={road === r.id} onClick={() => setRoad(r.id)}>
                  {r.label}
                </OptionButton>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-2 block">
              Traffic Density: <span className="text-foreground font-semibold">{trafficLabel}</span>
            </label>
            <Slider value={traffic} onValueChange={setTraffic} max={100} step={1} />
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-2 block">
              Ego Speed: <span className="text-foreground font-semibold">{speed[0]} km/h</span>
            </label>
            <Slider value={speed} onValueChange={setSpeed} min={10} max={200} step={5} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>⚠️ Edge Case</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {edgeCases.map((e) => (
              <OptionButton key={e.id} selected={edgeCase === e.id} onClick={() => setEdgeCase(e.id)}>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xl">{e.emoji}</span>
                  <span className="text-xs">{e.label}</span>
                </div>
              </OptionButton>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="p-4">
          <div className="text-sm font-medium text-muted-foreground mb-1">Preview</div>
          <div className="font-mono text-sm">
            🚗 Ego ({speed[0]} km/h) →{" "}
            {edgeObj?.id !== "none" ? `${edgeObj?.emoji} ${edgeObj?.label}` : "Normal driving"}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {road.charAt(0).toUpperCase() + road.slice(1)} road | {weatherObj?.emoji} {weatherObj?.label} |{" "}
            {timeObj?.emoji} {timeObj?.label} | {trafficLabel} traffic
          </div>
          {lastGenerated && (
            <div className="text-xs text-green-600 mt-2">
              ✅ Last generated: {lastGenerated}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex gap-3">
        <Button variant="outline">Cancel</Button>
        <Button onClick={handleGenerate} disabled={isGenerating}>
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            "Generate Scenario"
          )}
        </Button>
      </div>
    </div>
  );
}
