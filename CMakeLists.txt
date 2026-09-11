cmake_minimum_required(VERSION 3.10)
project(SystemResourceMonitor C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Compiler flags for Windows
if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Werror)
endif()

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/C_Monitor/include
    ${CMAKE_CURRENT_SOURCE_DIR}/C_Monitor/third_party
)

# Source files
set(SOURCES
    C_Monitor/src/main.c
    C_Monitor/src/metrics.c
    C_Monitor/src/database.c
    C_Monitor/src/utils.c
    C_Monitor/third_party/sqlite3.c
)

# Create executable
add_executable(system_monitor ${SOURCES})

# Keep warnings visible while allowing the existing code and SQLite amalgamation
# to build with MSVC's non-fatal compatibility warnings.
if(MSVC)
    target_compile_options(system_monitor PRIVATE /WX-)
    set_source_files_properties(C_Monitor/third_party/sqlite3.c
        PROPERTIES COMPILE_OPTIONS "/WX-;/wd4200")
endif()

# For Windows, link additional system libraries
if(WIN32)
    target_link_libraries(system_monitor PRIVATE 
        Psapi
        pdh
        advapi32
        ole32
        oleaut32
        wbemuuid
    )
endif()

# Output directory
set_target_properties(system_monitor PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Compiler flags for optimization and debugging
if(MSVC)
    set(CMAKE_C_FLAGS_DEBUG "/Zi /D_DEBUG /Ob0")
    set(CMAKE_C_FLAGS_RELEASE "/O2 /DNDEBUG")
else()
    set(CMAKE_C_FLAGS_DEBUG "-g -O0 -DDEBUG")
    set(CMAKE_C_FLAGS_RELEASE "-O3 -DNDEBUG")
endif()
