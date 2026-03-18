#!/usr/bin/env python3
"""
FastAPI Backend for Scenario Generator

Connects the React frontend to the scenario generation engine.
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from scenario_generator import (
    ScenarioConfig, Vehicle, Pedestrian,
    WeatherType, TimeOfDay, TrafficDensity, EdgeCaseType,
    OpenScenarioGenerator
)
from ai_generator import AIScenarioGenerator, generate_llm_scenario_description

app = FastAPI(
    title="Scenario Generator API",
    description="Generate OpenSCENARIO files for ADAS testing",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080", "http://192.168.178.34:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directories
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
SCENARIOS_DIR.mkdir(exist_ok=True)

RECORDINGS_DIR = Path(__file__).parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)

# Initialize generators
generator = OpenScenarioGenerator(SCENARIOS_DIR)
ai_generator = AIScenarioGenerator(str(SCENARIOS_DIR))


# ============ Request/Response Models ============

class GenerateRequest(BaseModel):
    """Request to generate a single scenario."""
    weather: str = "clear"
    time_of_day: str = "noon"
    road_type: str = "urban"
    edge_case: str = "none"
    traffic_density: int = 50  # 0-100
    ego_speed: int = 60  # km/h
    name: Optional[str] = None


class AIGenerateRequest(BaseModel):
    """Request to generate from natural language."""
    prompt: str


class BatchGenerateRequest(BaseModel):
    """Request to generate multiple scenarios."""
    count: int = 10
    template: Optional[str] = None
    include_all_weather: bool = False
    include_all_times: bool = False
    include_all_edge_cases: bool = False


class ScenarioResponse(BaseModel):
    """Response with generated scenario info."""
    id: str
    filename: str
    path: str
    weather: str
    time_of_day: str
    edge_case: str
    ego_speed: int
    created_at: str
    valid: bool = True


class ScenarioListResponse(BaseModel):
    """List of scenarios."""
    scenarios: List[ScenarioResponse]
    total: int


class StatsResponse(BaseModel):
    """Dashboard statistics."""
    total_scenarios: int
    scenarios_today: int
    weather_coverage: dict
    edge_case_coverage: dict


# ============ Helper Functions ============

def map_weather(weather: str) -> WeatherType:
    mapping = {
        "clear": WeatherType.CLEAR,
        "cloudy": WeatherType.CLOUDY,
        "rainy": WeatherType.RAINY,
        "foggy": WeatherType.FOGGY,
        "snowy": WeatherType.SNOWY,
    }
    return mapping.get(weather.lower(), WeatherType.CLEAR)


def map_time(time: str) -> TimeOfDay:
    mapping = {
        "dawn": TimeOfDay.DAWN,
        "morning": TimeOfDay.MORNING,
        "noon": TimeOfDay.NOON,
        "afternoon": TimeOfDay.AFTERNOON,
        "evening": TimeOfDay.EVENING,
        "night": TimeOfDay.NIGHT,
    }
    return mapping.get(time.lower(), TimeOfDay.NOON)


def map_traffic(density: int) -> TrafficDensity:
    if density < 10:
        return TrafficDensity.EMPTY
    elif density < 30:
        return TrafficDensity.SPARSE
    elif density < 60:
        return TrafficDensity.MODERATE
    elif density < 85:
        return TrafficDensity.DENSE
    else:
        return TrafficDensity.RUSH_HOUR


def map_edge_case(edge_case: str) -> EdgeCaseType:
    mapping = {
        "none": EdgeCaseType.NONE,
        "pedestrian": EdgeCaseType.PEDESTRIAN_CROSSING,
        "cutin": EdgeCaseType.CUT_IN,
        "cutout": EdgeCaseType.CUT_OUT,
        "ebrake": EdgeCaseType.EMERGENCY_BRAKE,
        "lanechange": EdgeCaseType.LANE_CHANGE,
        "cyclist": EdgeCaseType.CYCLIST,
        "animal": EdgeCaseType.ANIMAL_CROSSING,
        "intersection": EdgeCaseType.INTERSECTION,
    }
    return mapping.get(edge_case.lower(), EdgeCaseType.NONE)


def map_road_to_network(road_type: str) -> str:
    mapping = {
        "highway": "Town04",
        "urban": "Town01",
        "rural": "Town02",
    }
    return mapping.get(road_type.lower(), "Town01")


def get_scenario_metadata(filepath: Path) -> dict:
    """Extract metadata from scenario file."""
    # Parse basic info from filename and content
    filename = filepath.name
    stat = filepath.stat()
    
    # Try to extract info from filename pattern: scenario_{template}_{weather}_{time}_{id}.xosc
    parts = filename.replace(".xosc", "").split("_")
    
    return {
        "id": filepath.stem,
        "filename": filename,
        "path": str(filepath),
        "weather": parts[2] if len(parts) > 2 else "unknown",
        "time_of_day": parts[3] if len(parts) > 3 else "unknown",
        "edge_case": "unknown",
        "ego_speed": 60,
        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "valid": True,
    }


# ============ API Endpoints ============

@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "Scenario Generator API"}


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """Get dashboard statistics."""
    scenarios = list(SCENARIOS_DIR.glob("*.xosc"))
    today = datetime.now().date()
    
    scenarios_today = sum(
        1 for s in scenarios 
        if datetime.fromtimestamp(s.stat().st_mtime).date() == today
    )
    
    # Count weather types from filenames
    weather_counts = {}
    edge_counts = {}
    
    for s in scenarios:
        parts = s.stem.split("_")
        if len(parts) > 2:
            w = parts[2]
            weather_counts[w] = weather_counts.get(w, 0) + 1
    
    return StatsResponse(
        total_scenarios=len(scenarios),
        scenarios_today=scenarios_today,
        weather_coverage=weather_counts,
        edge_case_coverage=edge_counts,
    )


@app.post("/api/generate", response_model=ScenarioResponse)
def generate_scenario(request: GenerateRequest):
    """Generate a single scenario from parameters."""
    try:
        # Map parameters
        weather = map_weather(request.weather)
        time_of_day = map_time(request.time_of_day)
        traffic = map_traffic(request.traffic_density)
        edge_case = map_edge_case(request.edge_case)
        road_network = map_road_to_network(request.road_type)
        
        # Generate vehicles based on traffic
        vehicles = []
        vehicle_count = request.traffic_density // 20  # 0-5 vehicles
        for i in range(vehicle_count):
            vehicles.append(Vehicle(
                name=f"NPC_{i+1}",
                initial_speed=float(request.ego_speed - 10 + (i * 5)),
                lane=i % 2,
                s_position=30.0 + (i * 25),
            ))
        
        # Add pedestrian for pedestrian edge case
        pedestrians = []
        if edge_case == EdgeCaseType.PEDESTRIAN_CROSSING:
            pedestrians.append(Pedestrian(
                name="Pedestrian_1",
                s_position=60.0,
                lateral_offset=4.0,
                crossing=True,
            ))
        
        # Build scenario name
        name = request.name or f"{request.road_type}_{request.weather}_{request.edge_case}"
        
        # Create config
        config = ScenarioConfig(
            name=name,
            description=f"Generated scenario: {weather.value}, {time_of_day.value}, {edge_case.value}",
            road_network=road_network,
            weather=weather,
            time_of_day=time_of_day,
            traffic_density=traffic,
            edge_case=edge_case,
            ego_speed=float(request.ego_speed),
            duration=30.0,
            vehicles=vehicles,
            pedestrians=pedestrians,
        )
        
        # Generate
        output_path = generator.generate(config)
        
        return ScenarioResponse(
            id=Path(output_path).stem,
            filename=Path(output_path).name,
            path=str(output_path),
            weather=request.weather,
            time_of_day=request.time_of_day,
            edge_case=request.edge_case,
            ego_speed=request.ego_speed,
            created_at=datetime.now().isoformat(),
            valid=True,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/ai", response_model=ScenarioResponse)
def generate_from_prompt(request: AIGenerateRequest):
    """Generate scenario from natural language description."""
    try:
        # Parse prompt
        params = generate_llm_scenario_description(request.prompt)
        
        # Generate scenario
        path = ai_generator.generate_scenario(
            weather=params.get("weather"),
            time_of_day=params.get("time_of_day"),
            edge_case=params.get("edge_case"),
            custom_name="ai_generated",
        )
        
        return ScenarioResponse(
            id=Path(path).stem,
            filename=Path(path).name,
            path=path,
            weather=params.get("weather", WeatherType.CLEAR).value,
            time_of_day=params.get("time_of_day", TimeOfDay.NOON).value,
            edge_case=params.get("edge_case", EdgeCaseType.NONE).value,
            ego_speed=params.get("ego_speed", 60),
            created_at=datetime.now().isoformat(),
            valid=True,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/batch")
def generate_batch(request: BatchGenerateRequest):
    """Generate multiple scenarios."""
    try:
        paths = ai_generator.generate_batch(
            count=request.count,
            template_name=request.template,
            include_all_weather=request.include_all_weather,
            include_all_times=request.include_all_times,
            include_all_edge_cases=request.include_all_edge_cases,
        )
        
        scenarios = []
        for path in paths:
            meta = get_scenario_metadata(Path(path))
            scenarios.append(ScenarioResponse(**meta))
        
        return {
            "generated": len(paths),
            "scenarios": scenarios,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scenarios", response_model=ScenarioListResponse)
def list_scenarios(limit: int = 50, offset: int = 0):
    """List all generated scenarios."""
    all_files = sorted(
        SCENARIOS_DIR.glob("*.xosc"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    scenarios = []
    for filepath in all_files[offset:offset + limit]:
        meta = get_scenario_metadata(filepath)
        scenarios.append(ScenarioResponse(**meta))
    
    return ScenarioListResponse(
        scenarios=scenarios,
        total=len(all_files),
    )


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    """Get scenario details and content."""
    filepath = SCENARIOS_DIR / f"{scenario_id}.xosc"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    meta = get_scenario_metadata(filepath)
    content = filepath.read_text()
    
    return {
        **meta,
        "content": content,
    }


@app.get("/api/scenarios/{scenario_id}/download")
def download_scenario(scenario_id: str):
    """Download scenario file."""
    filepath = SCENARIOS_DIR / f"{scenario_id}.xosc"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return FileResponse(
        filepath,
        media_type="application/xml",
        filename=filepath.name,
    )


@app.delete("/api/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str):
    """Delete a scenario."""
    filepath = SCENARIOS_DIR / f"{scenario_id}.xosc"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    filepath.unlink()
    return {"deleted": scenario_id}


@app.get("/api/scenarios/{scenario_id}/video")
def get_scenario_video(scenario_id: str):
    """Download recorded video for a scenario."""
    video_path = RECORDINGS_DIR / f"{scenario_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found. Run the scenario first.")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{scenario_id}.mp4",
    )


@app.get("/api/scenarios/{scenario_id}/video/status")
def get_video_status(scenario_id: str):
    """Check if video exists for a scenario."""
    video_path = RECORDINGS_DIR / f"{scenario_id}.mp4"
    
    if video_path.exists():
        stat = video_path.stat()
        return {
            "available": True,
            "path": str(video_path),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    
    return {"available": False}


# Store last test result for report generation
last_test_result: Optional[dict] = None


@app.get("/api/scenarios/{scenario_id}/report")
def get_scenario_report(scenario_id: str):
    """Get detailed test report for a scenario."""
    global last_test_result, scenario_state
    
    filepath = SCENARIOS_DIR / f"{scenario_id}.xosc"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    meta = get_scenario_metadata(filepath)
    
    # Get last run result if available
    run_result = None
    if scenario_state.get("scenario_id") == scenario_id and scenario_state.get("result"):
        run_result = scenario_state["result"]
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "scenario": {
            "id": meta["id"],
            "filename": meta["filename"],
            "weather": meta["weather"],
            "time_of_day": meta["time_of_day"],
            "edge_case": meta.get("edge_case", "unknown"),
            "ego_speed": meta.get("ego_speed", 60),
            "created_at": meta["created_at"],
        },
        "test_results": run_result,
        "analysis": {
            "passed": run_result.get("success", False) if run_result else None,
            "collision_severity": "high" if run_result and run_result.get("collisions", 0) > 10 else "low" if run_result else None,
            "recommendations": [],
        }
    }
    
    # Add recommendations based on results
    if run_result:
        if run_result.get("collisions", 0) > 0:
            report["analysis"]["recommendations"].append(
                "High collision count detected. Consider adjusting autopilot parameters or filtering minor lane marker contacts."
            )
        if run_result.get("duration", 0) < 10:
            report["analysis"]["recommendations"].append(
                "Short scenario duration. Verify scenario completed successfully."
            )
    
    return report


@app.get("/api/templates")
def list_templates():
    """List available scenario templates."""
    from ai_generator import SCENARIO_TEMPLATES
    return {
        "templates": [
            {
                "id": name,
                "description": t["description"],
                "road_network": t["road_network"],
                "speed_range": t["ego_speed_range"],
            }
            for name, t in SCENARIO_TEMPLATES.items()
        ]
    }


@app.get("/api/options")
def list_options():
    """List all available options for generation."""
    return {
        "weather": [w.value for w in WeatherType],
        "time_of_day": [t.value for t in TimeOfDay],
        "traffic_density": [d.value for d in TrafficDensity],
        "edge_cases": [e.value for e in EdgeCaseType],
    }


# ============ CARLA Integration ============

from carla_integration.runner import CarlaScenarioRunner, CARLA_AVAILABLE
from carla_integration.camera_streamer import CameraStreamer, SpectatorStreamer

# Global CARLA runner instance
carla_runner: Optional[CarlaScenarioRunner] = None
carla_connected = False


@app.get("/api/carla/status")
def get_carla_status():
    """Check CARLA server status."""
    global carla_runner, carla_connected
    
    # Try to check if CARLA is available
    available = False
    if CARLA_AVAILABLE:
        try:
            import carla
            test_client = carla.Client("localhost", 2000)
            test_client.set_timeout(2.0)
            test_client.get_server_version()
            available = True
        except:
            available = False
    
    return {
        "available": available,
        "connected": carla_connected,
        "host": "localhost",
        "port": 2000,
        "carla_package": CARLA_AVAILABLE,
    }


@app.post("/api/carla/connect")
def connect_carla(retries: int = 3, timeout: int = 10):
    """Connect to CARLA server with retry logic."""
    global carla_runner, carla_connected
    
    if not CARLA_AVAILABLE:
        # Mock mode for development
        carla_runner = CarlaScenarioRunner()
        carla_connected = True
        return {
            "connected": True,
            "message": "Connected in mock mode (CARLA package not installed)",
        }
    
    last_error = None
    for attempt in range(retries):
        try:
            carla_runner = CarlaScenarioRunner(host="localhost", port=2000, timeout=timeout)
            if carla_runner.connect():
                carla_connected = True
                return {
                    "connected": True,
                    "message": f"Connected to CARLA server at localhost:2000 (attempt {attempt + 1})",
                }
            else:
                last_error = "Connection returned False"
        except Exception as e:
            last_error = str(e)
            print(f"CARLA connect attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2)  # Wait before retry
    
    raise HTTPException(
        status_code=503, 
        detail=f"Failed to connect to CARLA after {retries} attempts: {last_error}"
    )


@app.post("/api/carla/disconnect")
def disconnect_carla():
    """Disconnect from CARLA server."""
    global carla_runner, carla_connected
    
    carla_runner = None
    carla_connected = False
    
    return {
        "connected": False,
        "message": "Disconnected from CARLA",
    }


# Track running scenario state
scenario_state = {
    "running": False,
    "scenario_id": None,
    "started_at": None,
    "result": None,
    "error": None,
}
scenario_thread: Optional[threading.Thread] = None


def _run_scenario_thread(filepath: str, scenario_id: str):
    """Background thread to run scenario."""
    global scenario_state, carla_runner, camera_streamer
    
    start_time = time.time()
    max_runtime = 120  # 2 minute max runtime
    video_path = None
    
    try:
        # Verify CARLA connection before starting
        if carla_runner is None or carla_runner.world is None:
            scenario_state["error"] = "CARLA connection lost before scenario start"
            scenario_state["running"] = False
            return
        
        # Clear any existing ego vehicle reference
        carla_runner.ego_vehicle = None
        
        # Start scenario in a way that allows camera to attach mid-run
        # We'll run the scenario in chunks to allow camera attachment
        import threading
        
        scenario_result = [None]  # Use list to allow modification in nested function
        
        def run_scenario():
            scenario_result[0] = carla_runner.run_scenario(filepath)
        
        # Start scenario in separate thread
        scenario_thread = threading.Thread(target=run_scenario)
        scenario_thread.start()
        
        # Poll for ego vehicle and start camera once available
        camera_started = False
        recording_started = False
        for attempt in range(30):  # Try for 30 seconds
            time.sleep(1)
            
            # Check if scenario already finished (error case)
            if not scenario_thread.is_alive() and scenario_result[0] is not None:
                break
                
            try:
                # Check for ego vehicle from runner
                if carla_runner.ego_vehicle is not None:
                    world = carla_runner.world
                    if world is not None:
                        camera_streamer = CameraStreamer(
                            world=world,
                            vehicle=carla_runner.ego_vehicle,
                            width=800,
                            height=600,
                            camera_type='chase'
                        )
                        camera_streamer.start()
                        camera_started = True
                        print(f"Camera attached to ego vehicle on attempt {attempt + 1}")
                        
                        # Start recording immediately after camera starts
                        if camera_streamer.start_recording(str(RECORDINGS_DIR), scenario_id):
                            recording_started = True
                            print(f"Video recording started for {scenario_id}")
                        
                        break
            except Exception as e:
                print(f"Camera start attempt {attempt + 1} failed: {e}")
        
        if not camera_started:
            print("Warning: Could not start camera, continuing without streaming/recording")
        
        # Wait for scenario to complete
        scenario_thread.join(timeout=max_runtime)
        
        if scenario_thread.is_alive():
            print("Scenario thread still running after timeout")
            scenario_state["error"] = f"Scenario timed out after {max_runtime}s"
            scenario_state["running"] = False
            return
        
        # Get result
        result = scenario_result[0]
        if result is None:
            scenario_state["error"] = "Scenario returned no result"
            scenario_state["running"] = False
            return
            
        # Process result
        try:
            # Stop recording and encode video before storing result
            if camera_streamer and recording_started:
                print("Encoding video...")
                video_path = camera_streamer.stop_recording()
                if video_path:
                    print(f"Video saved: {video_path}")
            
            scenario_state["result"] = {
                "success": result.success,
                "duration": result.duration_seconds,
                "collisions": result.collision_count,
                "error": result.error_message,
                "video_path": video_path,
            }
        except Exception as e:
            elapsed = time.time() - start_time
            if elapsed >= max_runtime:
                scenario_state["error"] = f"Scenario timed out after {max_runtime}s"
            else:
                scenario_state["error"] = f"Scenario execution failed: {str(e)}"
                
    except Exception as e:
        scenario_state["error"] = f"Unexpected error: {str(e)}"
    finally:
        scenario_state["running"] = False
        # Clear ego vehicle reference
        if carla_runner:
            carla_runner.ego_vehicle = None
        # Stop camera safely (will also stop recording if still active)
        if camera_streamer:
            try:
                camera_streamer.stop()
            except Exception as e:
                print(f"Camera stop error (ignored): {e}")
            camera_streamer = None


@app.post("/api/carla/run/{scenario_id}")
def run_scenario_in_carla(scenario_id: str, background_tasks: BackgroundTasks):
    """Start a scenario in CARLA (async)."""
    global carla_runner, carla_connected, scenario_state, scenario_thread
    
    if not carla_connected or carla_runner is None:
        raise HTTPException(status_code=400, detail="Not connected to CARLA")
    
    if scenario_state["running"]:
        raise HTTPException(status_code=400, detail="A scenario is already running")
    
    filepath = SCENARIOS_DIR / f"{scenario_id}.xosc"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Reset state
    scenario_state = {
        "running": True,
        "scenario_id": scenario_id,
        "started_at": time.time(),
        "result": None,
        "error": None,
    }
    
    # Start scenario in background thread
    scenario_thread = threading.Thread(
        target=_run_scenario_thread,
        args=(str(filepath), scenario_id)
    )
    scenario_thread.start()
    
    return {
        "started": True,
        "scenario_id": scenario_id,
        "message": f"Started {filepath.name}",
    }


@app.get("/api/carla/run/status")
def get_scenario_status():
    """Get current scenario run status."""
    global scenario_state
    
    elapsed = 0
    if scenario_state["started_at"]:
        elapsed = time.time() - scenario_state["started_at"]
    
    # Check for video availability
    video_available = False
    if scenario_state["scenario_id"]:
        video_path = RECORDINGS_DIR / f"{scenario_state['scenario_id']}.mp4"
        video_available = video_path.exists()
    
    return {
        "running": scenario_state["running"],
        "scenario_id": scenario_state["scenario_id"],
        "elapsed_seconds": elapsed,
        "result": scenario_state["result"],
        "error": scenario_state["error"],
        "video_available": video_available,
    }


@app.post("/api/carla/stop")
def stop_carla_scenario():
    """Stop current running scenario."""
    global carla_runner
    
    # In future: implement actual stop logic
    return {
        "stopped": True,
        "message": "Scenario stopped",
    }


# ============ Camera Streaming ============

camera_streamer: Optional[CameraStreamer] = None


@app.post("/api/carla/camera/start")
def start_camera(camera_type: str = "chase"):
    """Start camera streaming from CARLA."""
    global camera_streamer, carla_runner, carla_connected
    
    if not carla_connected or carla_runner is None:
        raise HTTPException(status_code=400, detail="Not connected to CARLA")
    
    if not CARLA_AVAILABLE:
        raise HTTPException(status_code=400, detail="CARLA not available")
    
    try:
        import carla
        
        # Get ego vehicle from world
        world = carla_runner.world
        if world is None:
            raise HTTPException(status_code=400, detail="CARLA world not available")
        
        # Find ego vehicle (usually named 'hero' or first vehicle)
        vehicles = world.get_actors().filter('vehicle.*')
        if len(vehicles) == 0:
            raise HTTPException(status_code=400, detail="No vehicles in scene")
        
        ego_vehicle = vehicles[0]  # Take first vehicle as ego
        
        # Create and start camera streamer
        camera_streamer = CameraStreamer(
            world=world,
            vehicle=ego_vehicle,
            width=800,
            height=600,
            camera_type=camera_type
        )
        
        if camera_streamer.start():
            return {"started": True, "camera_type": camera_type}
        else:
            raise HTTPException(status_code=500, detail="Failed to start camera")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/carla/camera/stop")
def stop_camera():
    """Stop camera streaming."""
    global camera_streamer
    
    if camera_streamer:
        camera_streamer.stop()
        camera_streamer = None
    
    return {"stopped": True}


@app.get("/api/carla/camera/frame")
def get_camera_frame():
    """Get single camera frame as base64 JPEG."""
    global camera_streamer
    
    if camera_streamer is None:
        # Return empty response instead of error - allows frontend to keep polling
        return {"frame": None, "status": "camera_not_started"}
    
    try:
        frame = camera_streamer.get_frame_base64()
        if frame is None:
            return {"frame": None, "status": "no_frame_yet"}
        return {"frame": frame, "status": "ok"}
    except Exception as e:
        return {"frame": None, "status": "error", "error": str(e)}


@app.websocket("/ws/carla/stream")
async def websocket_camera_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time camera streaming."""
    global camera_streamer
    
    await websocket.accept()
    
    try:
        while True:
            if camera_streamer:
                frame = camera_streamer.get_frame_base64()
                if frame:
                    await websocket.send_json({"frame": frame})
            
            # ~30 FPS
            await asyncio.sleep(0.033)
            
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.post("/api/carla/camera/type/{camera_type}")
def set_camera_type(camera_type: str):
    """Change camera view type (chase, hood, bird)."""
    global camera_streamer
    
    if camera_streamer is None:
        raise HTTPException(status_code=400, detail="Camera not started")
    
    camera_streamer.set_camera_type(camera_type)
    return {"camera_type": camera_type}


