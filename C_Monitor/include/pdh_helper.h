/**
 * @file pdh_helper.h
 * @brief Windows Performance Data Helper (PDH) integration for advanced metrics
 * 
 * WEEK 2 ENHANCEMENT:
 * This module provides high-level access to Windows PDH API for accurate
 * performance counter readings. PDH is Windows' official performance monitoring
 * API that gives us precise CPU, disk, and network metrics.
 * 
 * Why PDH?
 * - More accurate than basic Windows API functions
 * - Per-process metrics (which process uses how much CPU/disk)
 * - Real-time performance counters
 * - Industry standard for Windows monitoring
 */

#ifndef PDH_HELPER_H
#define PDH_HELPER_H

#include <pdh.h>
#include <pdh.h>
#include <stdio.h>

#pragma comment(lib, "pdh.lib")

/**
 * PDH Query handle - maintains state for counter queries
 * Think of it like a "measurement session" - you set it up once,
 * then query it repeatedly to get updated values
 */
typedef struct {
    PDH_HQUERY query_handle;      // Main query handle
    PDH_HCOUNTER cpu_counter;     // Counter for system CPU
    PDH_HCOUNTER memory_counter;  // Counter for memory
    PDH_HCOUNTER disk_counter;    // Counter for disk I/O
    int is_initialized;           // Flag: has this been set up?
} PDHQuery;

/**
 * Per-process metrics structure
 * Stores CPU, memory, and I/O data for individual processes
 */
typedef struct {
    DWORD process_id;             // Windows Process ID
    char process_name[256];       // Process executable name
    float cpu_percent;            // CPU usage percentage (0-100)
    float memory_mb;              // Memory in megabytes
    float disk_io_mb;             // Disk I/O in MB/sec
} ProcessMetrics;

/* ============ FUNCTION DECLARATIONS ============ */

/**
 * Initialize PDH query system
 * Must be called once before any PDH operations
 * 
 * Usage:
 *   PDHQuery query = pdh_init_query();
 *   if (query.is_initialized) { // Check success
 *       // Ready to query
 *   }
 */
PDHQuery pdh_init_query(void);

/**
 * Get system-wide CPU usage percentage via PDH
 * More accurate than basic Windows API
 * 
 * Returns: CPU usage as percentage (0-100), or -1 on error
 */
float pdh_get_cpu_usage(PDHQuery *query);

/**
 * Get system-wide memory usage via PDH
 * 
 * Returns: Memory usage in MB, or -1 on error
 */
float pdh_get_memory_mb(PDHQuery *query);

/**
 * Get disk I/O statistics via PDH
 * 
 * Returns: Disk I/O in MB/sec, or -1 on error
 */
float pdh_get_disk_io(PDHQuery *query);

/**
 * Enumerate all running processes and get their metrics
 * 
 * Parameters:
 *   processes - array to store results
 *   max_count - maximum number of processes to return
 * 
 * Returns: Actual number of processes enumerated
 * 
 * Example:
 *   ProcessMetrics processes[500];
 *   int count = pdh_get_all_processes(processes, 500);
 *   for (int i = 0; i < count; i++) {
 *       printf("Process: %s, CPU: %.2f%%\n", 
 *              processes[i].process_name, 
 *              processes[i].cpu_percent);
 *   }
 */
int pdh_get_all_processes(ProcessMetrics *processes, int max_count);

/**
 * Get metrics for a specific process by PID
 * 
 * Parameters:
 *   process_id - Windows Process ID
 *   metrics - output structure
 * 
 * Returns: 0 on success, -1 on failure
 */
int pdh_get_process_metrics(DWORD process_id, ProcessMetrics *metrics);

/**
 * Get top N processes by CPU usage
 * Useful for quickly finding what's consuming resources
 * 
 * Parameters:
 *   processes - array to store results
 *   count - number of top processes to return
 * 
 * Returns: Actual number of processes returned
 * 
 * Example - Get top 5 CPU hogs:
 *   ProcessMetrics top[5];
 *   int found = pdh_get_top_processes_by_cpu(top, 5);
 */
int pdh_get_top_processes_by_cpu(ProcessMetrics *processes, int count);

/**
 * Update PDH query - required before each query operation
 * PDH collects data asynchronously, so you must "update" the query
 * to refresh counter values
 * 
 * This is like saying "OK PDH, collect the latest numbers"
 */
void pdh_update_query(PDHQuery *query);

/**
 * Cleanup PDH resources
 * Call this when done with PDH operations (usually at program exit)
 */
void pdh_cleanup_query(PDHQuery *query);

/* ============ ERROR HANDLING ============ */

/**
 * Get human-readable error message for PDH errors
 * 
 * Usage:
 *   printf("PDH Error: %s\n", pdh_get_error_string(error_code));
 */
const char* pdh_get_error_string(PDH_STATUS status);

#endif // PDH_HELPER_H
