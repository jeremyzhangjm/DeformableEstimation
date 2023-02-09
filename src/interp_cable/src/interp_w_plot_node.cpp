#include <ros/ros.h>
#include <geometry_msgs/PoseArray.h>
#include <interp_cable/sort.hpp>

#include <interp_cable/utilities.hpp>
#include <interp_cable/paraspline.hpp>
#include <interp_cable/matplotlibcpp.h>

namespace plt = matplotlibcpp;

std::vector<std::vector<double>> PointSet;
std::vector<double> startN; // Known normal vector for the starting
std::vector<double> startP; // Known starting point coordinates
double theta_max = M_PI;
double theta_min = 0.0;
double dL = 200;
double sigma = 0.25 * dL;

void printv(std::vector<double> &a)
{
    for (int i = 0; i < a.size(); i++)
    {
        std::cout << a[i] << ", ";
    }
    std::cout << std::endl;
}

void NDI_point_callback(const geometry_msgs::PoseArray &p)
{
    // std::cout<<"get in callback\n";
    PointSet.clear();
    startP.clear();
    std::vector<double> temp; // Temporary point tuple of (x,y,z)
    //------------------------------------------------------------------------------
    // extract the coordinates form the pose array
    // std::cout<<"arrive here\n";
    for (int i = 0; i < p.poses.size(); i++)
    {
        // std::cout<<"arrive here\n";
        temp.push_back(p.poses[i].position.x);
        temp.push_back(p.poses[i].position.y);
        temp.push_back(p.poses[i].position.z);
        if (i == 0)
        {
            startP = temp;
        }
        else
        {
            // std::cout<<"length is :"<<i<<std::endl;
            PointSet.push_back(temp);
        }
        temp.clear();
    }

    if (PointSet.size() >= 1)
    {
        ROS_INFO("Poses are caught!");
    }
};

void NDI_vector_callback(const geometry_msgs::Pose &v)
{
    startN.clear();
    startN.push_back(v.position.x);
    startN.push_back(v.position.y);
    startN.push_back(v.position.z);
};

void set_direction()
{
    startN.clear();
    startN.push_back(377.1 - 382.0);
    startN.push_back(-1.8 - (-46.1));
    startN.push_back(-1090.6 - (-1070.6));
};

int main(int argc, char **argv)
{
    // Initialize ROS stuff
    //------------------------------------------------------------------------------
    ros::init(argc, argv, "Sorting");
    ros::NodeHandle nh;
    ros::Subscriber NDI_point_sub_;
    ros::Subscriber NDI_vector_sub_;
    ros::Publisher sorted_pub_;

    // get parameters
    //------------------------------------------------------------------------------
    // if(nh.getParam(/theta_max, theta_max)){
    // }

    // Initialize object to plot
    //------------------------------------------------------------------------------
    std::vector<double> plot_x, plot_y, plot_z;

    //------------------------------------------------------------------------------
    // Subscribe to the stray markers
    NDI_point_sub_ = nh.subscribe("/NDI/measured_cp_array", 1, NDI_point_callback);
    NDI_vector_sub_ = nh.subscribe("/Normal_vec", 10, NDI_vector_callback);
    sorted_pub_ = nh.advertise<geometry_msgs::PoseArray>("/cpp_test", 10);
    // set_direction();
    ros::Rate rate(50);
    // plt::figure();
    while (nh.ok())
    {
        // std::cout<<"arrive sub\n";

        //------------------------------------------------------------------------------
        // sort the points here
        if (NDI_point_sub_.getNumPublishers() != 0)
        {
            if (PointSet.size() != 0)
            {
                Cable::Sort sort(theta_max, theta_min, dL, sigma, startP, startN);
                sort.fsort(PointSet);

                // Publish the result
                geometry_msgs::Pose p_temp;
                geometry_msgs::PoseArray output;
                for (int i = 0; i < PointSet.size(); i++)
                {
                    p_temp.position.x = PointSet[i][0];
                    p_temp.position.y = PointSet[i][1];
                    p_temp.position.z = PointSet[i][2];

                    output.poses.push_back(p_temp);
                    // std::cout << output.poses[i].position.x << "\n"
                    //           << output.poses[i].position.y << "\n"
                    //           << output.poses[i].position.z << std::endl;
                }

                sorted_pub_.publish(output);

                ////////////////////////////////////////////////////////////////////////////
                ///////// Plot Using Matplotlib-cpp Bridge//////////////////////////////////
                ////////////////////////////////////////////////////////////////////////////
                for (int i = 0; i < PointSet.size(); i++)
                {
                    plot_x.push_back(PointSet[i][0]);
                    plot_y.push_back(PointSet[i][1]);
                    plot_z.push_back(PointSet[i][2]);
                }

                // plt::close();
                ////////////////////////////////////////////////////////////////////////////
                ////////////////////////////////////////////////////////////////////////////

                ////////////////////////////////////////////////////////////////////////////
                ///////////// Perform spline interpolation//////////////////////////////////
                ////////////////////////////////////////////////////////////////////////////
                std::vector<std::vector<double>> PlotSet;
                auto interp_space = linspace(0.0, 1.0, plot_x.size());
                std::vector<double> interp_obj;
                std::vector<double> interp_plot;

                Cable::paraspline * spline;
                for (int i = 0; i < 3; i++)
                {
                    ROS_INFO("Loop Start");
                    spline = new Cable::paraspline;
                    spline->set_boundary(Cable::paraspline::bound_type::first_order, 0.0,
                                        Cable::paraspline::bound_type::first_order, 0.0);

                    if (i == 0)
                    {
                        interp_obj = plot_x;
                    }
                    else if (i == 1)
                    {
                        interp_obj = plot_y;
                    }
                    else if (i == 2)
                    {
                        interp_obj = plot_z;
                    }
                    ROS_INFO_STREAM("the length of the interpolation object is " << interp_obj.size());
                    spline->set_points(interp_space, interp_obj, Cable::paraspline::cubic);

                    auto fine_space = linspace(interp_obj[0], interp_obj[plot_x.size() - 1], 100);
                    for (int j = 0; j < 99; j++)
                    {
                        // std::cout << fine_space[j] << std::endl;

                        // interp_plot.push_back(spline(fine_space[j]));
                        interp_plot.push_back(spline->operator()(fine_space[j]));
                    }

                    // std::cout<< i << "th iteration" << std::endl;

                    // spline.~paraspline();
                    PlotSet.push_back(interp_obj);

                    interp_obj.clear();
                    interp_plot.clear();
                    spline->~paraspline();
                    delete spline;
                    ROS_INFO("Loop end");
                }

                plt::clf();
                std::vector<double> temp_x = PlotSet[0];
                std::vector<double> temp_y = PlotSet[1];

                plt::plot(temp_x, temp_y); // 2D plot animation works fine
                // plt::scatter(plot_x,plot_y,plot_z);
                // plt::show();
                plt::pause(0.01);
                plot_x.clear();
                plot_y.clear();
                plot_z.clear();
            }
        }
        PointSet.clear();
        startP.clear();

        ros::spinOnce();
        rate.sleep();
    }

    return 0;
};