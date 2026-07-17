#!/usr/bin/env python3
import argparse
from pathlib import Path


def initial_positions(num_agents):
    if num_agents == 1:
        return [(0.0, 0.0)]
    if num_agents == 2:
        return [(-1.5, 0.0), (1.5, 0.0)]
    if num_agents == 3:
        return [(-1.8, 0.0), (0.0, 1.4), (1.8, 0.0)]

    columns = int(num_agents**0.5)
    if columns * columns < num_agents:
        columns += 1
    spacing = 1.8
    rows = (num_agents + columns - 1) // columns
    x0 = -spacing * (columns - 1) / 2.0
    y0 = -spacing * (rows - 1) / 2.0
    positions = []
    for idx in range(num_agents):
        row = idx // columns
        col = idx % columns
        positions.append((x0 + col * spacing, y0 + row * spacing))
    return positions


def render_launch(num_agents, gui):
    lines = [
        "<launch>",
        '  <arg name="gui" default="false"/>',
        '  <arg name="enable_rviz" default="false"/>',
        "",
        '  <include file="$(find multi_robot_scenario)/launch/empty_world.launch">',
        f'    <arg name="gui" value="{str(gui).lower()}"/>',
        "  </include>",
        "",
    ]

    robot_specs = []
    for idx, (x, y) in enumerate(initial_positions(num_agents), start=1):
        name = f"r{idx}"
        robot_specs.append(f"{name},{x:.2f},{y:.2f},0.01,0.0")
        lines.extend(
            [
                f'  <param name="robot_description_{name}"',
                "         command=\"$(find xacro)/xacro "
                "'$(find multi_robot_scenario)/xacro/p3dx/pioneer3dx.xacro' "
                f"velodyne_name:={name}_velodyne "
                f"velodyne_topic:=/{name}/velodyne_points "
                f"robot_namespace:=/{name} tf_prefix:={name} "
                'enable_aux_sensors:=false"/>',
                "",
            ]
        )

    lines.extend(
        [
            '  <node name="sequential_multi_robot_spawner"',
            '        pkg="multi_robot_scenario"',
            '        type="spawn_multi_robots.py"',
            '        required="true"',
            '        output="screen"',
            f'        args="{" ".join(robot_specs)}"/>',
            "",
            '  <group if="$(arg enable_rviz)">',
            '    <node pkg="rviz"',
            '          type="rviz"',
            '          name="rviz"',
            '          args="-d $(find multi_robot_scenario)/launch/pioneer3dx.rviz"/>',
            "  </group>",
            "</launch>",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a namespaced multi-robot Gazebo launch file."
    )
    parser.add_argument("--num-agents", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if args.num_agents < 1 or args.num_agents > 10:
        raise SystemExit("--num-agents must be between 1 and 10")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_launch(args.num_agents, args.gui), encoding="utf-8")
    print(f"Generated {args.num_agents}-robot launch: {args.output}")


if __name__ == "__main__":
    main()
