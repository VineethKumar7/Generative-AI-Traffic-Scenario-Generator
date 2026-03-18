import { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScenarioResponse } from "@/lib/api";
import { Play, ArrowLeft, Cloud, Moon, Sun, CloudRain, CloudSnow, CloudFog, Camera, Video, VideoOff } from "lucide-react";

interface ScenarioPreviewProps {
  scenario: ScenarioResponse;
  isConnected?: boolean;
  onBack: () => void;
  onRunTest: () => void;
}

const API_BASE = "http://localhost:8000";

const SPECTATOR_LOCATIONS = [
  { id: "overview", label: "Overview", icon: "🗺️" },
  { id: "street", label: "Street Level", icon: "🚗" },
  { id: "spectator", label: "Free Camera", icon: "📷" },
];

const weatherIcons: Record<string, React.ReactNode> = {
  clear: <Sun className="h-5 w-5 text-yellow-500" />,
  cloudy: <Cloud className="h-5 w-5 text-gray-400" />,
  rainy: <CloudRain className="h-5 w-5 text-blue-500" />,
  foggy: <CloudFog className="h-5 w-5 text-gray-500" />,
  snowy: <CloudSnow className="h-5 w-5 text-blue-200" />,
};

const timeIcons: Record<string, React.ReactNode> = {
  dawn: <Sun className="h-5 w-5 text-orange-400" />,
  morning: <Sun className="h-5 w-5 text-yellow-400" />,
  noon: <Sun className="h-5 w-5 text-yellow-500" />,
  afternoon: <Sun className="h-5 w-5 text-orange-500" />,
  evening: <Moon className="h-5 w-5 text-orange-600" />,
  night: <Moon className="h-5 w-5 text-blue-900" />,
};

