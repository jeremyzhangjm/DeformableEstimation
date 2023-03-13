#!/usr/bin/env python3
import taichi as ti
from taichiCubeImport import data
import numpy as np
from scipy.spatial.transform import Rotation
import rospy
from geometry_msgs.msg import PoseArray
from geometry_msgs.msg import TransformStamped
from vectormath import Vector3
from utilis import VirtualRobot
from utilis import SortedSubscriber
import os
import sys
script_dir = os.path.dirname(__file__)
# mesh_dir = os.path.joint( script_dir)
sys.path.append(script_dir)


def initialize():
    '''
    Initialize the cable points and the cube position    
    '''

    # Initialize the cable points
    for i in range(n):
        cable_cur_position[i] = [i * seg_len, 0.0, 0.0]
        cable_old_position[i] = [i * seg_len, 0.0, 0.0]
        point_vel[i] = [0.0, 0.0, 0.0]

    # Initialize the visualization index for the cable
    for i in range(n - 1):
        cable_viz_idx[2*i + 0] = i
        cable_viz_idx[2*i + 1] = i + 1

    for i in range(link_num + 1 - 1):
        robot_joint_idx[2*i + 0] = i
        robot_joint_idx[2*i + 1] = i + 1

    scale = 0.02
    for i in range(len(data)):
        cube1_vertex_origin[i] = [scale * data[i][0],
                                  scale * data[i][1],
                                  scale * data[i][2]]
        cube2_vertex_origin[i] = [scale * data[i][0],
                                  scale * data[i][1],
                                  scale * data[i][2]]

    canvas.set_background_color((0.3, 0.3, 0.4))
    camera.position(2.5, -2.5, 2.5)
    camera.lookat(0, 0, -1.0)
    camera.up(0, 0, 1)


@ti.kernel
def update_free_end(free_end: ti.template()):

    #######################################################################
    ########## Update the cube position at the free end ###################
    #######################################################################
    for i in cube2_vertex_origin:
        for j in ti.static(range(3)):
            cube2_vertex_current[i][j] = cube2_vertex_origin[i][j] + free_end[j]


@ti.kernel
def update_fixed_end(fixed_end: ti.template()):
    for i in cube1_vertex_origin:
        for j in ti.static(range(3)):
            cube1_vertex_current[i][j] = cube1_vertex_origin[i][j] + \
                fixed_end[j]


def update_robot():
    
    pass


@ti.func
def euclidean_dist(point_a, point_b) -> float:

    d_square = (point_a[0] - point_b[0]) * (point_a[0] - point_b[0]) +\
        (point_a[1] - point_b[1]) * (point_a[1] - point_b[1]) +\
        (point_a[2] - point_b[2]) * (point_a[2] - point_b[2])

    d = ti.math.sqrt(d_square)
    return d


@ti.kernel
def update_cable():
    '''
    Update the cable position using Verlet Integration
    The cable is a chain of points, each point is connected to the next point

    The end points are fixed to the cube
    The cube position is updated using the data captured from ROS
    '''
    # print(cable_cur_position[0][0])
    for i in ti.grouped(cable_cur_position):
        point_vel[i] = cable_cur_position[i] - cable_old_position[i]
        cable_old_position[i] = cable_cur_position[i]
        G = ti.Vector([deltaTime*0, deltaTime*0.0, deltaTime*-9.8])
        # Gravity Term needs to be verified
        cable_cur_position[i] += (point_vel[i] + G) * 0.97/2.5

    loop_count = 0
    while loop_count < 50:
        loop_count += 1
        cable_cur_position[0] = cube1_vertex_current[1]
        cable_cur_position[n-1] = cube2_vertex_current[1]
        for i in range(n-1):
            first_seg = cable_cur_position[i]
            # print("first_seg is :",first_seg)

            if ti.math.isnan(first_seg[0]):
                ti.TaichiTypeError("first_seg is nan")

            eu_dist = euclidean_dist(
                cable_cur_position[i], cable_cur_position[i+1])
            # print("eu_dist is :",eu_dist)
            error = eu_dist - seg_len
            direction = (cable_cur_position[i+1] -
                         cable_cur_position[i]) / eu_dist

            # first_seg += error * 0.5 * direction
            # second_seg -= error * 0.5 * direction

            cable_cur_position[i] += error * 0.5 * direction
            cable_cur_position[i+1] -= error * 0.5 * direction

            # test whether the distance is corrected
            # eu_dist = euclidean_dist(cable_cur_position[i],cable_cur_position[i+1])


