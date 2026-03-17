#!/usr/bin/env python3
"""
AI-Powered Scenario Generator

Uses generative AI to create diverse, realistic driving scenarios
for ADAS validation testing.
"""

import json
import random
from typing import List, Optional
from dataclasses import dataclass

from scenario_generator import (
    ScenarioConfig, Vehicle, Pedestrian,
    WeatherType, TimeOfDay, TrafficDensity, EdgeCaseType,
    OpenScenarioGenerator
)


# Scenario templates for different test categories
SCENARIO_TEMPLATES = {
    "highway_cruise": {
        "description": "Highway cruising scenario with varying traffic",
        "road_network": "Town04",
        "ego_speed_range": (80, 130),
        "possible_weather": [WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.RAINY],
        "possible_times": [TimeOfDay.MORNING, TimeOfDay.NOON, TimeOfDay.AFTERNOON],
        "possible_edge_cases": [EdgeCaseType.NONE, EdgeCaseType.CUT_IN, EdgeCaseType.LANE_CHANGE],
    },
    "urban_intersection": {
        "description": "Urban intersection scenario with pedestrians",
        "road_network": "Town01",
        "ego_speed_range": (30, 50),
        "possible_weather": [WeatherType.CLEAR, WeatherType.CLOUDY, WeatherType.RAINY, WeatherType.FOGGY],
        "possible_times": list(TimeOfDay),
        "possible_edge_cases": [EdgeCaseType.PEDESTRIAN_CROSSING, EdgeCaseType.CYCLIST, EdgeCaseType.INTERSECTION],
    },
    "adverse_weather": {
        "description": "Driving in adverse weather conditions",
        "road_network": "Town02",
        "ego_speed_range": (30, 70),
        "possible_weather": [WeatherType.RAINY, WeatherType.FOGGY, WeatherType.SNOWY],
        "possible_times": list(TimeOfDay),
        "possible_edge_cases": [EdgeCaseType.EMERGENCY_BRAKE, EdgeCaseType.CUT_IN],
    },
    "night_driving": {
        "description": "Night driving with reduced visibility",
        "road_network": "Town03",
        "ego_speed_range": (40, 80),
        "possible_weather": [WeatherType.CLEAR, WeatherType.FOGGY],
        "possible_times": [TimeOfDay.EVENING, TimeOfDay.NIGHT],
        "possible_edge_cases": [EdgeCaseType.PEDESTRIAN_CROSSING, EdgeCaseType.ANIMAL_CROSSING],
    },
    "emergency_response": {
        "description": "Emergency braking and collision avoidance",
        "road_network": "Town01",
        "ego_speed_range": (40, 80),
        "possible_weather": list(WeatherType),
        "possible_times": list(TimeOfDay),
        "possible_edge_cases": [EdgeCaseType.EMERGENCY_BRAKE, EdgeCaseType.CUT_IN, EdgeCaseType.CUT_OUT],
    },
}