export function ScenarioPreview({ scenario, isConnected = false, onBack, onRunTest }: ScenarioPreviewProps) {
  const [useRealStream, setUseRealStream] = useState(true);
  const [spectatorLocation, setSpectatorLocation] = useState("overview");
  const [spectatorActive, setSpectatorActive] = useState(false);
  const [streamConnected, setStreamConnected] = useState(false);
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const spectatorPollingRef = useRef<NodeJS.Timeout | null>(null);

  const isRainy = scenario.weather?.toLowerCase().includes("rain");
  const isNight = scenario.time_of_day?.toLowerCase().includes("night") || 
                  scenario.time_of_day?.toLowerCase().includes("evening");
  const hasPedestrian = scenario.edge_case?.toLowerCase().includes("pedestrian");

  // Start spectator camera
  const startSpectator = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/carla/spectator/start?location=${spectatorLocation}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to start spectator camera");
      setSpectatorActive(true);
      return true;
    } catch (error) {
      console.error("Spectator start error:", error);
      return false;
    }
  }, [spectatorLocation]);

  // Stop spectator camera
  const stopSpectator = useCallback(async () => {
    if (spectatorPollingRef.current) {
      clearInterval(spectatorPollingRef.current);
      spectatorPollingRef.current = null;
    }
    
    try {
      await fetch(`${API_BASE}/api/carla/spectator/stop`, { method: "POST" });
    } catch {
      // Ignore errors
    }
    
    setSpectatorActive(false);
    setStreamConnected(false);
    setCurrentFrame(null);
  }, []);

  // Change spectator location
  const handleSpectatorLocationChange = useCallback(async (newLocation: string) => {
    setSpectatorLocation(newLocation);
    if (spectatorActive) {
      try {
        await fetch(`${API_BASE}/api/carla/spectator/location/${newLocation}`, {
          method: "POST",
        });
      } catch {
        // Ignore
      }
    }
  }, [spectatorActive]);

  // Toggle real stream
  const toggleRealStream = useCallback(async () => {
    if (useRealStream) {
      await stopSpectator();
      setUseRealStream(false);
    } else {
      setUseRealStream(true);
    }
  }, [useRealStream, stopSpectator]);

  // Start spectator when connected and useRealStream is true
  useEffect(() => {
    if (!isConnected || !useRealStream) {
      if (spectatorActive) {
        stopSpectator();
      }
      return;
    }

    startSpectator();

    return () => {
      stopSpectator();
    };
  }, [isConnected, useRealStream]);

  // Poll spectator frames
  useEffect(() => {
    if (!spectatorActive || !useRealStream || !isConnected) {
      if (spectatorPollingRef.current) {
        clearInterval(spectatorPollingRef.current);
        spectatorPollingRef.current = null;
      }
      return;
    }

    const pollSpectatorFrames = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/carla/spectator/frame`);
        if (res.ok) {
          const data = await res.json();
          if (data.frame && data.status === "ok") {
            setCurrentFrame(`data:image/jpeg;base64,${data.frame}`);
            setStreamConnected(true);
          } else if (data.status === "spectator_not_started" || data.status === "no_frame_yet") {
            setStreamConnected(false);
          }
        }
      } catch {
        setStreamConnected(false);
      }
    };

    pollSpectatorFrames();
    spectatorPollingRef.current = setInterval(pollSpectatorFrames, 66); // ~15 FPS

    return () => {
      if (spectatorPollingRef.current) {
        clearInterval(spectatorPollingRef.current);
        spectatorPollingRef.current = null;
      }
    };
  }, [spectatorActive, useRealStream, isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (spectatorPollingRef.current) {
        clearInterval(spectatorPollingRef.current);
      }
    };
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2">
          🚗 Preview: <span className="font-mono text-lg">{scenario.filename}</span>
        </h2>
      </div>

      {/* 3D Preview Card */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div className="relative aspect-video bg-gray-900">
            {/* Real CARLA Stream */}
            {useRealStream && isConnected && currentFrame ? (
              <>
                <img
                  src={currentFrame}
                  alt="CARLA Preview"
                  className="w-full h-full object-cover"
                />
                {/* Overlay badges */}
                <div className="absolute top-4 left-4 flex items-center gap-2">
                  <Badge variant="secondary" className="bg-blue-600 text-white">
                    👁️ LIVE PREVIEW
                  </Badge>
                  <Badge variant="secondary" className="bg-black/50 text-white">
                    {SPECTATOR_LOCATIONS.find((l) => l.id === spectatorLocation)?.icon}{" "}
                    {SPECTATOR_LOCATIONS.find((l) => l.id === spectatorLocation)?.label}
                  </Badge>
                </div>
              </>
            ) : useRealStream && isConnected && !currentFrame ? (
              /* Loading state */
              <div className="w-full h-full flex items-center justify-center text-white">
                <div className="text-center">
                  <div className="animate-spin text-4xl mb-2">⏳</div>
                  <p>Starting CARLA preview...</p>
                  <p className="text-gray-400 text-sm mt-2">
                    {spectatorActive ? "Waiting for first frame..." : "Initializing spectator camera..."}
                  </p>
                </div>
              </div>
            ) : (
              /* Fallback React-rendered preview */
              <div 
                className={`relative w-full h-full ${
                  isNight ? "bg-gradient-to-b from-slate-900 to-slate-800" : "bg-gradient-to-b from-sky-400 to-sky-200"
                }`}
              >
                {/* Rain Effect */}
                {isRainy && (
                  <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    {Array.from({ length: 50 }).map((_, i) => (
                      <div
                        key={i}
                        className="absolute w-0.5 bg-blue-300/40 rounded-full animate-rain"
                        style={{
                          left: `${Math.random() * 100}%`,
                          top: `${Math.random() * 100}%`,
                          height: `${10 + Math.random() * 20}px`,
                          animationDelay: `${Math.random() * 2}s`,
                          animationDuration: `${0.5 + Math.random() * 0.5}s`,
                        }}
                      />
                    ))}
                    <div className="absolute top-4 left-4 text-white/80 text-sm flex items-center gap-2">
                      <CloudRain className="h-5 w-5" />
                      Rain particles falling
                    </div>
                  </div>
                )}

                {/* Night Overlay */}
                {isNight && (
                  <div className="absolute top-4 right-4 text-white/80 text-sm flex items-center gap-2">
                    <Moon className="h-5 w-5" />
                    Night time lighting
                  </div>
                )}

                {/* Road */}
                <div className="absolute bottom-[30%] left-0 right-0 h-24 bg-gray-700">
                  <div className="absolute top-1/2 left-0 right-0 h-1 flex justify-center">
                    <div className="flex gap-8">
                      {Array.from({ length: 10 }).map((_, i) => (
                        <div key={i} className="w-12 h-1 bg-yellow-400" />
                      ))}
                    </div>
                  </div>
                  <div className="absolute top-2 left-0 right-0 h-0.5 bg-white/50" />
                  <div className="absolute bottom-2 left-0 right-0 h-0.5 bg-white/50" />
                </div>

                {/* Ego Vehicle */}
                <div className="absolute bottom-[35%] left-[30%] transform -translate-x-1/2">
                  <div className="relative">
                    <div className="text-4xl">🚗</div>
                    <div className="absolute -right-8 top-1/2 transform -translate-y-1/2 text-white text-2xl">
                      →
                    </div>
                  </div>
                </div>

                {/* Pedestrian */}
                {hasPedestrian && (
                  <div className="absolute bottom-[25%] right-[35%]">
                    <div className="flex flex-col items-center">
                      <span className="text-3xl">🚶</span>
                      <span className="text-xs text-white bg-black/50 px-2 py-0.5 rounded mt-1">
                        waiting to cross
                      </span>
                    </div>
                  </div>
                )}

                {/* Simulated badge */}
                <div className="absolute top-4 left-4">
                  <Badge variant="secondary" className="bg-gray-600 text-white">
                    🎨 SIMULATED
                  </Badge>
                </div>
              </div>
            )}

            {/* Camera Controls - always shown at bottom */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
              <div className="bg-black/70 rounded-lg px-4 py-2 flex items-center gap-4">
                {/* Real/Simulated Toggle */}
                {isConnected && (
                  <Button 
                    size="sm" 
                    variant={useRealStream ? "default" : "outline"} 
                    className={`h-7 ${useRealStream ? "bg-green-600 hover:bg-green-700" : "text-white border-white/30 hover:bg-white/20"}`}
                    onClick={toggleRealStream}
                  >
                    {useRealStream ? (
                      <><Video className="h-4 w-4 mr-1" /> Real</>
                    ) : (
                      <><VideoOff className="h-4 w-4 mr-1" /> Simulated</>
                    )}
                  </Button>
                )}

                {/* Location Selector (only when using real stream) */}
                {useRealStream && isConnected ? (
                  <Select value={spectatorLocation} onValueChange={handleSpectatorLocationChange}>
                    <SelectTrigger className="w-36 h-7 bg-white/10 border-white/20 text-white text-xs">
                      <Camera className="h-3 w-3 mr-1" />
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SPECTATOR_LOCATIONS.map((loc) => (
                        <SelectItem key={loc.id} value={loc.id}>
                          {loc.icon} {loc.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <span className="text-white text-sm">Camera: Bird's Eye</span>
                )}
              </div>
            </div>

            {/* Not connected hint */}
            {!isConnected && (
              <div className="absolute top-4 right-4">
                <Badge variant="secondary" className="bg-yellow-600 text-white">
                  ⚠️ Connect CARLA for live view
                </Badge>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Scenario Info */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="flex items-center gap-2">
              {weatherIcons[scenario.weather] || <Cloud className="h-5 w-5" />}
              <div>
                <div className="text-xs text-muted-foreground">Weather</div>
                <div className="font-medium capitalize">{scenario.weather}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {timeIcons[scenario.time_of_day] || <Sun className="h-5 w-5" />}
              <div>
                <div className="text-xs text-muted-foreground">Time</div>
                <div className="font-medium capitalize">{scenario.time_of_day}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Speed</div>
              <div className="font-medium">{scenario.ego_speed} km/h</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Edge Case</div>
              <div className="font-medium capitalize">{scenario.edge_case?.replace("_", " ")}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Duration</div>
              <div className="font-medium">30 seconds</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Vehicles</div>
              <div className="font-medium">3 NPCs</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Editor
        </Button>
        <Button onClick={onRunTest} className="bg-green-600 hover:bg-green-700">
          <Play className="h-4 w-4 mr-2" />
          Run Full Test
        </Button>
      </div>
    </div>
  );
}