if __name__ == "__main__":

    ti.init(arch=ti.vulkan)  # Alternatively, ti.init(arch=ti.cpu)

    n = 50
    seg_len = 2.0 / n

    #######################################################################
    ########## Definition of the simulation environment ###################
    #######################################################################
    # Define cable properties
    cable_cur_position = ti.Vector.field(3, dtype=float, shape=n)
    cable_old_position = ti.Vector.field(3, dtype=float, shape=n)  # 3 x n x 1
    cable_viz_idx = ti.field(dtype=int, shape=(2 * n))
    point_vel = ti.Vector.field(3, dtype=float, shape=n)

    # Define end position
    cube1_vertex_origin = ti.Vector.field(3, dtype=float, shape=len(data))
    cube2_vertex_origin = ti.Vector.field(3, dtype=float, shape=len(data))
    cube1_vertex_current = ti.Vector.field(3, dtype=float, shape=len(data))
    cube2_vertex_current = ti.Vector.field(3, dtype=float, shape=len(data))

    # Define physics param
    gravity = ti.field(dtype=float, shape=(3))
    gravity = [0, 0, -9.8]
    deltaTime = 0.01

    # Define the robot end effector position
    link_num = 5
    robot_joint_pos = ti.Vector.field(3, dtype=float, shape=link_num + 1 )
    robot_joint_idx = ti.field(dtype=int, shape=(2 * (link_num + 1)))
    robot_seg_len = 0.4
    robot_seg_dir = link_num * [ 0.0 ]
    tolerance = 0.001  # tolerance for the fabrik algorithm
    robot = VirtualRobot(seg_len=robot_seg_len, seg_dir=robot_seg_dir, robot_base=[0.5, -0.0, -2.6]) # Initialize the fabrik solver

    # Define the visualization process
    window = ti.ui.Window("Test for Drawing 3D-lines", (768, 768))
    canvas = window.get_canvas()
    scene = ti.ui.Scene()
    camera = ti.ui.Camera()
    gui = window.get_gui()

    # Define the reference frame
    origin = [0.0, 0.0, 0.0]
    axis_length = 0.5
    x_axis = ti.Vector.field(3, dtype=float, shape=2)
    y_axis = ti.Vector.field(3, dtype=float, shape=2)
    z_axis = ti.Vector.field(3, dtype=float, shape=2)

    x_axis[0], x_axis[1] = origin, [axis_length, 0, 0]  
    y_axis[0], y_axis[1] = origin, [0, axis_length, 0]
    z_axis[0], z_axis[1] = origin, [0, 0, axis_length]
    # Draw the reference frame


    # assign the initial value
    initialize()
    # sorted_pointset = None
    # free_end_pose = None

    # Initialize the ROS node
    rospy.init_node('taichi_node')
    sorted_sub_ = SortedSubscriber()
    rate = rospy.Rate(100)  # 100hz

    while not rospy.is_shutdown():

        if sorted_sub_.free_end_pose is not None:
            # print("value in main loop: " + str(sorted_sub_.free_end_pose.transform.translation.x))
            # x = ti.float64(free_end_pose.transform.translation.x)
            free_end_position = ti.Vector([ sorted_sub_.free_end_pose.transform.translation.x,
                                            sorted_sub_.free_end_pose.transform.translation.y,
                                            sorted_sub_.free_end_pose.transform.translation.z])
            update_free_end(free_end=free_end_position)

            # call the fabrik solver to update the robot end effector position
            x, y, z = robot.ik([free_end_position[0], free_end_position[1], free_end_position[2]], returnFlag=True)
            for i in range(len(x)):
                robot_joint_pos[i] = [x[i], y[i], z[i]]


        if sorted_sub_.sorted_pointset is not None:
            # cube_offset_2 = ti.Vector([sorted_insub_.sorted_pointset[0]])
            fix_end_position = ti.Vector([  sorted_sub_.sorted_pointset.poses[0].position.x,
                                            sorted_sub_.sorted_pointset.poses[0].position.y,
                                            sorted_sub_.sorted_pointset.poses[0].position.z])
            update_fixed_end(fixed_end=fix_end_position)

            optical_readings = ti.Vector.field(
                3, dtype=float, shape=len(sorted_sub_.sorted_pointset.poses))
            for i in range(len(sorted_sub_.sorted_pointset.poses)):
                optical_readings[i] = [sorted_sub_.sorted_pointset.poses[i].position.x,
                                       sorted_sub_.sorted_pointset.poses[i].position.y,
                                       sorted_sub_.sorted_pointset.poses[i].position.z]
            
            # Uncomment the line below to draw the optical readings
            # scene.particles(optical_readings, color=(1, 1, 1), radius=0.05)

        update_cable()
        camera.track_user_inputs(
            window, movement_speed=.03, hold_key=ti.ui.SPACE)
        scene.set_camera(camera)
        scene.ambient_light((1, 1, 1))
        scene.point_light(pos=(0.5, 1.5, 1.5), color=(0.1, 0.91, 0.91))

        
        # Draw the reference frame
        scene.lines(x_axis, color=(1, 0, 0), width=0.05)
        scene.lines(y_axis, color=(0, 1, 0), width=0.05)
        scene.lines(z_axis, color=(0, 0, 1), width=0.05)

        # Draw 3d-lines in the scene
        scene.lines(cable_cur_position, indices= cable_viz_idx, color=(1, 1, 1), width=0.01)
        scene.lines(robot_joint_pos, indices= robot_joint_idx, color=(1, 0.67, 0.0), width= 5.0 )
        scene.particles(robot_joint_pos, color=(1, 1, 1), radius=0.05)
        scene.mesh(cube1_vertex_current, color=(1, 1, 1))
        scene.mesh(cube2_vertex_current, color=(1, 0, 0))

        canvas.scene(scene)
        # gui.text("this is the text that I want to show")
        window.show()

        rate.sleep()
