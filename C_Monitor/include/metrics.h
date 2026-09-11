#ifndef METRICS_H
#define METRICS_H

#include <time.h>

typedef struct {
    time_t timestamp;
    float cpu_usage_percent;
    unsigned long memory_mb;
    unsigned long memory_available_mb;
    unsigned long disk_read_bytes;
    unsigned long disk_write_bytes;
    unsigned long network_bytes_sent;
    unsigned long network_bytes_recv;
    int process_count;
    float cpu_temp_celsius;  // Future: GPU/CPU temperature
} SystemMetrics;

typedef struct {
    int process_id;
    char process_name[256];
    float cpu_usage_percent;
    unsigned long memory_mb;
    unsigned long disk_io_bytes;
    unsigned long network_bytes;
    time_t timestamp;
} ProcessMetrics;

/**
 * Collect system-wide metrics
 * Returns allocated SystemMetrics struct or NULL on error
 */
SystemMetrics* collect_system_metrics(void);

/**
 * Collect per-process metrics
 * Returns array of ProcessMetrics or NULL on error
 * Sets count to number of processes
 */
ProcessMetrics* collect_process_metrics(int* count);

/**
 * Free allocated metrics memory
 */
void free_system_metrics(SystemMetrics* metrics);
void free_process_metrics(ProcessMetrics* metrics);

/**
 * Get CPU usage for all cores
 */
float get_system_cpu_usage(void);

/**
 * Get total memory usage in MB
 */
unsigned long get_system_memory_usage(void);

/**
 * Get available memory in MB
 */
unsigned long get_available_memory(void);

#endif  // METRICS_H
