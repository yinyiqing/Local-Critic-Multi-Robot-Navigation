#!/usr/bin/env python3
import argparse
from pathlib import Path


COLORS = [
    (255, 70, 50),
    (70, 160, 255),
    (80, 220, 120),
    (255, 190, 40),
    (210, 90, 255),
    (50, 230, 230),
    (255, 115, 140),
    (140, 215, 40),
    (180, 180, 255),
    (255, 140, 40),
]


def color_text(color):
    return "%i; %i; %i" % color


def robot_model_block(name):
    return f"""    - Alpha: 1
      Class: rviz/RobotModel
      Collision Enabled: false
      Enabled: true
      Links:
        All Links Enabled: true
        Expand Joint Details: false
        Expand Link Details: false
        Expand Tree: false
        Link Tree Style: Links in Alphabetic Order
      Name: {name} RobotModel
      Robot Description: /{name}/robot_description
      TF Prefix: {name}
      Update Interval: 0
      Value: true
      Visual Enabled: true"""


def odom_block(name, color):
    return f"""    - Angle Tolerance: 20
      Class: rviz/Odometry
      Enabled: false
      Keep: 1
      Name: {name} Odom
      Position Tolerance: 0.1
      Queue Size: 10
      Shape:
        Alpha: 1
        Axes Length: 0.45
        Axes Radius: 0.05
        Color: {color_text(color)}
        Head Length: 0.14
        Head Radius: 0.09
        Shaft Length: 0.28
        Shaft Radius: 0.035
        Value: Arrow
      Topic: /{name}/odom
      Unreliable: false
      Value: false"""


def pointcloud_block(name, enabled):
    value = "true" if enabled else "false"
    return f"""    - Alpha: 1
      Autocompute Intensity Bounds: true
      Autocompute Value Bounds:
        Max Value: 10
        Min Value: -10
        Value: true
      Axis: Z
      Channel Name: intensity
      Class: rviz/PointCloud2
      Color: 255; 255; 255
      Color Transformer: AxisColor
      Decay Time: 0
      Enabled: {value}
      Invert Rainbow: false
      Max Color: 255; 255; 255
      Min Color: 0; 0; 0
      Name: {name} Velodyne
      Position Transformer: XYZ
      Queue Size: 10
      Selectable: true
      Size (Pixels): 3
      Size (m): 0.01
      Style: Flat Squares
      Topic: /{name}/velodyne_points
      Unreliable: false
      Use Fixed Frame: true
      Use rainbow: true
      Value: {value}"""


def laserscan_block(name, enabled):
    value = "true" if enabled else "false"
    return f"""    - Alpha: 1
      Autocompute Intensity Bounds: true
      Autocompute Value Bounds:
        Max Value: 10
        Min Value: -10
        Value: true
      Axis: Z
      Channel Name: intensity
      Class: rviz/LaserScan
      Color: 255; 255; 255
      Color Transformer: AxisColor
      Decay Time: 0
      Enabled: {value}
      Invert Rainbow: false
      Max Color: 255; 255; 255
      Min Color: 0; 0; 0
      Name: {name} LaserScan
      Position Transformer: XYZ
      Queue Size: 10
      Selectable: true
      Size (Pixels): 3
      Size (m): 0.1
      Style: Flat Squares
      Topic: /{name}/front_laser/scan
      Unreliable: false
      Use Fixed Frame: true
      Use rainbow: true
      Value: {value}"""


def render_rviz(num_agents):
    agent_names = [f"r{i}" for i in range(1, num_agents + 1)]
    displays = [
        """    - Alpha: 0.35
      Cell Size: 1
      Class: rviz/Grid
      Color: 160; 160; 164
      Enabled: true
      Line Style:
        Line Width: 0.03
        Value: Lines
      Name: Grid
      Plane: XY
      Plane Cell Count: 20
      Reference Frame: <Fixed Frame>
      Value: true""",
        """    - Class: rviz/TF
      Enabled: false
      Frame Timeout: 15
      Frames:
        All Enabled: true
      Marker Scale: 0.35
      Name: TF
      Show Arrows: true
      Show Axes: true
      Show Names: false
      Tree:
        {}
      Update Interval: 0
      Value: false""",
    ]
    for idx, name in enumerate(agent_names):
        displays.append(robot_model_block(name))
        displays.append(odom_block(name, COLORS[idx % len(COLORS)]))
        displays.append(laserscan_block(name, False))
        displays.append(pointcloud_block(name, True))

    displays.extend(
        [
            """    - Class: rviz/MarkerArray
      Enabled: true
      Marker Topic: /goal_points
      Name: Goal Points
      Namespaces:
        goal_points: true
      Queue Size: 100
      Value: true""",
            """    - Class: rviz/MarkerArray
      Enabled: true
      Marker Topic: /multi_agent_overlay
      Name: Multi-Agent Overlay
      Namespaces:
        robot_labels: true
        robot_trails: true
      Queue Size: 10
      Value: true""",
        ]
    )

    display_text = "\n".join(displays)
    return f"""Panels:
  - Class: rviz/Displays
    Name: Displays
  - Class: rviz/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
{display_text}
  Enabled: true
  Global Options:
    Background Color: 48; 48; 48
    Default Light: true
    Fixed Frame: odom
    Frame Rate: 30
  Name: root
  Tools:
    - Class: rviz/Interact
      Hide Inactive Objects: true
    - Class: rviz/MoveCamera
    - Class: rviz/Select
    - Class: rviz/FocusCamera
    - Class: rviz/Measure
    - Class: rviz/SetInitialPose
      Theta std deviation: 0.2617993950843811
      Topic: /initialpose
      X std deviation: 0.5
      Y std deviation: 0.5
    - Class: rviz/SetGoal
      Topic: /move_base_simple/goal
    - Class: rviz/PublishPoint
      Single click: true
      Topic: /clicked_point
  Value: true
  Views:
    Current:
      Angle: 0.005
      Class: rviz/TopDownOrtho
      Enable Stereo Rendering:
        Stereo Eye Separation: 0.06
        Stereo Focal Distance: 1
        Swap Stereo Eyes: false
        Value: false
      Invert Z Axis: false
      Name: Current View
      Near Clip Distance: 0.01
      Scale: 73.6252212524414
      Target Frame: <Fixed Frame>
      X: 0.048065461218357086
      Y: 0.11967461556196213
    Saved: ~
Window Geometry:
  Displays:
    collapsed: false
  Height: 900
  Hide Left Dock: false
  Hide Right Dock: true
  Width: 1400
  X: 80
  Y: 40
"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate a reusable RViz config for namespaced multi-robot runs."
    )
    parser.add_argument("--num-agents", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.num_agents < 1 or args.num_agents > 10:
        raise SystemExit("--num-agents must be between 1 and 10")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_rviz(args.num_agents), encoding="utf-8")
    print(f"Generated {args.num_agents}-robot RViz config: {args.output}")


if __name__ == "__main__":
    main()
