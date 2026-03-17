import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const scenarios = [
  { id: 1, name: "highway_rain_cutin_001", weather: "🌧️", edgeCase: "Cut-In", status: "valid", date: "Mar 17, 2026", speed: 100, road: "Highway", time: "Noon" },
  { id: 2, name: "urban_night_ped_002", weather: "🌙", edgeCase: "Pedestrian", status: "valid", date: "Mar 17, 2026", speed: 60, road: "Urban", time: "Night" },
  { id: 3, name: "foggy_brake_003", weather: "🌫️", edgeCase: "E-Brake", status: "valid", date: "Mar 17, 2026", speed: 80, road: "Highway", time: "Noon" },
  { id: 4, name: "snow_cyclist_004", weather: "❄️", edgeCase: "Cyclist", status: "warning", date: "Mar 16, 2026", speed: 40, road: "Urban", time: "Morning" },
  { id: 5, name: "clear_normal_005", weather: "☀️", edgeCase: "None", status: "valid", date: "Mar 16, 2026", speed: 120, road: "Highway", time: "Afternoon" },
];

export default function ScenarioLibrary() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [detail, setDetail] = useState<(typeof scenarios)[0] | null>(null);

  const filtered = scenarios.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.edgeCase.toLowerCase().includes(search.toLowerCase())
  );

  const toggleSelect = (id: number) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <h1 className="text-2xl font-bold">Scenario Library</h1>

      <div className="flex gap-3">
        <Input
          placeholder="🔍 Search scenarios..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="p-3 w-10"></th>
                <th className="p-3 text-left font-medium">Name</th>
                <th className="p-3 text-left font-medium">Weather</th>
                <th className="p-3 text-left font-medium">Edge Case</th>
                <th className="p-3 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr
                  key={s.id}
                  className="border-b hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => setDetail(s)}
                >
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selected.includes(s.id)}
                      onCheckedChange={() => toggleSelect(s.id)}
                    />
                  </td>
                  <td className="p-3 font-mono">{s.name}</td>
                  <td className="p-3">{s.weather}</td>
                  <td className="p-3">{s.edgeCase}</td>
                  <td className="p-3">
                    <Badge
                      className={
                        s.status === "valid"
                          ? "bg-success text-success-foreground"
                          : "bg-warning text-warning-foreground"
                      }
                    >
                      {s.status === "valid" ? "✅ Valid" : "⚠️ Warning"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {selected.length > 0 && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Selected: {selected.length}</span>
          <Button size="sm" variant="outline">▶️ Run in Simulator</Button>
          <Button size="sm" variant="outline">📥 Download</Button>
          <Button size="sm" variant="destructive">🗑️ Delete</Button>
        </div>
      )}

      <Dialog open={!!detail} onOpenChange={() => setDetail(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-mono">{detail?.name}.xosc</DialogTitle>
          </DialogHeader>
          {detail && (
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground">Created: {detail.date}</p>
              <Card>
                <CardHeader><CardTitle className="text-sm">Parameters</CardTitle></CardHeader>
                <CardContent className="text-sm space-y-1">
                  <p>Weather: {detail.weather}</p>
                  <p>Time: {detail.time}</p>
                  <p>Road: {detail.road}</p>
                  <p>Ego Speed: {detail.speed} km/h</p>
                  <p>Edge Case: {detail.edgeCase}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-sm">Test Results</CardTitle></CardHeader>
                <CardContent className="text-sm space-y-1">
                  <p>Status: ✅ Passed</p>
                  <p>Collisions: 0</p>
                  <p>TTC Min: 2.3 seconds</p>
                  <p>Lane Departures: 0</p>
                </CardContent>
              </Card>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">📥 Download</Button>
                <Button size="sm" variant="outline">📋 Duplicate</Button>
                <Button size="sm" variant="outline">✏️ Edit</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
