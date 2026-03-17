#!/usr/bin/env python3
"""
CARLA Simulator Integration

Executes OpenSCENARIO files in CARLA simulator and collects test results.

Requirements:
    - CARLA simulator running (0.9.13+)
    - Python CARLA package: pip install carla
    - ScenarioRunner: https://github.com/carla-simulator/scenario_runner
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

# Check for CARLA availability
try:
    import carla
    CARLA_AVAILABLE = True
except ImportError:
    CARLA_AVAILABLE = False
    print("Warning: CARLA not installed. Install with: pip install carla")


@dataclass
class ScenarioResult:
    """Result from running a scenario in CARLA."""
    scenario_file: str
    success: bool
    duration_seconds: float
    collision_count: int = 0
    lane_invasion_count: int = 0
    traffic_light_violations: int = 0
    distance_traveled: float = 0.0
    average_speed: float = 0.0
    min_ttc: Optional[float] = None  # Time to collision
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metrics: Dict[str, Any] = field(default_factory=dict)


class CarlaScenarioRunner:
    """
    Runs OpenSCENARIO files in CARLA simulator.
    
    Can work in two modes:
    1. Direct API mode (requires CARLA Python package)
    2. ScenarioRunner CLI mode (uses external scenario_runner.py)
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 2000,
        scenario_runner_path: Optional[str] = None,
        timeout: int = 60,
    ):
        self.host = host
        self.port = port
        self.scenario_runner_path = scenario_runner_path
        self.timeout = timeout
        self.client = None
        self.world = None
        
    def connect(self) -> bool:
        """Connect to CARLA simulator."""
        if not CARLA_AVAILABLE:
            print("CARLA package not available")
            return False
            
        try:
            self.client = carla.Client(self.host, self.port)
            self.client.set_timeout(10.0)
            self.world = self.client.get_world()
            print(f"Connected to CARLA at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to CARLA: {e}")
            return False
            
    def run_scenario(self, scenario_path: str) -> ScenarioResult:
        """
        Execute a scenario and collect results.
        
        Args:
            scenario_path: Path to .xosc file
            
        Returns:
            ScenarioResult with metrics
        """
        path = Path(scenario_path)
        if not path.exists():
            return ScenarioResult(
                scenario_file=str(path),
                success=False,
                duration_seconds=0,
                error_message=f"Scenario file not found: {path}"
            )
            
        # Try ScenarioRunner CLI first (more reliable)
        if self.scenario_runner_path:
            return self._run_via_scenario_runner(path)
        elif CARLA_AVAILABLE and self.client:
            return self._run_direct(path)
        else:
            return self._run_mock(path)
            
    def _run_via_scenario_runner(self, scenario_path: Path) -> ScenarioResult:
        """Run scenario using CARLA ScenarioRunner."""
        start_time = time.time()
        
        cmd = [
            "python", self.scenario_runner_path,
            "--openscenario", str(scenario_path),
            "--host", self.host,
            "--port", str(self.port),
            "--timeout", str(self.timeout),
            "--output-dir", str(scenario_path.parent / "results"),
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 30,
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # Parse output for metrics
            metrics = self._parse_scenario_runner_output(result.stdout)
            
            return ScenarioResult(
                scenario_file=str(scenario_path),
                success=success,
                duration_seconds=duration,
                collision_count=metrics.get("collisions", 0),
                lane_invasion_count=metrics.get("lane_invasions", 0),
                traffic_light_violations=metrics.get("red_light", 0),
                error_message=result.stderr if not success else None,
                metrics=metrics,
            )
            
        except subprocess.TimeoutExpired:
            return ScenarioResult(
                scenario_file=str(scenario_path),
                success=False,
                duration_seconds=self.timeout,
                error_message="Scenario execution timed out",
            )
        except Exception as e:
            return ScenarioResult(
                scenario_file=str(scenario_path),
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )
            
    def _run_direct(self, scenario_path: Path) -> ScenarioResult:
        """Run scenario using direct CARLA API (simplified)."""
        # This is a simplified version - full implementation would need
        # to parse the OpenSCENARIO file and execute actions
        
        start_time = time.time()
        
        try:
            # Load the appropriate map
            # In full implementation, read from scenario file
            self.client.load_world("Town01")
            time.sleep(2)  # Wait for world to load
            
            # Set up spectator for viewing
            spectator = self.world.get_spectator()
            
            # Spawn ego vehicle
            blueprint_library = self.world.get_blueprint_library()
            vehicle_bp = blueprint_library.filter("model3")[0]
            
            spawn_points = self.world.get_map().get_spawn_points()
            if spawn_points:
                spawn_point = spawn_points[0]
                vehicle = self.world.spawn_actor(vehicle_bp, spawn_point)
                
                # Enable autopilot for basic testing
                vehicle.set_autopilot(True)
                
                # Run for scenario duration
                duration = 30  # Default duration
                time.sleep(duration)
                
                # Collect basic metrics
                velocity = vehicle.get_velocity()
                speed = (velocity.x**2 + velocity.y**2 + velocity.z**2)**0.5
                
                # Cleanup
                vehicle.destroy()
                
                return ScenarioResult(
                    scenario_file=str(scenario_path),
                    success=True,
                    duration_seconds=time.time() - start_time,
                    average_speed=speed * 3.6,  # Convert to km/h
                    metrics={"note": "Basic execution - full metrics require ScenarioRunner"},
                )
            else:
                return ScenarioResult(
                    scenario_file=str(scenario_path),
                    success=False,
                    duration_seconds=0,
                    error_message="No spawn points available",
                )
                
        except Exception as e:
            return ScenarioResult(
                scenario_file=str(scenario_path),
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )
            
    def _run_mock(self, scenario_path: Path) -> ScenarioResult:
        """Mock execution for testing without CARLA."""
        import random
        
        # Simulate execution
        time.sleep(0.5)
        
        return ScenarioResult(
            scenario_file=str(scenario_path),
            success=True,
            duration_seconds=30.0,
            collision_count=random.randint(0, 1),
            lane_invasion_count=random.randint(0, 3),
            traffic_light_violations=0,
            distance_traveled=random.uniform(500, 1500),
            average_speed=random.uniform(40, 80),
            metrics={"note": "Mock execution - CARLA not connected"},
        )
        
    def _parse_scenario_runner_output(self, output: str) -> Dict[str, Any]:
        """Parse ScenarioRunner output for metrics."""
        metrics = {}
        
        # Example parsing - adjust based on actual ScenarioRunner output
        lines = output.split("\n")
        for line in lines:
            if "Collision" in line:
                metrics["collisions"] = metrics.get("collisions", 0) + 1
            if "Lane" in line and "invasion" in line.lower():
                metrics["lane_invasions"] = metrics.get("lane_invasions", 0) + 1
            if "Red light" in line:
                metrics["red_light"] = metrics.get("red_light", 0) + 1
                
        return metrics
        
    def run_batch(
        self,
        scenario_dir: str,
        pattern: str = "*.xosc",
    ) -> List[ScenarioResult]:
        """
        Run all scenarios in a directory.
        
        Args:
            scenario_dir: Directory containing .xosc files
            pattern: Glob pattern for scenario files
            
        Returns:
            List of ScenarioResults
        """
        results = []
        scenario_path = Path(scenario_dir)
        
        for scenario_file in sorted(scenario_path.glob(pattern)):
            print(f"\nRunning: {scenario_file.name}")
            result = self.run_scenario(str(scenario_file))
            results.append(result)
            
            status = "✅" if result.success else "❌"
            print(f"  {status} Duration: {result.duration_seconds:.1f}s, "
                  f"Collisions: {result.collision_count}")
                  
        return results
        
    def generate_report(
        self,
        results: List[ScenarioResult],
        output_path: str = "test_report.json",
    ) -> str:
        """Generate JSON report from test results."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(results),
            "passed": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_collisions": sum(r.collision_count for r in results),
            "total_lane_invasions": sum(r.lane_invasion_count for r in results),
            "scenarios": [
                {
                    "file": r.scenario_file,
                    "success": r.success,
                    "duration": r.duration_seconds,
                    "collisions": r.collision_count,
                    "lane_invasions": r.lane_invasion_count,
                    "error": r.error_message,
                    "metrics": r.metrics,
                }
                for r in results
            ]
        }
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
            
        return output_path


def main():
    """Demo CARLA integration."""
    print("=== CARLA Scenario Runner Demo ===\n")
    
    runner = CarlaScenarioRunner()
    
    # Check for CARLA connection
    if CARLA_AVAILABLE:
        connected = runner.connect()
        if not connected:
            print("Running in mock mode (CARLA not available)")
    else:
        print("Running in mock mode (CARLA package not installed)")
        
    # Run scenarios from directory
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    if scenarios_dir.exists():
        results = runner.run_batch(str(scenarios_dir))
        
        if results:
            report_path = runner.generate_report(results)
            print(f"\n📊 Report saved to: {report_path}")
    else:
        print(f"No scenarios found in {scenarios_dir}")
        print("Run 'python cli.py generate --count 5' first")


if __name__ == "__main__":
    main()
