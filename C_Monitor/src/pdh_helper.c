/**
 * @file pdh_helper.c
 * @brief Implementation of PDH helper functions for advanced Windows metrics
 * 
 * WEEK 2 IMPLEMENTATION:
 * This implements high-level Windows Performance Data Helper (PDH) API access.
 * PDH is Windows' native performance monitoring system that provides:
 * - Accurate CPU, memory, disk metrics
 * - Per-process resource tracking
 * - Real-time performance counters
 * 
 * How PDH Works (Beginner's Guide):
 * 1. Create a Query: Like opening a "measurement session"
 * 2. Add Counters: Tell PDH which metrics to track (CPU, memory, etc.)
 * 3. Collect Data: PDH monitors these in the background
 * 4. Read Values: Query the latest measured values whenever you need them
 * 5. Update: Refresh the measurements before each read
 * 
 * Think of it like a weather station:
 * - Query = Setting up the weather station
 * - Counters = "Measure temperature, humidity, wind"
 * - Update = "Take new measurements"
 * - Read = "Check what the thermometer says now"
 */

#include "pdh_helper.h"
#include <stdlib.h>
#include <string.h>
#include <tlhelp32.h>
#include <windows.h>

/**
 * IMPORTANT: PDH Error Codes
 * PDH functions return PDH_STATUS codes, not traditional HRESULT
 * Common values:
 * - ERROR_SUCCESS: Everything worked
 * - PDH_CSTATUS_NO_OBJECT: Counter object not found
 * - PDH_CSTATUS_NO_COUNTER: Counter not found
 * - PDH_INVALID_ARGUMENT: Bad parameter
 */

/* ============ PRIVATE HELPER FUNCTIONS ============ */

/**
 * Internal: Add a counter to a PDH query
 * This is where we tell PDH "I want to measure this specific thing"
 * 
 * counter_path: Path to the performance counter
 *   Format: "\\Object(instance)\\Counter"
 *   Example: "\\Processor(_Total)\\% Processor Time"
 */
static PDH_STATUS add_counter_to_query(
    PDH_HQUERY hQuery,
    const char *counter_path,
    PDH_HCOUNTER *counter)
{
    // PDH API uses wide character strings, so we need to convert
    wchar_t wide_path[MAX_PATH];
    MultiByteToWideChar(CP_ACP, 0, counter_path, -1, wide_path, MAX_PATH);
    
    // Add the counter to our query
    return PdhAddCounterA(hQuery, counter_path, 0, counter);
}

/**
 * Internal: Read a counter value from PDH
 * Returns the numeric value that PDH measured
 */
static float read_counter_value(PDH_HCOUNTER counter)
{
    PDH_FMT_COUNTERVALUE counter_value;
    PDH_STATUS status;
    
    // Get the counter value and format it as a double
    status = PdhGetFormattedCounterValue(counter, PDH_FMT_DOUBLE, NULL, &counter_value);
    
    if (status == ERROR_SUCCESS) {
        return (float)counter_value.doubleValue;
    }
    return -1.0f; // Error indicator
}

/* ============ PUBLIC FUNCTION IMPLEMENTATIONS ============ */

/**
 * Initialize PDH query system
 * 
 * What this does:
 * 1. Creates a new PDH query handle (measurement session)
 * 2. Adds counters for CPU, memory, disk I/O
 * 3. Starts collecting data in the background
 * 
 * First call always returns ~0% values (PDH needs a baseline)
 * Subsequent calls return accurate data
 */
