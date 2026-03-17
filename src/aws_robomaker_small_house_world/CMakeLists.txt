cmake_minimum_required(VERSION 3.5)
project(aws_robomaker_small_house_world)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY models worlds photos
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
