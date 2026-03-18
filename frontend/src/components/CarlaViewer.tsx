import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  Maximize,
  Volume2,
  Camera,
  Gauge,
  AlertTriangle,
  Car,
  Video,
  VideoOff,
} from "lucide-react";
import { toast } from "sonner";

interface CarlaViewerProps {
  scenarioName?: string;
  isConnected: boolean;
  isRunning: boolean;
  onPlay?: () => void;
  onPause?: () => void;
  onStop?: () => void;
  onRestart?: () => void;
}

interface Metrics {
  speed: number;
  ttc: number;
  position: { x: number; y: number };
  road: string;
  collisions: number;
  laneDeparts: number;
}

const CAMERA_OPTIONS = [
  { id: "bird", label: "Bird's Eye", icon: "🦅" },
  { id: "chase", label: "Chase Cam", icon: "🚗" },
  { id: "hood", label: "Hood View", icon: "🎯" },
];

const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";

export function CarlaViewer({
  scenarioName = "scenario_rainy_night.xosc",
  isConnected,
  isRunning,
  onPlay,
  onPause,
  onStop,
  onRestart,
}: CarlaViewerProps) {
  const [camera, setCamera] = useState("chase");
  const [isPaused, setIsPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [useRealStream, setUseRealStream] = useState(false);
  const [streamConnected, setStreamConnected] = useState(false);
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics>({
    speed: 0,
    ttc: 999,
    position: { x: 0, y: 0 },
    road: "#0",
    collisions: 0,
    laneDeparts: 0,
  });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const animationRef = useRef<number>();
  const wsRef = useRef<WebSocket | null>(null);

  // Start camera streaming
  const startCamera = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/carla/camera/start?camera_type=${camera}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to start camera");
      
      // Connect WebSocket for streaming
      wsRef.current = new WebSocket(`${WS_BASE}/ws/carla/stream`);
      
      wsRef.current.onopen = () => {
        setStreamConnected(true);
        toast.success("Camera stream connected");
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.frame) {
          setCurrentFrame(`data:image/jpeg;base64,${data.frame}`);
        }
      };
      
      wsRef.current.onclose = () => {
        setStreamConnected(false);
      };
      
      wsRef.current.onerror = () => {
        setStreamConnected(false);
        toast.error("Camera stream error");
      };
      
    } catch (error) {
      console.error("Camera start error:", error);
      toast.error("Failed to start camera stream");
      setUseRealStream(false);
    }
  }, [camera]);

  // Stop camera streaming
  const stopCamera = useCallback(async () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    try {
      await fetch(`${API_BASE}/api/carla/camera/stop`, { method: "POST" });
    } catch {
      // Ignore errors
    }
    
    setStreamConnected(false);
    setCurrentFrame(null);
  }, []);

  // Toggle real stream
  const toggleRealStream = useCallback(async () => {
    if (useRealStream) {
      await stopCamera();
      setUseRealStream(false);
    } else {
      setUseRealStream(true);
      await startCamera();
    }
  }, [useRealStream, startCamera, stopCamera]);

  // Change camera type
  const handleCameraChange = useCallback(async (newCamera: string) => {
    setCamera(newCamera);
    if (useRealStream && streamConnected) {
      try {
        await fetch(`${API_BASE}/api/carla/camera/type/${newCamera}`, {
          method: "POST",
        });
      } catch {
        // Ignore
      }
    }
  }, [useRealStream, streamConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Simulated CARLA view with animated canvas (fallback when no real stream)
  useEffect(() => {
    if (!canvasRef.current || !isRunning || isPaused || useRealStream) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    const animate = () => {
      frame++;
      
      // Clear canvas
      ctx.fillStyle = "#1a1a2e";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw road
      ctx.fillStyle = "#374151";
      ctx.fillRect(0, canvas.height * 0.4, canvas.width, canvas.height * 0.35);

      // Road lines
      ctx.strokeStyle = "#fbbf24";
      ctx.lineWidth = 3;
      ctx.setLineDash([20, 15]);
      ctx.beginPath();
      ctx.moveTo(0, canvas.height * 0.575);
      ctx.lineTo(canvas.width, canvas.height * 0.575);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw horizon/sky gradient
      const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height * 0.4);
      gradient.addColorStop(0, "#0f172a");
      gradient.addColorStop(1, "#1e3a5f");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height * 0.4);

      // Weather effects (rain)
      if (scenarioName.includes("rain") || scenarioName.includes("rainy")) {
        ctx.strokeStyle = "rgba(200, 220, 255, 0.3)";
        ctx.lineWidth = 1;
        for (let i = 0; i < 100; i++) {
          const x = (i * 17 + frame * 2) % canvas.width;
          const y = (i * 13 + frame * 8) % canvas.height;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x - 2, y + 15);
          ctx.stroke();
        }
      }

      // Night effect
      if (scenarioName.includes("night")) {
        ctx.fillStyle = "rgba(0, 0, 20, 0.4)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // Draw ego vehicle (from behind - chase cam view)
      const carX = canvas.width / 2;
      const carY = canvas.height * 0.7;
      
      // Car body
      ctx.fillStyle = "#3b82f6";
      ctx.beginPath();
      ctx.roundRect(carX - 25, carY - 15, 50, 35, 5);
      ctx.fill();
      
      // Car roof
      ctx.fillStyle = "#1d4ed8";
      ctx.beginPath();
      ctx.roundRect(carX - 18, carY - 25, 36, 15, 3);
      ctx.fill();

      // Tail lights
      ctx.fillStyle = "#ef4444";
      ctx.fillRect(carX - 23, carY + 15, 8, 4);
      ctx.fillRect(carX + 15, carY + 15, 8, 4);

      // Draw NPC vehicle ahead
      const npcY = canvas.height * 0.48 + Math.sin(frame * 0.05) * 5;
      ctx.fillStyle = "#9ca3af";
      ctx.beginPath();
      ctx.roundRect(carX - 15, npcY - 8, 30, 20, 3);
      ctx.fill();

      // Pedestrian (if applicable)
      if (scenarioName.includes("pedestrian") || scenarioName.includes("ped")) {
        const pedX = canvas.width * 0.3 + Math.sin(frame * 0.03) * 50;
        const pedY = canvas.height * 0.55;
        ctx.fillStyle = "#f59e0b";
        ctx.beginPath();
        ctx.arc(pedX, pedY - 10, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillRect(pedX - 3, pedY - 4, 6, 15);
      }

      // Update metrics
      setMetrics({
        speed: 55 + Math.sin(frame * 0.02) * 10,
        ttc: 2.5 + Math.sin(frame * 0.01) * 1.5,
        position: { 
          x: Math.round(142 + frame * 0.5), 
          y: Math.round(89 + Math.sin(frame * 0.02) * 5) 
        },
        road: `#${47 + Math.floor(frame / 100) % 5}`,
        collisions: 0,
        laneDeparts: 0,
      });

      // Update progress
      setProgress(Math.min(100, (frame / 300) * 100));

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [isRunning, isPaused, scenarioName, useRealStream]);

  const handlePlayPause = () => {
    if (isPaused) {
      setIsPaused(false);
      onPlay?.();
    } else {
      setIsPaused(true);
      onPause?.();
    }
  };

  const formatTime = (percent: number) => {
    const seconds = Math.round((percent / 100) * 30);
    return `00:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-4">
      {/* Video Container */}
      <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
        {/* Real CARLA Stream */}
        {useRealStream && currentFrame ? (
          <img
            ref={imgRef}
            src={currentFrame}
            alt="CARLA Stream"
            className="w-full h-full object-cover"
          />
        ) : useRealStream && !currentFrame ? (
          <div className="w-full h-full flex items-center justify-center text-white">
            <div className="text-center">
              <div className="animate-spin text-4xl mb-2">⏳</div>
              <p>Waiting for camera stream...</p>
            </div>
          </div>
        ) : (
          /* Canvas for simulated CARLA view */
          <canvas
            ref={canvasRef}
            width={800}
            height={450}
            className="w-full h-full object-cover"
          />
        )}

        {/* Overlay - Live Badge */}
        {isRunning && (
          <div className="absolute top-4 left-4 flex items-center gap-2">
            <Badge variant="destructive" className="animate-pulse">
              🔴 LIVE
            </Badge>
            <Badge variant="secondary" className="bg-black/50 text-white">
              {camera === "bird" ? "🦅" : camera === "chase" ? "🚗" : "👁️"}{" "}
              {CAMERA_OPTIONS.find((c) => c.id === camera)?.label}
            </Badge>
            {useRealStream && (
              <Badge variant={streamConnected ? "default" : "secondary"} className="bg-green-600 text-white">
                {streamConnected ? "📡 Real Stream" : "📡 Connecting..."}
              </Badge>
            )}
          </div>
        )}

        {/* Overlay - Metrics */}
        {isRunning && (
          <div className="absolute top-4 right-4 bg-black/70 rounded-lg p-3 text-white text-sm space-y-1">
            <div className="flex items-center gap-2">
              <Gauge className="h-4 w-4" />
              <span>Speed: {Math.round(metrics.speed)} km/h</span>
            </div>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-400" />
              <span>TTC: {metrics.ttc.toFixed(1)}s</span>
            </div>
            <div className="flex items-center gap-2">
              <Car className="h-4 w-4" />
              <span>Road: {metrics.road}</span>
            </div>
          </div>
        )}

        {/* Overlay - Progress Bar */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
          {/* Progress slider */}
          <div className="flex items-center gap-3 text-white text-sm mb-3">
            <span>{formatTime(progress)}</span>
            <div className="flex-1">
              <Slider
                value={[progress]}
                max={100}
                step={1}
                className="cursor-pointer"
              />
            </div>
            <span>00:30</span>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {!isRunning ? (
                <Button size="sm" onClick={onPlay}>
                  <Play className="h-4 w-4 mr-1" /> Play
                </Button>
              ) : (
                <>
                  <Button size="sm" variant="secondary" onClick={handlePlayPause}>
                    {isPaused ? (
                      <Play className="h-4 w-4" />
                    ) : (
                      <Pause className="h-4 w-4" />
                    )}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={onStop}>
                    <Square className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="secondary" onClick={onRestart}>
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </>
              )}

              {/* Speed control */}
              <Select
                value={playbackSpeed.toString()}
                onValueChange={(v) => setPlaybackSpeed(parseFloat(v))}
              >
                <SelectTrigger className="w-20 h-8 bg-white/10 border-white/20 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0.5">0.5x</SelectItem>
                  <SelectItem value="1">1x</SelectItem>
                  <SelectItem value="2">2x</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              {/* Real Stream Toggle */}
              {isConnected && (
                <Button 
                  size="sm" 
                  variant={useRealStream ? "default" : "outline"} 
                  className={useRealStream ? "bg-green-600 hover:bg-green-700" : "text-white border-white/30"}
                  onClick={toggleRealStream}
                >
                  {useRealStream ? (
                    <><Video className="h-4 w-4 mr-1" /> Real</>
                  ) : (
                    <><VideoOff className="h-4 w-4 mr-1" /> Simulated</>
                  )}
                </Button>
              )}

              {/* Camera selector */}
              <Select value={camera} onValueChange={handleCameraChange}>
                <SelectTrigger className="w-36 h-8 bg-white/10 border-white/20 text-white">
                  <Camera className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CAMERA_OPTIONS.map((cam) => (
                    <SelectItem key={cam.id} value={cam.id}>
                      {cam.icon} {cam.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button size="sm" variant="ghost" className="text-white">
                <Volume2 className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="ghost" className="text-white">
                <Maximize className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Not connected overlay */}
        {!isConnected && (
          <div className="absolute inset-0 bg-black/80 flex flex-col items-center justify-center text-white">
            <div className="text-6xl mb-4">🎮</div>
            <h3 className="text-xl font-bold mb-2">CARLA Not Connected</h3>
            <p className="text-gray-400 text-sm mb-4">
              Connect to CARLA server to see 3D visualization
            </p>
            <Button variant="outline" className="border-white/30">
              Connect to CARLA
            </Button>
          </div>
        )}
      </div>

      {/* Scenario Info Bar */}
      <div className="flex items-center justify-between text-sm bg-muted/50 rounded-lg px-4 py-2">
        <div className="flex items-center gap-4">
          <span className="font-mono">{scenarioName}</span>
          {isRunning && (
            <Badge variant="secondary" className="bg-green-100 text-green-700">
              ✅ No collisions
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-4 text-muted-foreground">
          <span>Duration: 30s</span>
          <span>Vehicles: 3</span>
          <span>Weather: Rainy</span>
        </div>
      </div>
    </div>
  );
}
