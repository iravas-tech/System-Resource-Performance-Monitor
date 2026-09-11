#include "utils.h"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <windows.h>

// Global logging state
static FILE* g_log_file = NULL;
static LogLevel g_log_level = LOG_INFO;

/**
 * Initialize logging
 */
void log_init(const char* log_file) {
    if (log_file) {
        g_log_file = fopen(log_file, "a");
        if (!g_log_file) {
            fprintf(stderr, "Failed to open log file: %s\n", log_file);
            g_log_file = stdout;
        }
    } else {
        g_log_file = stdout;
    }
}

/**
 * Get log level string
 */
static const char* log_level_string(LogLevel level) {
    switch (level) {
        case LOG_DEBUG: return "DEBUG";
        case LOG_INFO:  return "INFO ";
        case LOG_WARN:  return "WARN ";
        case LOG_ERROR: return "ERROR";
        default:        return "UNKNOWN";
    }
}

/**
 * Log message with level
 */
void log_message(LogLevel level, const char* format, ...) {
    if (level < g_log_level || !g_log_file) {
        return;
    }

    // Get current time
    time_t now = time(NULL);
    struct tm* timeinfo = localtime(&now);
    char time_str[32];
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", timeinfo);

    // Write timestamp and level
    fprintf(g_log_file, "[%s] %s | ", time_str, log_level_string(level));

    // Write formatted message
    va_list args;
    va_start(args, format);
    vfprintf(g_log_file, format, args);
    va_end(args);

    // Write newline
    fprintf(g_log_file, "\n");

    // Flush to ensure data is written
    fflush(g_log_file);
}

/**
 * Close logging
 */
void log_close(void) {
    if (g_log_file && g_log_file != stdout && g_log_file != stderr) {
        fclose(g_log_file);
        g_log_file = NULL;
    }
}

/**
 * Sleep for milliseconds
 */
void sleep_ms(unsigned int milliseconds) {
    Sleep(milliseconds);
}

/**
 * Get current timestamp
 */
time_t get_current_timestamp(void) {
    return time(NULL);
}

/**
 * Get default configuration
 */
Config* config_get_default(void) {
    Config* config = (Config*)malloc(sizeof(Config));
    if (!config) {
        log_message(LOG_ERROR, "Failed to allocate memory for Config");
        return NULL;
    }

    // Default configuration values
    config->sample_interval_ms = 5000;      // Sample every 5 seconds
    config->retention_days = 30;             // Keep 30 days of data
    config->db_path = "data/metrics.db";     // SQLite database path
    config->log_file = "system_monitor.log"; // Log file path
    config->enable_process_monitoring = 1;   // Enable per-process metrics

    log_message(LOG_DEBUG, 
               "Default config: interval=%ums, retention=%d days, "
               "db=%s, log=%s, processes=%s",
               config->sample_interval_ms,
               config->retention_days,
               config->db_path,
               config->log_file,
               config->enable_process_monitoring ? "enabled" : "disabled");

    return config;
}

/**
 * Load configuration from file
 */
Config* config_load(const char* config_file) {
    if (!config_file) {
        log_message(LOG_WARN, "No config file specified, using defaults");
        return config_get_default();
    }

    // TODO: Implement INI/JSON config file parsing
    log_message(LOG_INFO, "Config file loading not yet implemented: %s", config_file);
    return config_get_default();
}

/**
 * Free configuration
 */
void config_free(Config* config) {
    if (config) {
        free(config);
    }
}
