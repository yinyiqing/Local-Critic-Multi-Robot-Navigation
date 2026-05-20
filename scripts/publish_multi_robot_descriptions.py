#!/usr/bin/env python3
import argparse

import rospy


def main():
    parser = argparse.ArgumentParser(
        description="Copy generated per-robot URDF descriptions into namespaced RViz parameters."
    )
    parser.add_argument("--agents", required=True)
    args = parser.parse_args(rospy.myargv()[1:])

    rospy.init_node("multi_robot_description_publisher", anonymous=True)
    agent_names = [name.strip() for name in args.agents.split(",") if name.strip()]
    for name in agent_names:
        source_param = f"/robot_description_{name}"
        target_param = f"/{name}/robot_description"
        if not rospy.has_param(source_param):
            raise RuntimeError(f"Missing parameter: {source_param}")
        robot_description = rospy.get_param(source_param)
        if not isinstance(robot_description, str) or not robot_description.strip():
            raise RuntimeError(f"Empty robot description: {source_param}")
        rospy.set_param(target_param, robot_description)
        print(f"Published {source_param} -> {target_param}")


if __name__ == "__main__":
    main()
