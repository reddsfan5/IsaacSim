# ROS 2 Integration

<!-- Auto-generated Table of Contents -->
- [Overview](#overview)
- [Bridge Architecture](#bridge-architecture)
- [Communication Patterns](#communication-patterns)
- [Message Conversion System](#message-conversion-system)
- [Quality of Service Configuration](#quality-of-service-configuration)
- [Integration Examples](#integration-examples)

## Overview

Isaac Sim provides comprehensive ROS 2 integration through the `isaacsim.ros2.bridge` extension, enabling bidirectional communication between the simulation environment and external ROS 2 systems. This integration follows a modular architecture that supports various message types, services, and quality of service (QoS) configurations.

The ROS 2 integration enables Isaac Sim to function as both a data source and a control target for ROS 2 applications, making it ideal for developing, testing, and validating robotics systems in simulation before real-world deployment.

## Bridge Architecture

The ROS 2 bridge architecture is implemented as a factory pattern that creates and manages various ROS 2 entities. This design provides flexibility in creating different types of ROS 2 communication interfaces while maintaining consistency in their management.

```mermaid
classDiagram
    class ROS2Bridge {
        +create_publisher()
        +create_subscriber()
        +create_service_client()
        +create_service_server() 
        +create_action_client()
        +create_action_server()
        +manage_node_lifecycle()
        +configure_qos()
    }
    
    class MessageFactory {
        +create_message()
        +convert_isaac_to_ros()
        +convert_ros_to_isaac()
        +validate_message_schema()
        +get_message_definition()
    }
    
    class QoSManager {
        +configure_reliability()
        +set_durability()
        +manage_history()
        +handle_liveliness()
        +set_deadline()
    }
    
    class NodeManager {
        +create_node()
        +manage_lifecycle()
        +handle_callbacks()
        +coordinate_execution()
    }
    
    ROS2Bridge --> MessageFactory : "uses"
    ROS2Bridge --> QoSManager : "configures"
    ROS2Bridge --> NodeManager : "manages"
    MessageFactory --> "ROS 2 Messages" : "creates"
    QoSManager --> "QoS Policies" : "applies"
    NodeManager --> "ROS 2 Nodes" : "coordinates"
```

### Core Components

The bridge system consists of several interconnected components:

#### Publisher Interface
Publishers enable Isaac Sim to send data to ROS 2 topics:
- **Sensor Data Publishing** - Camera images, point clouds, IMU data
- **Robot State Publishing** - Joint states, poses, velocities
- **Simulation Status** - Timing, events, diagnostics

#### Subscriber Interface  
Subscribers allow Isaac Sim to receive commands from ROS 2:
- **Control Commands** - Velocity commands, joint targets, trajectories
- **Configuration Updates** - Parameter changes, mode switches
- **External Events** - Triggers, resets, state changes

#### Service Interface
Bidirectional request/response communication:
- **Robot Control Services** - Move to pose, execute trajectory
- **Configuration Services** - Get/set parameters, mode changes
- **Diagnostic Services** - Health checks, status queries

## Communication Patterns

### Topic-Based Communication
The most common pattern for streaming data and commands:

#### Sensor Data Streaming
```python
from isaacsim.ros2_bridge import ROS2Bridge

# Create ROS 2 bridge
ros2_bridge = ROS2Bridge()

# Create publisher for camera data
camera_publisher = ros2_bridge.create_publisher(
    topic_name="/camera/image_raw",
    message_type="sensor_msgs/Image",
    qos_profile="sensor_data"
)

# Create publisher for robot joint states  
joint_state_publisher = ros2_bridge.create_publisher(
    topic_name="/joint_states",
    message_type="sensor_msgs/JointState", 
    qos_profile="default"
)

# Publish data in simulation loop
def simulation_step():
    # Get camera image from Isaac Sim
    camera_image = get_camera_data()
    camera_publisher.publish(camera_image)
    
    # Get joint states from robot
    joint_positions = robot.get_joint_positions()
    joint_velocities = robot.get_joint_velocities()
    joint_state_msg = create_joint_state_message(joint_positions, joint_velocities)
    joint_state_publisher.publish(joint_state_msg)
```

#### Command Reception
```python
# Create subscriber for velocity commands
cmd_vel_subscriber = ros2_bridge.create_subscriber(
    topic_name="/cmd_vel",
    message_type="geometry_msgs/Twist",
    callback=handle_velocity_command,
    qos_profile="reliable"
)

def handle_velocity_command(msg):
    """Process incoming velocity commands."""
    linear_vel = [msg.linear.x, msg.linear.y, msg.linear.z]
    angular_vel = [msg.angular.x, msg.angular.y, msg.angular.z]
    
    # Apply commands to robot in simulation
    robot.set_velocity_command(linear_vel, angular_vel)
```

### Service-Based Communication
For request/response interactions:

```python
# Create service server for robot control
move_robot_service = ros2_bridge.create_service_server(
    service_name="/move_to_pose",
    service_type="geometry_msgs/PoseStamped",
    callback=handle_move_request
)

def handle_move_request(request, response):
    """Handle robot move requests."""
    target_pose = request.pose
    success = robot.move_to_pose(target_pose)
    
    response.success = success
    response.message = "Move completed" if success else "Move failed"
    return response
```

### Action-Based Communication
For long-running operations with feedback:

```python
# Create action server for trajectory execution
trajectory_action = ros2_bridge.create_action_server(
    action_name="/execute_trajectory", 
    action_type="control_msgs/FollowJointTrajectory",
    execute_callback=execute_trajectory_callback
)

def execute_trajectory_callback(goal_handle):
    """Execute joint trajectory with feedback."""
    trajectory = goal_handle.request.trajectory
    
    for point in trajectory.points:
        # Execute trajectory point
        robot.set_joint_targets(point.positions)
        
        # Send feedback
        feedback = create_feedback_message(robot.get_joint_positions())
        goal_handle.publish_feedback(feedback)
        
        # Check for cancellation
        if goal_handle.is_cancel_requested:
            goal_handle.canceled()
            return
    
    # Send result
    result = create_result_message(True)
    goal_handle.succeed(result)
```

## Message Conversion System

The bridge automatically handles conversion between Isaac Sim data types and ROS 2 message formats:

### Geometric Data Conversion
```python
# Isaac Sim pose to ROS 2 geometry_msgs/Pose
def isaac_pose_to_ros_pose(isaac_position, isaac_orientation):
    """Convert Isaac Sim pose to ROS 2 Pose message."""
    pose_msg = geometry_msgs.msg.Pose()
    
    # Position conversion (Isaac Sim uses right-handed Z-up)
    pose_msg.position.x = isaac_position[0]
    pose_msg.position.y = isaac_position[1] 
    pose_msg.position.z = isaac_position[2]
    
    # Quaternion conversion (Isaac Sim: [x,y,z,w], ROS 2: [x,y,z,w])
    pose_msg.orientation.x = isaac_orientation[0]
    pose_msg.orientation.y = isaac_orientation[1]
    pose_msg.orientation.z = isaac_orientation[2]
    pose_msg.orientation.w = isaac_orientation[3]
    
    return pose_msg

# ROS 2 Twist to Isaac Sim velocity command
def ros_twist_to_isaac_velocity(twist_msg):
    """Convert ROS 2 Twist to Isaac Sim velocity."""
    linear_velocity = [
        twist_msg.linear.x,
        twist_msg.linear.y, 
        twist_msg.linear.z
    ]
    angular_velocity = [
        twist_msg.angular.x,
        twist_msg.angular.y,
        twist_msg.angular.z
    ]
    return linear_velocity, angular_velocity
```

### Sensor Data Conversion
```python
# Camera image conversion
def isaac_image_to_ros_image(isaac_image_data, encoding="rgb8"):
    """Convert Isaac Sim image to ROS 2 sensor_msgs/Image."""
    image_msg = sensor_msgs.msg.Image()
    
    image_msg.header.stamp = get_ros_time()
    image_msg.header.frame_id = "camera_frame"
    image_msg.height = isaac_image_data.shape[0]
    image_msg.width = isaac_image_data.shape[1]
    image_msg.encoding = encoding
    image_msg.step = isaac_image_data.shape[1] * 3  # 3 bytes per pixel for RGB
    image_msg.data = isaac_image_data.tobytes()
    
    return image_msg

# Point cloud conversion
def isaac_pointcloud_to_ros_pointcloud(isaac_points):
    """Convert Isaac Sim point cloud to ROS 2 PointCloud2."""
    cloud_msg = sensor_msgs.msg.PointCloud2()
    
    cloud_msg.header.stamp = get_ros_time()
    cloud_msg.header.frame_id = "lidar_frame"
    cloud_msg.height = 1
    cloud_msg.width = len(isaac_points)
    cloud_msg.is_dense = True
    
    # Define point fields (x, y, z)
    cloud_msg.fields = [
        sensor_msgs.msg.PointField(name="x", offset=0, datatype=sensor_msgs.msg.PointField.FLOAT32, count=1),
        sensor_msgs.msg.PointField(name="y", offset=4, datatype=sensor_msgs.msg.PointField.FLOAT32, count=1),
        sensor_msgs.msg.PointField(name="z", offset=8, datatype=sensor_msgs.msg.PointField.FLOAT32, count=1)
    ]
    cloud_msg.point_step = 12  # 4 bytes * 3 fields
    cloud_msg.row_step = cloud_msg.point_step * cloud_msg.width
    cloud_msg.data = isaac_points.astype(np.float32).tobytes()
    
    return cloud_msg
```

## Quality of Service Configuration

ROS 2 QoS (Quality of Service) policies allow fine-tuning of communication behavior:

### Predefined QoS Profiles
```python
# Standard QoS profiles for different use cases
qos_profiles = {
    "sensor_data": {
        "reliability": "best_effort",
        "durability": "volatile", 
        "history": "keep_last",
        "depth": 10
    },
    "control_commands": {
        "reliability": "reliable",
        "durability": "volatile",
        "history": "keep_last", 
        "depth": 1
    },
    "diagnostics": {
        "reliability": "reliable",
        "durability": "transient_local",
        "history": "keep_last",
        "depth": 50
    }
}

# Apply QoS profile to publisher/subscriber
camera_publisher = ros2_bridge.create_publisher(
    topic_name="/camera/image_raw",
    message_type="sensor_msgs/Image",
    qos_profile=qos_profiles["sensor_data"]
)
```

### Custom QoS Configuration
```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

# Create custom QoS for high-frequency control
high_freq_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    deadline=Duration(seconds=0, nanoseconds=10_000_000)  # 10ms deadline
)

control_subscriber = ros2_bridge.create_subscriber(
    topic_name="/high_freq_control",
    message_type="geometry_msgs/Twist",
    callback=handle_high_freq_control,
    qos_profile=high_freq_qos
)
```

## Integration Examples

### Complete Robot Simulation with ROS 2
```python
from isaacsim.core import SimulationApp, World
from isaacsim.core.robots import Robot
from isaacsim.ros2_bridge import ROS2Bridge

# Initialize simulation
simulation_app = SimulationApp({"headless": False})
world = World()

# Create robot
robot = Robot(prim_path="/World/robot", name="my_robot")
world.scene.add(robot)

# Initialize ROS 2 bridge
ros2_bridge = ROS2Bridge()

# Setup publishers
joint_state_pub = ros2_bridge.create_publisher(
    "/joint_states", "sensor_msgs/JointState"
)
odom_pub = ros2_bridge.create_publisher(
    "/odom", "nav_msgs/Odometry"
)

# Setup subscribers  
cmd_vel_sub = ros2_bridge.create_subscriber(
    "/cmd_vel", "geometry_msgs/Twist", handle_cmd_vel
)

# Setup services
reset_service = ros2_bridge.create_service_server(
    "/reset_robot", "std_srvs/Empty", handle_reset_request
)

def handle_cmd_vel(msg):
    """Handle velocity commands."""
    linear = [msg.linear.x, msg.linear.y, msg.linear.z]
    angular = [msg.angular.x, msg.angular.y, msg.angular.z] 
    robot.set_velocity_command(linear, angular)

def handle_reset_request(request, response):
    """Handle robot reset requests."""
    robot.reset()
    response.success = True
    return response

# Simulation loop
def simulation_step():
    # Publish robot state
    joint_positions = robot.get_joint_positions()
    joint_velocities = robot.get_joint_velocities()
    publish_joint_state(joint_positions, joint_velocities)
    
    # Publish odometry
    position, orientation = robot.get_world_pose()
    linear_vel, angular_vel = robot.get_velocity()
    publish_odometry(position, orientation, linear_vel, angular_vel)

# Run simulation
world.reset()
while simulation_app.is_running():
    simulation_step()
    world.step(render=True)

simulation_app.close()
```

### Multi-Robot ROS 2 Integration
```python
# Create multiple robots with ROS 2 interfaces
robots = []
ros2_interfaces = []

for i in range(3):
    # Create robot
    robot = Robot(prim_path=f"/World/robot_{i}", name=f"robot_{i}")
    world.scene.add(robot)
    robots.append(robot)
    
    # Create ROS 2 interface for each robot
    robot_ns = f"robot_{i}"
    interface = {
        "joint_state_pub": ros2_bridge.create_publisher(
            f"/{robot_ns}/joint_states", "sensor_msgs/JointState"
        ),
        "cmd_vel_sub": ros2_bridge.create_subscriber(
            f"/{robot_ns}/cmd_vel", "geometry_msgs/Twist", 
            lambda msg, r=robot: handle_robot_cmd_vel(msg, r)
        )
    }
    ros2_interfaces.append(interface)

def handle_robot_cmd_vel(msg, robot):
    """Handle velocity command for specific robot."""
    robot.set_velocity_command([msg.linear.x, msg.linear.y, 0], [0, 0, msg.angular.z])
```

---

**Referenced Files:**
- [ROS 2 Bridge Extension](../../source/deprecated/omni.isaac.ros2_bridge/README.md)
- [ROS 2 Bridge Implementation](../../source/deprecated/omni.isaac.ros2_bridge/omni/isaac/ros2_bridge/)

**Related Topics:**
- [ROS 2 Bridge Architecture](../integration-systems/ros2-integration/bridge-architecture.md)
- [Publishers and Subscribers](../integration-systems/ros2-integration/publishers.md)
- [Message Types](../integration-systems/ros2-integration/message-types.md)