PDHQuery pdh_init_query(void)
{
    PDHQuery query = {0};
    PDH_STATUS status;
    
    // Step 1: Create a new PDH query
    // Think: "Open a new measurement session"
    status = PdhOpenQuery(NULL, 0, &query.query_handle);
    if (status != ERROR_SUCCESS) {
        printf("[PDH] Error: Failed to open PDH query (0x%08X)\n", status);
        query.is_initialized = 0;
        return query;
    }
    
    // Step 2: Add counters for system-wide metrics
    // These paths are standard Windows PDH counter paths
    
    // CPU counter: "How much of all processors is being used?"
    status = add_counter_to_query(
        query.query_handle,
        "\\Processor(_Total)\\% Processor Time",
        &query.cpu_counter
    );
    if (status != ERROR_SUCCESS) {
        printf("[PDH] Warning: Could not add CPU counter\n");
    }
    
    // Memory counter: "How much memory is used?"
    status = add_counter_to_query(
        query.query_handle,
        "\\Memory\\% Committed Bytes In Use",
        &query.memory_counter
    );
    if (status != ERROR_SUCCESS) {
        printf("[PDH] Warning: Could not add Memory counter\n");
    }
    
    // Disk counter: "How much disk I/O is happening?"
    status = add_counter_to_query(
        query.query_handle,
        "\\PhysicalDisk(_Total)\\% Disk Time",
        &query.disk_counter
    );
    if (status != ERROR_SUCCESS) {
        printf("[PDH] Warning: Could not add Disk counter\n");
    }
    
    // Step 3: Collect initial data
    // PDH needs at least 2 readings to calculate rates
    // So we collect once to establish a baseline
    status = PdhCollectQueryData(query.query_handle);
    if (status != ERROR_SUCCESS) {
        printf("[PDH] Error: Failed to collect initial query data\n");
        query.is_initialized = 0;
        return query;
    }
    
    query.is_initialized = 1;
    printf("[PDH] Successfully initialized PDH query\n");
    return query;
}

/**
 * Get system-wide CPU usage via PDH
 * 
 * This gives you the percentage of total CPU being used
 * Example return values: 15.5 (15.5%), 78.2 (78.2%), etc.
 */
float pdh_get_cpu_usage(PDHQuery *query)
{
    if (!query || !query->is_initialized) {
        return -1.0f;
    }
    
    // Update query to get fresh data
    pdh_update_query(query);
    
    // Read the CPU counter value
    return read_counter_value(query->cpu_counter);
}

/**
 * Get system-wide memory usage via PDH
 * Returns percentage of memory committed (0-100)
 */
float pdh_get_memory_mb(PDHQuery *query)
{
    if (!query || !query->is_initialized) {
        return -1.0f;
    }
    
    // For more accurate memory in MB, we need system total
    // For now, return the counter value (works with other metrics)
    return read_counter_value(query->memory_counter);
}

/**
 * Get disk I/O statistics via PDH
 * Returns percentage of disk time being used
 */
float pdh_get_disk_io(PDHQuery *query)
{
    if (!query || !query->is_initialized) {
        return -1.0f;
    }
    
    return read_counter_value(query->disk_counter);
}

/**
 * Update PDH query - refresh counter values
 * MUST be called before reading counter values
 * 
 * Why is this needed?
 * PDH doesn't constantly update values. Instead, it collects data
 * at intervals. You call this to collect new data.
 * 
 * Think: "OK, PDH, collect the latest measurements"
 */
void pdh_update_query(PDHQuery *query)
{
    if (!query || !query->is_initialized) {
        return;
    }
    
    // Collect data from all counters in this query
    PDH_STATUS status = PdhCollectQueryData(query->query_handle);
    
    // Note: First collection after init always returns 0 values
    // This is PDH behavior - it needs a baseline for rate calculations
    if (status != ERROR_SUCCESS && status != PDH_CSTATUS_VALID_DATA) {
        // Note: PDH_CSTATUS_VALID_DATA means "partial success - some counters worked"
        // This is actually OK for our purposes
        if (status != PDH_CSTATUS_VALID_DATA) {
            // printf("[PDH] Warning: PdhCollectQueryData returned 0x%08X\n", status);
        }
    }
}

/**
 * Cleanup PDH resources
 * Always call this before program exit to avoid resource leaks
 */
void pdh_cleanup_query(PDHQuery *query)
{
    if (!query || !query->is_initialized) {
        return;
    }
    
    // Close the PDH query handle
    if (query->query_handle) {
        PdhCloseQuery(query->query_handle);
    }
    
    query->is_initialized = 0;
    printf("[PDH] Cleaned up PDH query\n");
}

/**
 * Enumerate all running processes and get their metrics
 * 
 * Algorithm:
 * 1. Create a process snapshot (list of running processes)
 * 2. Iterate through each process
 * 3. Get the process name and ID
 * 4. Calculate per-process metrics
 * 5. Sort by CPU usage (descending)
 */