class AIScenarioGenerator:
    """
    Generates diverse scenarios using AI-driven parameter selection.
    
    This class uses templates and randomization to create varied scenarios.
    Can be extended to use actual LLM APIs for more sophisticated generation.
    """
    
    def __init__(self, output_dir: str = "scenarios", use_llm: bool = False):
        self.output_dir = output_dir
        self.use_llm = use_llm
        self.generator = OpenScenarioGenerator(output_dir)
        
    def generate_scenario(
        self,
        template_name: Optional[str] = None,
        weather: Optional[WeatherType] = None,
        time_of_day: Optional[TimeOfDay] = None,
        traffic_density: Optional[TrafficDensity] = None,
        edge_case: Optional[EdgeCaseType] = None,
        custom_name: Optional[str] = None,
    ) -> str:
        """
        Generate a single scenario with optional overrides.
        
        Args:
            template_name: Base template to use (random if not specified)
            weather: Override weather condition
            time_of_day: Override time of day
            traffic_density: Override traffic density
            edge_case: Override edge case type
            custom_name: Custom scenario name
            
        Returns:
            Path to generated .xosc file
        """
        # Select template
        if template_name and template_name in SCENARIO_TEMPLATES:
            template = SCENARIO_TEMPLATES[template_name]
        else:
            template_name = random.choice(list(SCENARIO_TEMPLATES.keys()))
            template = SCENARIO_TEMPLATES[template_name]
            
        # Generate parameters
        selected_weather = weather or random.choice(template["possible_weather"])
        selected_time = time_of_day or random.choice(template["possible_times"])
        selected_density = traffic_density or random.choice(list(TrafficDensity))
        selected_edge_case = edge_case or random.choice(template["possible_edge_cases"])
        ego_speed = random.uniform(*template["ego_speed_range"])
        
        # Generate name
        if custom_name:
            name = custom_name
        else:
            name = f"{template_name}_{selected_weather.value}_{selected_time.value}"
            
        # Create vehicles based on traffic density
        vehicles = self._generate_traffic(selected_density, selected_edge_case)
        
        # Create pedestrians for relevant edge cases
        pedestrians = self._generate_pedestrians(selected_edge_case)
        
        # Build config
        config = ScenarioConfig(
            name=name,
            description=f"AI-generated {template['description']}. "
                       f"Weather: {selected_weather.value}, "
                       f"Time: {selected_time.value}, "
                       f"Edge case: {selected_edge_case.value}",
            road_network=template["road_network"],
            weather=selected_weather,
            time_of_day=selected_time,
            traffic_density=selected_density,
            edge_case=selected_edge_case,
            ego_speed=ego_speed,
            duration=30.0,
            vehicles=vehicles,
            pedestrians=pedestrians,
        )
        
        # Generate OpenSCENARIO file
        output_path = self.generator.generate(config)
        return str(output_path)
        
    def generate_batch(
        self,
        count: int = 10,
        template_name: Optional[str] = None,
        include_all_weather: bool = False,
        include_all_times: bool = False,
        include_all_edge_cases: bool = False,
    ) -> List[str]:
        """
        Generate multiple scenarios for comprehensive testing.
        
        Args:
            count: Number of scenarios to generate
            template_name: Limit to specific template
            include_all_weather: Ensure all weather types are covered
            include_all_times: Ensure all times of day are covered
            include_all_edge_cases: Ensure all edge cases are covered
            
        Returns:
            List of paths to generated .xosc files
        """
        generated = []
        
        # Build coverage sets if requested
        weather_queue = list(WeatherType) if include_all_weather else []
        time_queue = list(TimeOfDay) if include_all_times else []
        edge_queue = list(EdgeCaseType) if include_all_edge_cases else []
        
        for i in range(count):
            weather = weather_queue.pop(0) if weather_queue else None
            time = time_queue.pop(0) if time_queue else None
            edge = edge_queue.pop(0) if edge_queue else None
            
            try:
                path = self.generate_scenario(
                    template_name=template_name,
                    weather=weather,
                    time_of_day=time,
                    edge_case=edge,
                )
                generated.append(path)
                print(f"  [{i+1}/{count}] Generated: {path}")
            except Exception as e:
                print(f"  [{i+1}/{count}] Error: {e}")
                
        return generated
    
    def generate_edge_case_suite(self) -> List[str]:
        """
        Generate a comprehensive suite of edge case scenarios.
        
        Returns:
            List of paths to generated .xosc files
        """
        generated = []
        
        for edge_case in EdgeCaseType:
            if edge_case == EdgeCaseType.NONE:
                continue
                
            # Generate variants for each edge case
            for weather in [WeatherType.CLEAR, WeatherType.RAINY]:
                for time in [TimeOfDay.NOON, TimeOfDay.NIGHT]:
                    try:
                        path = self.generate_scenario(
                            edge_case=edge_case,
                            weather=weather,
                            time_of_day=time,
                            custom_name=f"edge_{edge_case.value}_{weather.value}_{time.value}",
                        )
                        generated.append(path)
                    except Exception as e:
                        print(f"Error generating {edge_case.value}: {e}")
                        
        return generated
        
    def _generate_traffic(self, density: TrafficDensity, 
                         edge_case: EdgeCaseType) -> List[Vehicle]:
        """Generate NPC vehicles based on traffic density."""
        density_counts = {
            TrafficDensity.EMPTY: 0,
            TrafficDensity.SPARSE: 2,
            TrafficDensity.MODERATE: 5,
            TrafficDensity.DENSE: 10,
            TrafficDensity.RUSH_HOUR: 15,
        }
        
        count = density_counts.get(density, 3)
        
        # Always ensure at least one vehicle for vehicle-based edge cases
        if edge_case in [EdgeCaseType.CUT_IN, EdgeCaseType.CUT_OUT, 
                        EdgeCaseType.EMERGENCY_BRAKE, EdgeCaseType.LANE_CHANGE]:
            count = max(count, 1)
            
        vehicles = []
        vehicle_types = ["sedan", "suv", "truck", "van"]
        
        for i in range(count):
            # Position vehicles ahead of ego
            s_position = random.uniform(20, 100) + (i * 30)
            lane = random.choice([-1, 0, 1])  # Adjacent lanes
            speed = random.uniform(40, 80)
            
            # Special positioning for edge cases
            if i == 0 and edge_case == EdgeCaseType.CUT_IN:
                lane = 1  # Start in adjacent lane
                s_position = random.uniform(30, 50)
                speed = 60
            elif i == 0 and edge_case == EdgeCaseType.EMERGENCY_BRAKE:
                lane = 0  # Same lane as ego
                s_position = random.uniform(40, 60)
                speed = 50
                
            vehicles.append(Vehicle(
                name=f"NPC_{i+1}",
                vehicle_type=random.choice(vehicle_types),
                initial_speed=speed,
                lane=lane,
                s_position=s_position,
            ))
            
        return vehicles
        
    def _generate_pedestrians(self, edge_case: EdgeCaseType) -> List[Pedestrian]:
        """Generate pedestrians for relevant edge cases."""
        pedestrians = []
        
        if edge_case == EdgeCaseType.PEDESTRIAN_CROSSING:
            pedestrians.append(Pedestrian(
                name="Pedestrian_1",
                s_position=random.uniform(50, 80),
                lateral_offset=4.0,  # On sidewalk
                walk_speed=1.4,
                crossing=True,
            ))
            # Maybe add a second pedestrian
            if random.random() > 0.5:
                pedestrians.append(Pedestrian(
                    name="Pedestrian_2",
                    s_position=random.uniform(50, 80),
                    lateral_offset=-4.0,  # Other side
                    walk_speed=1.2,
                    crossing=True,
                ))
                
        return pedestrians