# ============ Spectator Camera (Preview Mode) ============

spectator_streamer: Optional[SpectatorStreamer] = None


@app.post("/api/carla/spectator/start")
def start_spectator_camera(location: str = "overview"):
    """Start spectator camera for preview (no vehicle needed)."""
    global spectator_streamer, carla_runner, carla_connected
    
    if not carla_connected or carla_runner is None:
        raise HTTPException(status_code=400, detail="Not connected to CARLA")
    
    if not CARLA_AVAILABLE:
        raise HTTPException(status_code=400, detail="CARLA not available")
    
    try:
        world = carla_runner.world
        if world is None:
            raise HTTPException(status_code=400, detail="CARLA world not available")
        
        # Stop existing spectator if running
        if spectator_streamer:
            spectator_streamer.stop()
        
        # Create and start spectator camera
        spectator_streamer = SpectatorStreamer(
            world=world,
            width=800,
            height=600
        )
        
        if spectator_streamer.start(location=location):
            return {"started": True, "location": location}
        else:
            raise HTTPException(status_code=500, detail="Failed to start spectator camera")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/carla/spectator/stop")
def stop_spectator_camera():
    """Stop spectator camera."""
    global spectator_streamer
    
    if spectator_streamer:
        spectator_streamer.stop()
        spectator_streamer = None
    
    return {"stopped": True}


@app.get("/api/carla/spectator/frame")
def get_spectator_frame():
    """Get single spectator frame as base64 JPEG."""
    global spectator_streamer
    
    if spectator_streamer is None:
        return {"frame": None, "status": "spectator_not_started"}
    
    try:
        frame = spectator_streamer.get_frame_base64()
        if frame is None:
            return {"frame": None, "status": "no_frame_yet"}
        return {"frame": frame, "status": "ok"}
    except Exception as e:
        return {"frame": None, "status": "error", "error": str(e)}


@app.post("/api/carla/spectator/location/{location}")
def set_spectator_location(location: str):
    """Change spectator camera location (overview, street, spectator)."""
    global spectator_streamer
    
    if spectator_streamer is None:
        raise HTTPException(status_code=400, detail="Spectator camera not started")
    
    spectator_streamer.set_location(location)
    return {"location": location}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
