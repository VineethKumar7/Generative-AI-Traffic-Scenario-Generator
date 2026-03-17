import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { api, ScenarioResponse } from "@/lib/api";
import { Loader2, Download, ExternalLink } from "lucide-react";

const examples = [
  "Highway driving in fog with a car cutting in",
  "School zone at 8am with children crossing",
  "Emergency brake test on wet road at 80 km/h",
  "Rainy night with pedestrian crossing",
];

interface ParsedScenario {
  weather: string;
  time: string;
  edgeCase: string;
  speed: string;
  road: string;
}

export default function AIGenerator() {
  const [prompt, setPrompt] = useState("");
  const [parsed, setParsed] = useState<ParsedScenario | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatedScenario, setGeneratedScenario] = useState<ScenarioResponse | null>(null);

  // Local parsing for preview (matching backend logic)
  const parsePrompt = (text: string): ParsedScenario => {
    const lower = text.toLowerCase();
    return {
      weather: lower.includes("rain") || lower.includes("wet")
        ? "🌧️ Rainy"
        : lower.includes("fog")
        ? "🌫️ Foggy"
        : lower.includes("snow")
        ? "❄️ Snowy"
        : lower.includes("cloud")
        ? "☁️ Cloudy"
        : "☀️ Clear",
      time: lower.includes("night")
        ? "🌙 Night"
        : lower.includes("morning") || lower.includes("8am") || lower.includes("dawn")
        ? "🌅 Morning"
        : lower.includes("evening")
        ? "🌆 Evening"
        : "☀️ Noon",
      edgeCase: lower.includes("pedestrian") || lower.includes("cross") || lower.includes("children")
        ? "🚶 Pedestrian Crossing"
        : lower.includes("cut") && lower.includes("in")
        ? "🚗 Cut-In"
        : lower.includes("brake") || lower.includes("emergency")
        ? "🛑 Emergency Brake"
        : lower.includes("cyclist") || lower.includes("bike")
        ? "🚴 Cyclist"
        : "❌ None",
      speed: lower.match(/(\d+)\s*km/)?.[1]
        ? `${lower.match(/(\d+)\s*km/)![1]} km/h`
        : "60 km/h",
      road: lower.includes("highway")
        ? "🛣️ Highway"
        : lower.includes("urban") || lower.includes("school") || lower.includes("street") || lower.includes("city")
        ? "🏙️ Urban"
        : "🌾 Rural",
    };
  };

  const handleAnalyze = () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setGeneratedScenario(null);
    
    // Simulate brief analysis delay for UX
    setTimeout(() => {
      setParsed(parsePrompt(prompt));
      setLoading(false);
    }, 500);
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setGenerating(true);
    try {
      const result = await api.generateFromPrompt(prompt);
      setGeneratedScenario(result);
      toast.success("Scenario generated!", {
        description: result.filename,
        action: {
          label: "Download",
          onClick: () => window.open(api.getDownloadUrl(result.id), "_blank"),
        },
      });
    } catch (error) {
      toast.error("Generation failed", {
        description: error instanceof Error ? error.message : "Backend not connected",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleReset = () => {
    setParsed(null);
    setPrompt("");
    setGeneratedScenario(null);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold">✨ AI Generator</h1>

      <Card>
        <CardHeader>
          <CardTitle>Describe your scenario in plain English</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="A rainy night scenario where a pedestrian suddenly crosses the road while the car is driving at 60 km/h on an urban street."
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              setParsed(null);
              setGeneratedScenario(null);
            }}
            rows={4}
          />

          <div>
            <p className="text-sm text-muted-foreground mb-2">💡 Examples:</p>
            <div className="flex flex-wrap gap-2">
              {examples.map((ex) => (
                <button
                  key={ex}
                  className="text-xs px-3 py-1.5 rounded-full border border-border bg-card hover:bg-accent text-muted-foreground transition-colors"
                  onClick={() => {
                    setPrompt(ex);
                    setParsed(null);
                    setGeneratedScenario(null);
                  }}
                >
                  "{ex}"
                </button>
              ))}
            </div>
          </div>

          <Button onClick={handleAnalyze} disabled={!prompt.trim() || loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              "🪄 Analyze Description"
            )}
          </Button>
        </CardContent>
      </Card>

      {parsed && !generatedScenario && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle>🤖 AI Understood</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(parsed).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <Badge className="bg-success text-success-foreground">✅</Badge>
                <span className="text-sm capitalize text-muted-foreground">{key}:</span>
                <span className="text-sm font-medium">{value}</span>
              </div>
            ))}
            <div className="flex gap-3 pt-4">
              <Button variant="outline" onClick={handleReset}>
                ← Edit Prompt
              </Button>
              <Button onClick={handleGenerate} disabled={generating}>
                {generating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  "✓ Looks Good – Generate"
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {generatedScenario && (
        <Card className="border-success/50 bg-success/5">
          <CardHeader>
            <CardTitle className="text-success">✅ Scenario Generated!</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="font-mono text-sm bg-background rounded-md p-3 border">
              {generatedScenario.filename}
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Weather:</span>{" "}
                <span className="font-medium">{generatedScenario.weather}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Time:</span>{" "}
                <span className="font-medium">{generatedScenario.time_of_day}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Edge Case:</span>{" "}
                <span className="font-medium">{generatedScenario.edge_case}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Speed:</span>{" "}
                <span className="font-medium">{generatedScenario.ego_speed} km/h</span>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => window.open(api.getDownloadUrl(generatedScenario.id), "_blank")}
              >
                <Download className="mr-2 h-4 w-4" />
                Download .xosc
              </Button>
              <Button variant="outline" onClick={handleReset}>
                Generate Another
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