def generate_llm_scenario_description(prompt: str) -> dict:
    """
    Use LLM to generate scenario parameters from natural language.
    
    This is a placeholder for actual LLM integration.
    Can be connected to OpenAI, Claude, or local models.
    
    Example prompt: "Create a rainy night scenario with a pedestrian 
    suddenly crossing the road while the ego vehicle is driving at 60 km/h"
    """
    # Placeholder - would call actual LLM API here
    # For now, extract keywords and map to parameters
    
    prompt_lower = prompt.lower()
    
    params = {
        "weather": WeatherType.CLEAR,
        "time_of_day": TimeOfDay.NOON,
        "edge_case": EdgeCaseType.NONE,
        "ego_speed": 50,
    }
    
    # Simple keyword extraction
    if "rain" in prompt_lower:
        params["weather"] = WeatherType.RAINY
    elif "fog" in prompt_lower:
        params["weather"] = WeatherType.FOGGY
    elif "snow" in prompt_lower:
        params["weather"] = WeatherType.SNOWY
        
    if "night" in prompt_lower:
        params["time_of_day"] = TimeOfDay.NIGHT
    elif "morning" in prompt_lower:
        params["time_of_day"] = TimeOfDay.MORNING
    elif "evening" in prompt_lower:
        params["time_of_day"] = TimeOfDay.EVENING
        
    if "pedestrian" in prompt_lower:
        params["edge_case"] = EdgeCaseType.PEDESTRIAN_CROSSING
    elif "cut" in prompt_lower and "in" in prompt_lower:
        params["edge_case"] = EdgeCaseType.CUT_IN
    elif "brake" in prompt_lower or "emergency" in prompt_lower:
        params["edge_case"] = EdgeCaseType.EMERGENCY_BRAKE
        
    # Extract speed if mentioned
    import re
    speed_match = re.search(r'(\d+)\s*km/?h', prompt_lower)
    if speed_match:
        params["ego_speed"] = int(speed_match.group(1))
        
    return params


if __name__ == "__main__":
    print("=== AI Scenario Generator Demo ===\n")
    
    generator = AIScenarioGenerator(output_dir="scenarios")
    
    # Generate a few diverse scenarios
    print("Generating 5 random scenarios...")
    paths = generator.generate_batch(count=5)
    
    print(f"\nGenerated {len(paths)} scenarios")
    for p in paths:
        print(f"  - {p}")
