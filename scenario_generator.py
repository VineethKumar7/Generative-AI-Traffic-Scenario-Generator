#!/usr/bin/env python3
"""
Generative AI Traffic Scenario Generator

Generates OpenSCENARIO-compliant scenario files for ADAS validation testing.
Supports varying traffic densities, weather conditions, and edge cases.
"""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
from lxml import etree
import hashlib


class WeatherType(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    FOGGY = "foggy"
    SNOWY = "snowy"


class TimeOfDay(Enum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class TrafficDensity(Enum):
    EMPTY = "empty"
    SPARSE = "sparse"
    MODERATE = "moderate"
    DENSE = "dense"
    RUSH_HOUR = "rush_hour"


class EdgeCaseType(Enum):
    NONE = "none"
    PEDESTRIAN_CROSSING = "pedestrian_crossing"
    EMERGENCY_BRAKE = "emergency_brake"
    CUT_IN = "cut_in"
    CUT_OUT = "cut_out"
    LANE_CHANGE = "lane_change"
    INTERSECTION = "intersection"
    CYCLIST = "cyclist"
    ANIMAL_CROSSING = "animal_crossing"


@dataclass
class Vehicle:
    """Represents a vehicle in the scenario."""
    name: str
    vehicle_type: str = "car"
    initial_speed: float = 50.0  # km/h
    lane: int = 0
    s_position: float = 0.0  # position along road
    behavior: str = "default"
    
    
@dataclass
class Pedestrian:
    """Represents a pedestrian in the scenario."""
    name: str
    s_position: float = 0.0
    lateral_offset: float = 3.0
    walk_speed: float = 1.4  # m/s
    crossing: bool = False


@dataclass
class ScenarioConfig:
    """Configuration for scenario generation."""
    name: str
    description: str = ""
    road_network: str = "Town01"  # CARLA town or OpenDRIVE file
    weather: WeatherType = WeatherType.CLEAR
    time_of_day: TimeOfDay = TimeOfDay.NOON
    traffic_density: TrafficDensity = TrafficDensity.MODERATE
    edge_case: EdgeCaseType = EdgeCaseType.NONE
    ego_speed: float = 50.0  # km/h
    duration: float = 30.0  # seconds
    vehicles: List[Vehicle] = field(default_factory=list)
    pedestrians: List[Pedestrian] = field(default_factory=list)


class OpenScenarioGenerator:
    """Generates OpenSCENARIO 1.0 compliant XML files."""
    
    OPENSCENARIO_VERSION = "1.0"
    
    def __init__(self, output_dir: Path = Path("scenarios")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate(self, config: ScenarioConfig) -> Path:
        """Generate an OpenSCENARIO file from config."""
        root = self._create_root()
        
        # FileHeader
        self._add_file_header(root, config)
        
        # ParameterDeclarations (empty for now)
        etree.SubElement(root, "ParameterDeclarations")
        
        # CatalogLocations
        self._add_catalog_locations(root)
        
        # RoadNetwork
        self._add_road_network(root, config)
        
        # Entities
        self._add_entities(root, config)
        
        # Storyboard
        self._add_storyboard(root, config)
        
        # Write to file
        scenario_id = hashlib.md5(f"{config.name}{datetime.now()}".encode()).hexdigest()[:8]
        filename = f"scenario_{config.name.lower().replace(' ', '_')}_{scenario_id}.xosc"
        output_path = self.output_dir / filename
        
        tree = etree.ElementTree(root)
        tree.write(str(output_path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        
        return output_path
    
    def _create_root(self) -> etree.Element:
        """Create the root OpenSCENARIO element."""
        nsmap = {
            None: "http://www.w3.org/2001/XMLSchema-instance"
        }
        root = etree.Element("OpenSCENARIO")
        root.set("xmlns", "http://www.asam.net/OpenSCENARIO/1.0")
        return root
    
    def _add_file_header(self, root: etree.Element, config: ScenarioConfig):
        """Add FileHeader element."""
        header = etree.SubElement(root, "FileHeader")
        header.set("revMajor", "1")
        header.set("revMinor", "0")
        header.set("date", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        header.set("description", config.description or f"Generated scenario: {config.name}")
        header.set("author", "Scenario Generator AI")
        
    def _add_catalog_locations(self, root: etree.Element):
        """Add CatalogLocations element."""
        catalogs = etree.SubElement(root, "CatalogLocations")
        
        # Vehicle catalog
        vehicle_cat = etree.SubElement(catalogs, "VehicleCatalog")
        etree.SubElement(vehicle_cat, "Directory").set("path", "catalogs/vehicles")
        
        # Controller catalog
        controller_cat = etree.SubElement(catalogs, "ControllerCatalog")
        etree.SubElement(controller_cat, "Directory").set("path", "catalogs/controllers")
        
    def _add_road_network(self, root: etree.Element, config: ScenarioConfig):
        """Add RoadNetwork element."""
        road_network = etree.SubElement(root, "RoadNetwork")
        
        # Logic file (OpenDRIVE)
        logic_file = etree.SubElement(road_network, "LogicFile")
        logic_file.set("filepath", f"{config.road_network}.xodr")
        
        # Scene graph file (optional)
        scene_file = etree.SubElement(road_network, "SceneGraphFile")
        scene_file.set("filepath", f"{config.road_network}.osgb")
        
    def _add_entities(self, root: etree.Element, config: ScenarioConfig):
        """Add Entities element with ego vehicle and NPCs."""
        entities = etree.SubElement(root, "Entities")
        
        # Ego vehicle
        self._add_vehicle_entity(entities, "Ego", "vehicle.tesla.model3", is_ego=True)
        
        # NPC vehicles
        for vehicle in config.vehicles:
            self._add_vehicle_entity(entities, vehicle.name, f"vehicle.{vehicle.vehicle_type}")
            
        # Pedestrians
        for ped in config.pedestrians:
            self._add_pedestrian_entity(entities, ped.name)
            
    def _add_vehicle_entity(self, entities: etree.Element, name: str, 
                           vehicle_model: str, is_ego: bool = False):
        """Add a vehicle entity."""
        entity = etree.SubElement(entities, "ScenarioObject")
        entity.set("name", name)
        
        vehicle = etree.SubElement(entity, "Vehicle")
        vehicle.set("name", vehicle_model)
        vehicle.set("vehicleCategory", "car")
        
        # Bounding box
        bbox = etree.SubElement(vehicle, "BoundingBox")
        center = etree.SubElement(bbox, "Center")
        center.set("x", "1.5")
        center.set("y", "0.0")
        center.set("z", "0.9")
        dimensions = etree.SubElement(bbox, "Dimensions")
        dimensions.set("width", "2.0")
        dimensions.set("length", "4.5")
        dimensions.set("height", "1.8")
        
        # Performance
        perf = etree.SubElement(vehicle, "Performance")
        perf.set("maxSpeed", "69.44")  # 250 km/h in m/s
        perf.set("maxAcceleration", "10.0")
        perf.set("maxDeceleration", "10.0")
        
        # Axles
        axles = etree.SubElement(vehicle, "Axles")
        front = etree.SubElement(axles, "FrontAxle")
        front.set("maxSteering", "0.5")
        front.set("wheelDiameter", "0.6")
        front.set("trackWidth", "1.8")
        front.set("positionX", "3.1")
        front.set("positionZ", "0.3")
        rear = etree.SubElement(axles, "RearAxle")
        rear.set("maxSteering", "0.0")
        rear.set("wheelDiameter", "0.6")
        rear.set("trackWidth", "1.8")
        rear.set("positionX", "0.0")
        rear.set("positionZ", "0.3")
        
        # Properties
        props = etree.SubElement(vehicle, "Properties")
        prop = etree.SubElement(props, "Property")
        prop.set("name", "type")
        prop.set("value", "ego_vehicle" if is_ego else "npc_vehicle")
        
    def _add_pedestrian_entity(self, entities: etree.Element, name: str):
        """Add a pedestrian entity."""
        entity = etree.SubElement(entities, "ScenarioObject")
        entity.set("name", name)
        
        pedestrian = etree.SubElement(entity, "Pedestrian")
        pedestrian.set("name", "pedestrian.adult")
        pedestrian.set("pedestrianCategory", "pedestrian")
        pedestrian.set("model", "walker.pedestrian.0001")
        pedestrian.set("mass", "75.0")
        
        # Bounding box
        bbox = etree.SubElement(pedestrian, "BoundingBox")
        center = etree.SubElement(bbox, "Center")
        center.set("x", "0.0")
        center.set("y", "0.0")
        center.set("z", "0.9")
        dimensions = etree.SubElement(bbox, "Dimensions")
        dimensions.set("width", "0.5")
        dimensions.set("length", "0.3")
        dimensions.set("height", "1.8")
        
    def _add_storyboard(self, root: etree.Element, config: ScenarioConfig):
        """Add Storyboard element with Init and Story."""
        storyboard = etree.SubElement(root, "Storyboard")
        
        # Init
        self._add_init(storyboard, config)
        
        # Story
        self._add_story(storyboard, config)
        
        # StopTrigger
        stop_trigger = etree.SubElement(storyboard, "StopTrigger")
        cond_group = etree.SubElement(stop_trigger, "ConditionGroup")
        condition = etree.SubElement(cond_group, "Condition")
        condition.set("name", "EndCondition")
        condition.set("delay", "0")
        condition.set("conditionEdge", "rising")
        by_value = etree.SubElement(condition, "ByValueCondition")
        sim_time = etree.SubElement(by_value, "SimulationTimeCondition")
        sim_time.set("value", str(config.duration))
        sim_time.set("rule", "greaterThan")
        
    def _add_init(self, storyboard: etree.Element, config: ScenarioConfig):
        """Add Init element with initial positions and environment."""
        init = etree.SubElement(storyboard, "Init")
        actions = etree.SubElement(init, "Actions")
        
        # Environment action (weather, time of day)
        global_action = etree.SubElement(actions, "GlobalAction")
        env_action = etree.SubElement(global_action, "EnvironmentAction")
        environment = etree.SubElement(env_action, "Environment")
        environment.set("name", f"{config.weather.value}_{config.time_of_day.value}")
        
        # Time of day
        time_elem = etree.SubElement(environment, "TimeOfDay")
        time_elem.set("animation", "false")
        time_elem.set("dateTime", self._get_datetime_for_time(config.time_of_day))
        
        # Weather
        weather = etree.SubElement(environment, "Weather")
        weather.set("cloudState", self._get_cloud_state(config.weather))
        sun = etree.SubElement(weather, "Sun")
        sun.set("intensity", self._get_sun_intensity(config.weather, config.time_of_day))
        sun.set("azimuth", "0.0")
        sun.set("elevation", self._get_sun_elevation(config.time_of_day))
        fog = etree.SubElement(weather, "Fog")
        fog.set("visualRange", self._get_fog_range(config.weather))
        precip = etree.SubElement(weather, "Precipitation")
        precip.set("precipitationType", self._get_precipitation_type(config.weather))
        precip.set("intensity", self._get_precipitation_intensity(config.weather))
        
        # Road condition
        road_cond = etree.SubElement(environment, "RoadCondition")
        road_cond.set("frictionScaleFactor", self._get_friction(config.weather))
        
        # Ego vehicle initial position
        self._add_init_position(actions, "Ego", 0, 0, config.ego_speed)
        
        # NPC vehicles initial positions
        for vehicle in config.vehicles:
            self._add_init_position(actions, vehicle.name, vehicle.lane, 
                                   vehicle.s_position, vehicle.initial_speed)
            
        # Pedestrians initial positions
        for ped in config.pedestrians:
            self._add_init_pedestrian_position(actions, ped)
            
    def _add_init_position(self, actions: etree.Element, entity_name: str, 
                          lane: int, s_pos: float, speed: float):
        """Add initial position action for an entity."""
        private = etree.SubElement(actions, "Private")
        private.set("entityRef", entity_name)
        
        # Teleport action
        private_action = etree.SubElement(private, "PrivateAction")
        teleport = etree.SubElement(private_action, "TeleportAction")
        position = etree.SubElement(teleport, "Position")
        lane_pos = etree.SubElement(position, "LanePosition")
        lane_pos.set("roadId", "1")
        lane_pos.set("laneId", str(lane))
        lane_pos.set("offset", "0.0")
        lane_pos.set("s", str(s_pos))
        
        # Speed action
        private_action2 = etree.SubElement(private, "PrivateAction")
        longitudinal = etree.SubElement(private_action2, "LongitudinalAction")
        speed_action = etree.SubElement(longitudinal, "SpeedAction")
        speed_target = etree.SubElement(speed_action, "SpeedActionTarget")
        abs_target = etree.SubElement(speed_target, "AbsoluteTargetSpeed")
        abs_target.set("value", str(speed / 3.6))  # Convert km/h to m/s
        speed_dynamics = etree.SubElement(speed_action, "SpeedActionDynamics")
        speed_dynamics.set("dynamicsShape", "step")
        speed_dynamics.set("value", "0")
        speed_dynamics.set("dynamicsDimension", "time")
        
    def _add_init_pedestrian_position(self, actions: etree.Element, ped: Pedestrian):
        """Add initial position for pedestrian."""
        private = etree.SubElement(actions, "Private")
        private.set("entityRef", ped.name)
        
        private_action = etree.SubElement(private, "PrivateAction")
        teleport = etree.SubElement(private_action, "TeleportAction")
        position = etree.SubElement(teleport, "Position")
        lane_pos = etree.SubElement(position, "LanePosition")
        lane_pos.set("roadId", "1")
        lane_pos.set("laneId", "0")
        lane_pos.set("offset", str(ped.lateral_offset))
        lane_pos.set("s", str(ped.s_position))
        
    def _add_story(self, storyboard: etree.Element, config: ScenarioConfig):
        """Add Story element with maneuvers based on edge case."""
        story = etree.SubElement(storyboard, "Story")
        story.set("name", "MainStory")
        
        act = etree.SubElement(story, "Act")
        act.set("name", "MainAct")
        
        # Add maneuver group based on edge case
        if config.edge_case != EdgeCaseType.NONE:
            self._add_edge_case_maneuver(act, config)
        else:
            self._add_default_maneuver(act, config)
            
        # Start trigger for act
        start_trigger = etree.SubElement(act, "StartTrigger")
        cond_group = etree.SubElement(start_trigger, "ConditionGroup")
        condition = etree.SubElement(cond_group, "Condition")
        condition.set("name", "StartCondition")
        condition.set("delay", "0")
        condition.set("conditionEdge", "rising")
        by_value = etree.SubElement(condition, "ByValueCondition")
        sim_time = etree.SubElement(by_value, "SimulationTimeCondition")
        sim_time.set("value", "0")
        sim_time.set("rule", "greaterThan")
        
    def _add_edge_case_maneuver(self, act: etree.Element, config: ScenarioConfig):
        """Add maneuvers for specific edge cases."""
        mg = etree.SubElement(act, "ManeuverGroup")
        mg.set("maximumExecutionCount", "1")
        mg.set("name", f"{config.edge_case.value}_maneuver_group")
        
        if config.edge_case == EdgeCaseType.PEDESTRIAN_CROSSING:
            if config.pedestrians:
                actors = etree.SubElement(mg, "Actors")
                actors.set("selectTriggeringEntities", "false")
                entity_ref = etree.SubElement(actors, "EntityRef")
                entity_ref.set("entityRef", config.pedestrians[0].name)
                
                maneuver = etree.SubElement(mg, "Maneuver")
                maneuver.set("name", "PedestrianCrossing")
                
                event = etree.SubElement(maneuver, "Event")
                event.set("name", "CrossingEvent")
                event.set("priority", "overwrite")
                
                action = etree.SubElement(event, "Action")
                action.set("name", "WalkAcross")
                private_action = etree.SubElement(action, "PrivateAction")
                routing = etree.SubElement(private_action, "RoutingAction")
                acquire = etree.SubElement(routing, "AcquirePositionAction")
                position = etree.SubElement(acquire, "Position")
                lane_pos = etree.SubElement(position, "LanePosition")
                lane_pos.set("roadId", "1")
                lane_pos.set("laneId", "0")
                lane_pos.set("offset", "-3.0")
                lane_pos.set("s", str(config.pedestrians[0].s_position))
                
                # Trigger when ego is close
                start_trigger = etree.SubElement(event, "StartTrigger")
                self._add_distance_trigger(start_trigger, "Ego", config.pedestrians[0].name, 30.0)
                
        elif config.edge_case == EdgeCaseType.CUT_IN:
            if config.vehicles:
                actors = etree.SubElement(mg, "Actors")
                actors.set("selectTriggeringEntities", "false")
                entity_ref = etree.SubElement(actors, "EntityRef")
                entity_ref.set("entityRef", config.vehicles[0].name)
                
                maneuver = etree.SubElement(mg, "Maneuver")
                maneuver.set("name", "CutInManeuver")
                
                event = etree.SubElement(maneuver, "Event")
                event.set("name", "LaneChangeEvent")
                event.set("priority", "overwrite")
                
                action = etree.SubElement(event, "Action")
                action.set("name", "CutIn")
                private_action = etree.SubElement(action, "PrivateAction")
                lateral = etree.SubElement(private_action, "LateralAction")
                lane_change = etree.SubElement(lateral, "LaneChangeAction")
                lane_change.set("targetLaneOffset", "0.0")
                dynamics = etree.SubElement(lane_change, "LaneChangeActionDynamics")
                dynamics.set("dynamicsShape", "sinusoidal")
                dynamics.set("value", "2.0")
                dynamics.set("dynamicsDimension", "time")
                target = etree.SubElement(lane_change, "LaneChangeTarget")
                rel_target = etree.SubElement(target, "RelativeTargetLane")
                rel_target.set("entityRef", "Ego")
                rel_target.set("value", "0")
                
                start_trigger = etree.SubElement(event, "StartTrigger")
                self._add_distance_trigger(start_trigger, "Ego", config.vehicles[0].name, 20.0)
                
        elif config.edge_case == EdgeCaseType.EMERGENCY_BRAKE:
            if config.vehicles:
                actors = etree.SubElement(mg, "Actors")
                actors.set("selectTriggeringEntities", "false")
                entity_ref = etree.SubElement(actors, "EntityRef")
                entity_ref.set("entityRef", config.vehicles[0].name)
                
                maneuver = etree.SubElement(mg, "Maneuver")
                maneuver.set("name", "EmergencyBrakeManeuver")
                
                event = etree.SubElement(maneuver, "Event")
                event.set("name", "BrakeEvent")
                event.set("priority", "overwrite")
                
                action = etree.SubElement(event, "Action")
                action.set("name", "EmergencyBrake")
                private_action = etree.SubElement(action, "PrivateAction")
                longitudinal = etree.SubElement(private_action, "LongitudinalAction")
                speed_action = etree.SubElement(longitudinal, "SpeedAction")
                speed_target = etree.SubElement(speed_action, "SpeedActionTarget")
                abs_target = etree.SubElement(speed_target, "AbsoluteTargetSpeed")
                abs_target.set("value", "0")
                dynamics = etree.SubElement(speed_action, "SpeedActionDynamics")
                dynamics.set("dynamicsShape", "linear")
                dynamics.set("value", "-8.0")  # -8 m/s² deceleration
                dynamics.set("dynamicsDimension", "rate")
                
                start_trigger = etree.SubElement(event, "StartTrigger")
                self._add_time_trigger(start_trigger, 5.0)
        else:
            self._add_default_maneuver(act, config)
            
    def _add_default_maneuver(self, act: etree.Element, config: ScenarioConfig):
        """Add default follow-lane maneuver."""
        mg = etree.SubElement(act, "ManeuverGroup")
        mg.set("maximumExecutionCount", "1")
        mg.set("name", "DefaultManeuverGroup")
        
        actors = etree.SubElement(mg, "Actors")
        actors.set("selectTriggeringEntities", "false")
        entity_ref = etree.SubElement(actors, "EntityRef")
        entity_ref.set("entityRef", "Ego")
        
        maneuver = etree.SubElement(mg, "Maneuver")
        maneuver.set("name", "FollowLane")
        
        event = etree.SubElement(maneuver, "Event")
        event.set("name", "DriveEvent")
        event.set("priority", "overwrite")
        
        action = etree.SubElement(event, "Action")
        action.set("name", "Drive")
        private_action = etree.SubElement(action, "PrivateAction")
        longitudinal = etree.SubElement(private_action, "LongitudinalAction")
        speed_action = etree.SubElement(longitudinal, "SpeedAction")
        speed_target = etree.SubElement(speed_action, "SpeedActionTarget")
        abs_target = etree.SubElement(speed_target, "AbsoluteTargetSpeed")
        abs_target.set("value", str(config.ego_speed / 3.6))
        dynamics = etree.SubElement(speed_action, "SpeedActionDynamics")
        dynamics.set("dynamicsShape", "step")
        dynamics.set("value", "0")
        dynamics.set("dynamicsDimension", "time")
        
        start_trigger = etree.SubElement(event, "StartTrigger")
        self._add_time_trigger(start_trigger, 0.0)
        
    def _add_distance_trigger(self, trigger: etree.Element, entity1: str, 
                              entity2: str, distance: float):
        """Add a distance-based trigger condition."""
        cond_group = etree.SubElement(trigger, "ConditionGroup")
        condition = etree.SubElement(cond_group, "Condition")
        condition.set("name", "DistanceCondition")
        condition.set("delay", "0")
        condition.set("conditionEdge", "rising")
        by_entity = etree.SubElement(condition, "ByEntityCondition")
        triggering = etree.SubElement(by_entity, "TriggeringEntities")
        triggering.set("triggeringEntitiesRule", "any")
        entity_ref = etree.SubElement(triggering, "EntityRef")
        entity_ref.set("entityRef", entity1)
        entity_cond = etree.SubElement(by_entity, "EntityCondition")
        dist_cond = etree.SubElement(entity_cond, "DistanceCondition")
        dist_cond.set("value", str(distance))
        dist_cond.set("freespace", "false")
        dist_cond.set("alongRoute", "true")
        dist_cond.set("rule", "lessThan")
        position = etree.SubElement(dist_cond, "Position")
        rel_pos = etree.SubElement(position, "RelativeObjectPosition")
        rel_pos.set("entityRef", entity2)
        rel_pos.set("dx", "0")
        rel_pos.set("dy", "0")
        
    def _add_time_trigger(self, trigger: etree.Element, time: float):
        """Add a time-based trigger condition."""
        cond_group = etree.SubElement(trigger, "ConditionGroup")
        condition = etree.SubElement(cond_group, "Condition")
        condition.set("name", "TimeCondition")
        condition.set("delay", "0")
        condition.set("conditionEdge", "rising")
        by_value = etree.SubElement(condition, "ByValueCondition")
        sim_time = etree.SubElement(by_value, "SimulationTimeCondition")
        sim_time.set("value", str(time))
        sim_time.set("rule", "greaterThan")
        
    # Helper methods for weather/time
    def _get_datetime_for_time(self, time_of_day: TimeOfDay) -> str:
        times = {
            TimeOfDay.DAWN: "2024-06-15T05:30:00",
            TimeOfDay.MORNING: "2024-06-15T08:00:00",
            TimeOfDay.NOON: "2024-06-15T12:00:00",
            TimeOfDay.AFTERNOON: "2024-06-15T15:00:00",
            TimeOfDay.EVENING: "2024-06-15T19:00:00",
            TimeOfDay.NIGHT: "2024-06-15T23:00:00",
        }
        return times.get(time_of_day, "2024-06-15T12:00:00")
    
    def _get_cloud_state(self, weather: WeatherType) -> str:
        states = {
            WeatherType.CLEAR: "free",
            WeatherType.CLOUDY: "cloudy",
            WeatherType.RAINY: "overcast",
            WeatherType.FOGGY: "overcast",
            WeatherType.SNOWY: "overcast",
        }
        return states.get(weather, "free")
    
    def _get_sun_intensity(self, weather: WeatherType, time: TimeOfDay) -> str:
        base = 1.0 if weather == WeatherType.CLEAR else 0.5
        if time in [TimeOfDay.DAWN, TimeOfDay.EVENING]:
            base *= 0.5
        elif time == TimeOfDay.NIGHT:
            base *= 0.1
        return str(base)
    
    def _get_sun_elevation(self, time: TimeOfDay) -> str:
        elevations = {
            TimeOfDay.DAWN: "0.1",
            TimeOfDay.MORNING: "0.5",
            TimeOfDay.NOON: "1.2",
            TimeOfDay.AFTERNOON: "0.8",
            TimeOfDay.EVENING: "0.2",
            TimeOfDay.NIGHT: "-0.5",
        }
        return elevations.get(time, "1.0")
    
    def _get_fog_range(self, weather: WeatherType) -> str:
        ranges = {
            WeatherType.CLEAR: "100000",
            WeatherType.CLOUDY: "10000",
            WeatherType.RAINY: "1000",
            WeatherType.FOGGY: "100",
            WeatherType.SNOWY: "500",
        }
        return ranges.get(weather, "100000")
    
    def _get_precipitation_type(self, weather: WeatherType) -> str:
        types = {
            WeatherType.CLEAR: "dry",
            WeatherType.CLOUDY: "dry",
            WeatherType.RAINY: "rain",
            WeatherType.FOGGY: "dry",
            WeatherType.SNOWY: "snow",
        }
        return types.get(weather, "dry")
    
    def _get_precipitation_intensity(self, weather: WeatherType) -> str:
        intensity = {
            WeatherType.CLEAR: "0.0",
            WeatherType.CLOUDY: "0.0",
            WeatherType.RAINY: "0.7",
            WeatherType.FOGGY: "0.0",
            WeatherType.SNOWY: "0.5",
        }
        return intensity.get(weather, "0.0")
    
    def _get_friction(self, weather: WeatherType) -> str:
        friction = {
            WeatherType.CLEAR: "1.0",
            WeatherType.CLOUDY: "1.0",
            WeatherType.RAINY: "0.7",
            WeatherType.FOGGY: "0.9",
            WeatherType.SNOWY: "0.4",
        }
        return friction.get(weather, "1.0")
