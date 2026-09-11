#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <windows.h>
#include "metrics.h"
#include "database.h"
#include "utils.h"

// Global flag for graceful shutdown
static volatile int should_exit = 0;

/**
 * Signal handler for graceful shutdown
 */
void signal_handler(int signal) {
    if (signal == SIGINT || signal == SIGTERM) {
        log_message(LOG_INFO, "Received shutdown signal (%d), cleaning up...", signal);
        should_exit = 1;
    }
}

/**
 * Main monitoring loop
 */
int monitoring_loop(Database* db, Config* config) {
    if (!db || !config) {
        log_message(LOG_ERROR, "Invalid database or config");
        return -1;
    }

    log_message(LOG_INFO, "Starting monitoring loop (sample interval: %u ms)", 
                config->sample_interval_ms);

    int error_count = 0;
    const int MAX_ERRORS = 10;

    while (!should_exit) {
        // Collect system metrics
        SystemMetrics* sys_metrics = collect_system_metrics();
        if (!sys_metrics) {
            error_count++;
            log_message(LOG_WARN, "Failed to collect system metrics (error %d/%d)", 
                       error_count, MAX_ERRORS);
            if (error_count > MAX_ERRORS) {
                log_message(LOG_ERROR, "Too many errors, exiting");
                return -1;
            }
            sleep_ms(config->sample_interval_ms);
            continue;
        }

        // Store in database
        if (database_insert_system_metrics(db, sys_metrics) != 0) {
            log_message(LOG_WARN, "Failed to insert system metrics into database");
        } else {
            log_message(LOG_DEBUG, 
                       "Recorded metrics - CPU: %.1f%%, Memory: %lu MB, "
                       "Processes: %d",
                       sys_metrics->cpu_usage_percent,
                       sys_metrics->memory_mb,
                       sys_metrics->process_count);
        }

        // Collect process metrics if enabled
        if (config->enable_process_monitoring) {
            int process_count = 0;
            ProcessMetrics* proc_metrics = collect_process_metrics(&process_count);
            
            if (proc_metrics) {
                for (int i = 0; i < process_count; i++) {
                    if (database_insert_process_metrics(db, &proc_metrics[i]) != 0) {
                        log_message(LOG_WARN, 
                                   "Failed to insert process metrics for %s",
                                   proc_metrics[i].process_name);
                    }
                }
                free_process_metrics(proc_metrics);
            }
        }

        free_system_metrics(sys_metrics);
        error_count = 0;  // Reset error count on success

        // Sleep for the configured interval
        sleep_ms(config->sample_interval_ms);
    }

    return 0;
}

/**
 * Main entry point
 */
int main(int argc, char* argv[]) {
    // Initialize logging
    log_init("system_monitor.log");
    log_message(LOG_INFO, "System Resource Monitor starting...");

    // Setup signal handlers for graceful shutdown
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // Load configuration
    Config* config = config_get_default();
    if (!config) {
        log_message(LOG_ERROR, "Failed to load configuration");
        log_close();
        return 1;
    }

    // Initialize database
    Database* db = database_init(config->db_path);
    if (!db) {
        log_message(LOG_ERROR, "Failed to initialize database at %s", config->db_path);
        config_free(config);
        log_close();
        return 1;
    }

    // Create database tables
    if (database_create_tables(db) != 0) {
        log_message(LOG_ERROR, "Failed to create database tables");
        database_close(db);
        config_free(config);
        log_close();
        return 1;
    }

    log_message(LOG_INFO, "Database initialized successfully");

    // Run monitoring loop
    int result = monitoring_loop(db, config);

    // Cleanup
    log_message(LOG_INFO, "Shutting down monitoring loop");
    
    // Perform data cleanup (keep 30 days of data)
    if (database_cleanup_old_data(db, config->retention_days) != 0) {
        log_message(LOG_WARN, "Failed to cleanup old data");
    }

    database_close(db);
    config_free(config);
    log_close();

    log_message(LOG_INFO, "System Resource Monitor stopped");
    return result == 0 ? 0 : 1;
}
