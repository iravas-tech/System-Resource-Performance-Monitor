#ifndef DATABASE_H
#define DATABASE_H

#include "metrics.h"
#include <sqlite3.h>

typedef struct {
    sqlite3* db;
    const char* db_path;
} Database;

/**
 * Initialize database connection
 * Returns Database struct with connection or NULL on error
 */
Database* database_init(const char* db_path);

/**
 * Create tables if they don't exist
 */
int database_create_tables(Database* db);

/**
 * Insert system metrics into database
 */
int database_insert_system_metrics(Database* db, const SystemMetrics* metrics);

/**
 * Insert process metrics into database
 */
int database_insert_process_metrics(Database* db, const ProcessMetrics* metrics);

/**
 * Query metrics from a time range
 * Returns array of SystemMetrics or NULL on error
 */
SystemMetrics* database_query_metrics(Database* db, 
                                      time_t start_time, 
                                      time_t end_time,
                                      int* count);

/**
 * Get latest metrics
 */
SystemMetrics* database_get_latest_metrics(Database* db);

/**
 * Cleanup old data (older than days_to_keep)
 */
int database_cleanup_old_data(Database* db, int days_to_keep);

/**
 * Close database connection
 */
void database_close(Database* db);

#endif  // DATABASE_H
