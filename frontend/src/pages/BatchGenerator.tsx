import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

export default function BatchGenerator() {
  const [count, setCount] = useState([25]);
  const [options, setOptions] = useState({
    allWeather: true,
    allTimes: true,
    allEdgeCases: true,
    customOnly: false,
  });
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  const totalEstimate = options.allWeather && options.allTimes && options.allEdgeCases ? 240 : count[0];

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleStart = () => {
    setRunning(true);
    setProgress(0);
    intervalRef.current = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(intervalRef.current);
          setRunning(false);
          toast.success(`Batch complete! ${totalEstimate} scenarios generated.`);
          return 100;
        }
        return p + 2;
      });
    }, 100);
  };

  const handleCancel = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setRunning(false);
    setProgress(0);
  };

  const toggleOption = (key: keyof typeof options) => {
    setOptions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const generated = Math.round((progress / 100) * totalEstimate);

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold">Batch Generator</h1>

      <Card>
        <CardContent className="pt-6 space-y-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-2 block">
              How many scenarios? <span className="text-foreground font-semibold">{count[0]}</span>
            </label>
            <Slider value={count} onValueChange={setCount} min={5} max={100} step={5} disabled={running} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Coverage Options</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { key: "allWeather" as const, label: "All weather types (5 scenarios each)" },
            { key: "allTimes" as const, label: "All times of day (6 scenarios each)" },
            { key: "allEdgeCases" as const, label: "All edge cases (8 scenarios each)" },
            { key: "customOnly" as const, label: "Custom template only" },
          ].map(({ key, label }) => (
            <div key={key} className="flex items-center gap-2">
              <Checkbox
                checked={options[key]}
                onCheckedChange={() => toggleOption(key)}
                disabled={running}
              />
              <span className="text-sm">{label}</span>
            </div>
          ))}
          <p className="text-sm text-muted-foreground pt-2">
            📊 This will generate approximately <strong>{totalEstimate}</strong> unique scenarios
          </p>
        </CardContent>
      </Card>

      {running || progress === 100 ? (
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={progress} />
            <p className="text-sm text-muted-foreground">
              {progress < 100
                ? `${Math.round(progress)}% (${generated}/${totalEstimate})`
                : `✅ Complete! ${totalEstimate} scenarios generated`}
            </p>
            {progress < 100 && (
              <div className="text-sm space-y-1">
                <p>{progress > 40 ? "✅" : "⏳"} Weather coverage{progress > 40 ? ": Complete" : ""}</p>
                <p>{progress > 70 ? "✅" : "⏳"} Time coverage{progress > 70 ? ": Complete" : `: ${Math.min(6, Math.round((progress / 70) * 6))}/6 done`}</p>
                <p>{progress > 70 ? "⏳ Edge cases: In progress" : "⏸️ Edge cases: Waiting"}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      <div className="flex gap-3">
        {running ? (
          <Button variant="destructive" onClick={handleCancel}>Cancel Batch</Button>
        ) : (
          <Button onClick={handleStart} disabled={progress === 100}>
            {progress === 100 ? "✅ Done" : "▶️ Start Batch"}
          </Button>
        )}
        {progress === 100 && (
          <Button variant="outline" onClick={() => toast.info("Download started")}>
            📥 Download All .zip
          </Button>
        )}
      </div>
    </div>
  );
}
