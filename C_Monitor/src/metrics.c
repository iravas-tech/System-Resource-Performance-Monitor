#include "metrics.h"
#include "utils.h"
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <psapi.h>
#include <pdh.h>
#include <stdio.h>

#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "pdh.lib")

// PDH query handle for performance counters
static PDH_HQUERY g_pdhQuery = NULL;
static PDH_HCOUNTER g_cpuCounter = NULL;
static int g_pdh_initialized = 0;

/**
 * Initialize PDH (Performance Data Helper) for CPU metrics
 */
static int pdh_init(void) {
    if (g_pdh_initialized) {
        return 0;
    }

    PDH_STATUS status;

    // Create a query
    status = PdhOpenQuery(NULL, 0, &g_pdhQuery);
    if (status != ERROR_SUCCESS) {
        log_message(LOG_WARN, "Failed to open PDH query: 0x%x", status);
        return -1;
    }

    // Add counter for total CPU usage
    status = PdhAddCounter(g_pdhQuery, 
                          "\\Processor(_Total)\\% Processor Time",
                          0, 
                          &g_cpuCounter);
    if (status != ERROR_SUCCESS) {
        log_message(LOG_WARN, "Failed to add CPU counter: 0x%x", status);
        PdhCloseQuery(&g_pdhQuery);
        return -1;
    }

    // Collect initial data
    status = PdhCollectQueryData(g_pdhQuery);
    if (status != ERROR_SUCCESS) {
        log_message(LOG_WARN, "Failed to collect initial PDH data: 0x%x", status);
        PdhRemoveCounter(g_cpuCounter);
        PdhCloseQuery(&g_pdhQuery);
        return -1;
    }

    g_pdh_initialized = 1;
    log_message(LOG_DEBUG, "PDH initialized successfully");
    return 0;
}

/**
 * Get system CPU usage
 */
float get_system_cpu_usage(void) {
    if (!g_pdh_initialized && pdh_init() != 0) {
        return 0.0f;
    }

    PDH_STATUS status;
    PDH_FMT_COUNTERVALUE counterValue;

    // Collect current query data
    status = PdhCollectQueryData(g_pdhQuery);
    if (status != ERROR_SUCCESS) {
        log_message(LOG_DEBUG, "Failed to collect PDH data: 0x%x", status);
        return 0.0f;
    }

    // Get formatted counter value
    status = PdhGetFormattedCounterValue(g_cpuCounter, 
                                        PDH_FMT_DOUBLE,
                                        NULL,
                                        &counterValue);
    if (status != ERROR_SUCCESS) {
        log_message(LOG_DEBUG, "Failed to get CPU counter value: 0x%x", status);
        return 0.0f;
    }

    float cpu_usage = (float)counterValue.doubleValue;
    return (cpu_usage < 0.0f) ? 0.0f : cpu_usage;
}

/**
 * Get total system memory usage in MB
 */
unsigned long get_system_memory_usage(void) {
    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(MEMORYSTATUSEX);

    if (!GlobalMemoryStatusEx(&memStatus)) {
        log_message(LOG_WARN, "Failed to get memory status");
        return 0;
    }

    // Return used memory in MB (total - available)
    unsigned long total_mb = memStatus.ullTotalPhys / (1024 * 1024);
    unsigned long available_mb = memStatus.ullAvailPhys / (1024 * 1024);
    unsigned long used_mb = total_mb - available_mb;

    return used_mb;
}

/**
 * Get available memory in MB
 */
unsigned long get_available_memory(void) {
    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(MEMORYSTATUSEX);

    if (!GlobalMemoryStatusEx(&memStatus)) {
        log_message(LOG_WARN, "Failed to get memory status");
        return 0;
    }

    return memStatus.ullAvailPhys / (1024 * 1024);
}

/**
 * Collect system-wide metrics
 */
