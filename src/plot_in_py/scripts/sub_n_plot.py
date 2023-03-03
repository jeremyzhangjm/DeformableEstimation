#!usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseArray
from matplotlib import pyplot as plt
from mpl_toolkits import mplot3d
import scipy as sp
import numpy as np
from scipy.interpolate import interp1d


# def interp_callback(interp_pointset):
#     # Make sure that the container is empty
#     x_i.clear()
#     y_i.clear()
#     z_i.clear()
#     for i in range(len(interp_pointset.poses)):
#         x_i.append(interp_pointset.poses[i].position.x)
#         y_i.append(interp_pointset.poses[i].position.y)
#         z_i.append(interp_pointset.poses[i].position.z)

#     # rospy.loginfo('Pose are successfully catched in Pyhton!')


def sorted_callback(sorted_pointset):
    # Make sure that the container is empty
    x_s.clear()
    y_s.clear()
    z_s.clear()
    for i in range(len(sorted_pointset.poses)):
        x_s.append(sorted_pointset.poses[i].position.x)
        y_s.append(sorted_pointset.poses[i].position.y)
        z_s.append(sorted_pointset.poses[i].position.z)



    visualize()
    
def interpolation_sorted(x:np.ndarray):
    t = np.linspace(0,1,len(x))
    f = interp1d(t, x, kind='cubic')
    interp_x = f(interp_param)

    return interp_x

def visualize():

    ax.clear()
    x = interpolation_sorted(np.array(x_s))
    y = interpolation_sorted(np.array(y_s))
    z = interpolation_sorted(np.array(z_s))
    ax.plot3D(x, y, z, 'Green', label='Interpolated Curve')
    x,y,z = np.array(x_s), np.array(y_s), np.array(z_s)
    ax.scatter3D(x_s, y_s, z_s, color='red', label='Sorted Knots')
    ax.text3D(x_s[0], y_s[0], z_s[0] + 50, 'Fixed End', color='black')
    ax.text3D(x_s[len(x_s)-1], y_s[len(y_s)-1], z_s[len(z_s)-1] + 50, 'Free End', color='black')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
 # type: ignore
    ax.set_xlim(left=-400, right=600)
    ax.set_ylim(-600, 600)
    ax.set_zlim(-1500, -900)
 # type: ignore
    ax.legend()
    ax.set_title('Real-time Interpolation')
    plt.draw()
    plt.pause(0.001)


if __name__ == "__main__":

    x_s,y_s,z_s = [],[],[] # sorted x,y,z
    interp_param = np.linspace(0,1,100)

    fig = plt.figure()
    ax = plt.axes(projection='3d')

    rospy.init_node('ploter', anonymous=True)
    rate = rospy.Rate(100)  # 10hz
    # rospy.Subscriber("Interp", PoseArray, interp_callback)
    rospy.Subscriber("Sorted", PoseArray, sorted_callback)

    while not rospy.is_shutdown():
        plt.show()

        rate.sleep()
