project(controller_input VERSION ${XSTUDIO_GLOBAL_VERSION} LANGUAGES CXX)

add_library(${PROJECT_NAME} SHARED input.cpp bindings.cpp controller_plugin.cpp)
default_plugin_options(${PROJECT_NAME})
target_link_libraries(${PROJECT_NAME}
	PUBLIC xstudio::plugin_manager
	PRIVATE Xinput
)