SystemMetrics* collect_system_metrics(void) {
    SystemMetrics* metrics = (SystemMetrics*)malloc(sizeof(SystemMetrics));
    if (!metrics) {
        log_message(LOG_ERROR, "Failed to allocate memory for SystemMetrics");
        return NULL;
    }

    memset(metrics, 0, sizeof(SystemMetrics));

    // Get timestamp
    metrics->timestamp = time(NULL);

    // Get CPU usage
    metrics->cpu_usage_percent = get_system_cpu_usage();

    // Get memory info
    MEMORYSTATUSEX memStatus;
    memStatus.dwLength = sizeof(MEMORYSTATUSEX);
    if (!GlobalMemoryStatusEx(&memStatus)) {
        log_message(LOG_WARN, "Failed to get memory status");
        free(metrics);
        return NULL;
    }

    metrics->memory_mb = memStatus.ullTotalPhys / (1024 * 1024) - 
                        memStatus.ullAvailPhys / (1024 * 1024);
    metrics->memory_available_mb = memStatus.ullAvailPhys / (1024 * 1024);

    // Get process count
    DWORD aProcesses[1024], cProcesses;
    if (!EnumProcesses(aProcesses, sizeof(aProcesses), &cProcesses)) {
        log_message(LOG_WARN, "Failed to enumerate processes");
        metrics->process_count = 0;
    } else {
        metrics->process_count = (int)(cProcesses / sizeof(DWORD));
    }

    // Disk and network I/O (simplified - would need more implementation)
    metrics->disk_read_bytes = 0;
    metrics->disk_write_bytes = 0;
    metrics->network_bytes_sent = 0;
    metrics->network_bytes_recv = 0;
    metrics->cpu_temp_celsius = 0.0f;

    return metrics;
}

/**
 * Collect per-process metrics
 */
ProcessMetrics* collect_process_metrics(int* count) {
    if (!count) {
        log_message(LOG_ERROR, "Invalid count pointer");
        return NULL;
    }

    DWORD aProcesses[1024], cProcesses;
    if (!EnumProcesses(aProcesses, sizeof(aProcesses), &cProcesses)) {
        log_message(LOG_WARN, "Failed to enumerate processes");
        *count = 0;
        return NULL;
    }

    int process_count = (int)(cProcesses / sizeof(DWORD));
    ProcessMetrics* metrics = (ProcessMetrics*)malloc(process_count * sizeof(ProcessMetrics));
    
    if (!metrics) {
        log_message(LOG_ERROR, "Failed to allocate memory for ProcessMetrics");
        *count = 0;
        return NULL;
    }

    memset(metrics, 0, process_count * sizeof(ProcessMetrics));

    int valid_processes = 0;
    time_t current_time = time(NULL);

    for (int i = 0; i < process_count; i++) {
        HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                     FALSE,
                                     aProcesses[i]);
        
        if (!hProcess) {
            continue;
        }

        // Get process name
        HMODULE hMod[1];
        DWORD cbNeeded;
        if (EnumProcessModules(hProcess, hMod, sizeof(hMod), &cbNeeded)) {
            GetModuleBaseName(hProcess, hMod[0], 
                            metrics[valid_processes].process_name,
                            sizeof(metrics[valid_processes].process_name));
        }

        // Get memory usage
        PROCESS_MEMORY_COUNTERS_EX pmc;
        if (GetProcessMemoryInfo(hProcess, (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
            metrics[valid_processes].memory_mb = pmc.WorkingSetSize / (1024 * 1024);
        }

        metrics[valid_processes].process_id = aProcesses[i];
        metrics[valid_processes].timestamp = current_time;
        metrics[valid_processes].cpu_usage_percent = 0.0f;  // TODO: Implement CPU per-process
        metrics[valid_processes].disk_io_bytes = 0;         // TODO: Implement disk I/O per-process
        metrics[valid_processes].network_bytes = 0;         // TODO: Implement network per-process

        valid_processes++;
        CloseHandle(hProcess);
    }

    *count = valid_processes;
    return metrics;
}

/**
 * Free system metrics
 */
void free_system_metrics(SystemMetrics* metrics) {
    if (metrics) {
        free(metrics);
    }
}

/**
 * Free process metrics
 */
void free_process_metrics(ProcessMetrics* metrics) {
    if (metrics) {
        free(metrics);
    }
}