int pdh_get_all_processes(ProcessMetrics *processes, int max_count)
{
    if (!processes || max_count <= 0) {
        return 0;
    }
    
    int count = 0;
    
    // Step 1: Get a snapshot of all running processes
    // TLHELP32 (Tool Help Library) lets us enumerate processes
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    
    if (snapshot == INVALID_HANDLE_VALUE) {
        printf("[PDH] Error: Could not create process snapshot\n");
        return 0;
    }
    
    // Step 2: Prepare to iterate processes
    PROCESSENTRY32 proc_entry = {0};
    proc_entry.dwSize = sizeof(PROCESSENTRY32);
    
    // Get first process
    if (!Process32First(snapshot, &proc_entry)) {
        printf("[PDH] Error: Could not get first process\n");
        CloseHandle(snapshot);
        return 0;
    }
    
    // Step 3: Iterate through all processes
    do {
        if (count >= max_count) {
            break; // Array full
        }
        
        // Copy process data to our array
        processes[count].process_id = proc_entry.th32ProcessID;
        strncpy_s(
            processes[count].process_name,
            sizeof(processes[count].process_name),
            proc_entry.szExeFile,
            sizeof(proc_entry.szExeFile)
        );
        
        // Try to get detailed metrics for this process
        // Note: May fail for some system processes (security restrictions)
        pdh_get_process_metrics(proc_entry.th32ProcessID, &processes[count]);
        
        count++;
        
    } while (Process32Next(snapshot, &proc_entry));
    
    CloseHandle(snapshot);
    
    printf("[PDH] Enumerated %d processes\n", count);
    return count;
}

/**
 * Get metrics for a specific process by PID
 * 
 * Challenge: Getting per-process metrics requires creating
 * PDH counters for each process, which is complex and slow.
 * 
 * Current approach: Set CPU/memory to 0 as placeholder
 * Future enhancement: Create per-process PDH counters
 */
int pdh_get_process_metrics(DWORD process_id, ProcessMetrics *metrics)
{
    if (!metrics) {
        return -1;
    }
    
    metrics->process_id = process_id;
    
    // Try to open the process to verify it's running
    HANDLE process_handle = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, process_id);
    
    if (!process_handle) {
        // Process doesn't exist or we don't have permissions
        return -1;
    }
    
    // TODO: Implement actual per-process PDH counters
    // This is complex and requires creating counters for each process
    // For now, we note that this needs expansion
    
    // Placeholder values (will be enhanced in future updates)
    metrics->cpu_percent = 0.0f;
    metrics->memory_mb = 0.0f;
    metrics->disk_io_mb = 0.0f;
    
    CloseHandle(process_handle);
    return 0;
}

/**
 * Get top N processes by CPU usage
 * 
 * Algorithm:
 * 1. Get all processes
 * 2. Sort by CPU descending
 * 3. Return top N
 */
int pdh_get_top_processes_by_cpu(ProcessMetrics *processes, int count)
{
    if (!processes || count <= 0) {
        return 0;
    }
    
    // Buffer to hold all processes (reasonable limit)
    ProcessMetrics all_processes[500];
    int total = pdh_get_all_processes(all_processes, 500);
    
    if (total == 0) {
        return 0;
    }
    
    // Sort by CPU usage (descending)
    // Simple bubble sort for clarity (not production-grade)
    for (int i = 0; i < total - 1; i++) {
        for (int j = 0; j < total - i - 1; j++) {
            if (all_processes[j].cpu_percent < all_processes[j + 1].cpu_percent) {
                // Swap
                ProcessMetrics temp = all_processes[j];
                all_processes[j] = all_processes[j + 1];
                all_processes[j + 1] = temp;
            }
        }
    }
    
    // Copy top N to output array
    int to_copy = count < total ? count : total;
    memcpy(processes, all_processes, to_copy * sizeof(ProcessMetrics));
    
    return to_copy;
}

/**
 * Get human-readable error message for PDH errors
 */
const char* pdh_get_error_string(PDH_STATUS status)
{
    static char buffer[256];
    
    switch (status) {
        case ERROR_SUCCESS:
            return "Success";
        case PDH_CSTATUS_NO_OBJECT:
            return "Performance object not found";
        case PDH_CSTATUS_NO_COUNTER:
            return "Performance counter not found";
        case PDH_INVALID_ARGUMENT:
            return "Invalid argument";
        case PDH_MEMORY_ALLOCATION_FAILURE:
            return "Memory allocation failed";
        case PDH_CSTATUS_VALID_DATA:
            return "Valid data (partial)";
        default:
            snprintf(buffer, sizeof(buffer), "Unknown error (0x%08X)", status);
            return buffer;
    }
}
