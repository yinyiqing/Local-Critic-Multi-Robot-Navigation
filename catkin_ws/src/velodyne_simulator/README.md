# Velodyne Simulator

This vendored ROS package provides the URDF description and Gazebo plugins used to simulate the project's Velodyne laser scanner. It is built through the repository's ROS Noetic catkin workspace; use the root execution guide for environment setup.

![RViz screenshot](img/rviz.png)

## Features

- VLP-16 and HDL-32E sensor descriptions.
- `PointCloud2` output with `x`, `y`, `z`, `intensity`, and `ring` fields.
- Configurable Gaussian noise, range, resolution, and update rate.
- CPU ray and GPU ray sensor modes.

## Xacro Parameters

- `origin`: transform from the parent link.
- `parent`: parent link name; defaults to `base_link`.
- `name`: model and point-cloud frame name; defaults to `velodyne`.
- `topic`: point-cloud topic; defaults to `/velodyne_points`.
- `hz`: update rate; defaults to `10`.
- `lasers`: number of vertical lasers.
- `samples`: number of horizontal samples.
- `min_range` and `max_range`: range limits in meters.
- `noise`: Gaussian range noise in meters.
- `min_angle` and `max_angle`: horizontal limits in radians.
- `gpu`: select the GPU ray sensor.
- `min_intensity`: discard returns below this intensity.

## Examples

```bash
roslaunch velodyne_description example.launch
roslaunch velodyne_description example.launch gpu:=true
```

Large point clouds can reduce the Gazebo update rate. Lower `samples` or `hz` when simulation cannot maintain real time.
