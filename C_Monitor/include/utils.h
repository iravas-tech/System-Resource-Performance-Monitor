#ifndef UTILS_H
#define UTILS_H

#include <stdio.h>

/**
 * Log levels
 */
typedef enum {
    LOG_DEBUG = 0,
    LOG_INFO = 1,
    LOG_WARN = 2,
    LOG_ERROR = 3
} LogLevel;

/**
 * Initialize logging
 */
void log_init(const char* log_file);

/**
 * Log message with level
 */
void log_message(LogLevel level, const char* format, ...);

/**
 * Close logging
 */
void log_close(void);

/**
 * Sleep for milliseconds
 */
void sleep_ms(unsigned int milliseconds);

/**
 * Get current timestamp
 */
time_t get_current_timestamp(void);

/**
 * Configuration structure
 */
typedef struct {
    unsigned int sample_interval_ms;  // How often to collect metrics (milliseconds)
    unsigned int retention_days;      // How long to keep data (days)
    const char* db_path;              // Path to SQLite database
    const char* log_file;             // Path to log file
    int enable_process_monitoring;    // Enable per-process metrics (1=yes, 0=no)
} Config;

/**
 * Load configuration from file
 */
Config* config_load(const char* config_file);

/**
 * Get default configuration
 */
Config* config_get_default(void);

/**
 * Free configuration
 */
void config_free(Config* config);

#endif  // UTILS_H
