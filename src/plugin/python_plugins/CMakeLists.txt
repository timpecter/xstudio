add_python_plugin(viewport_flag_indicator)
add_python_plugin(picture_in_picture)
add_python_plugin(on_screen_version_name)
add_python_plugin(viewport_field_chart)
add_python_plugin(annotations_exporter)
add_python_plugin(basic_viewport_mask)
add_python_plugin(utility)
if(WIN32)
    add_python_plugin(controller_input)
    if(BUILD_TESTING)
        add_test(NAME controller_input_python_test
            COMMAND ${Python_EXECUTABLE} -B -m unittest discover
                -s "${PROJECT_SOURCE_DIR}/python/test/controller_input" -v)
        find_program(CONTROLLER_QMLTESTRUNNER qmltestrunner
            HINTS "${Qt6_DIR}/../../../bin")
        if(CONTROLLER_QMLTESTRUNNER)
            add_test(NAME controller_input_mapping_test
                COMMAND ${Python_EXECUTABLE} -B
                    "${PROJECT_SOURCE_DIR}/python/test/controller_input/check_mapping.py"
                    "${CONTROLLER_QMLTESTRUNNER}")
            add_test(NAME controller_input_overlay_test
                COMMAND ${Python_EXECUTABLE} -B
                    "${PROJECT_SOURCE_DIR}/python/test/controller_input/check_overlay.py"
                    "${CONTROLLER_QMLTESTRUNNER}")
        endif()
    endif()
endif()