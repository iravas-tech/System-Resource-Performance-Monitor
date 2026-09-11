#include "database.h"
#include "utils.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/**
 * Initialize database connection
 */
Database* database_init(const char* db_path) {
    if (!db_path) {
        log_message(LOG_ERROR, "Invalid database path");
        return NULL;
    }

    Database* db = (Database*)malloc(sizeof(Database));
    if (!db) {
        log_message(LOG_ERROR, "Failed to allocate memory for Database");
        return NULL;
    }

    db->db_path = db_path;
    db->db = NULL;

    // Open SQLite database
    int rc = sqlite3_open(db_path, &db->db);
    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to open database: %s", sqlite3_errmsg(db->db));
        free(db);
        return NULL;
    }

    // Enable WAL mode for better concurrency
    sqlite3_exec(db->db, "PRAGMA journal_mode=WAL;", NULL, NULL, NULL);

    // Set synchronous to NORMAL for performance
    sqlite3_exec(db->db, "PRAGMA synchronous=NORMAL;", NULL, NULL, NULL);

    log_message(LOG_INFO, "Database opened: %s", db_path);
    return db;
}

/**
 * Create database tables
 */
int database_create_tables(Database* db) {
    if (!db || !db->db) {
        log_message(LOG_ERROR, "Invalid database pointer");
        return -1;
    }

    const char* sql = 
        "CREATE TABLE IF NOT EXISTS system_metrics ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  timestamp INTEGER NOT NULL,"
        "  cpu_usage_percent REAL,"
        "  memory_mb INTEGER,"
        "  memory_available_mb INTEGER,"
        "  disk_read_bytes INTEGER,"
        "  disk_write_bytes INTEGER,"
        "  network_bytes_sent INTEGER,"
        "  network_bytes_recv INTEGER,"
        "  process_count INTEGER,"
        "  cpu_temp_celsius REAL"
        ");"
        ""
        "CREATE TABLE IF NOT EXISTS process_metrics ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  timestamp INTEGER NOT NULL,"
        "  process_id INTEGER,"
        "  process_name TEXT,"
        "  cpu_usage_percent REAL,"
        "  memory_mb INTEGER,"
        "  disk_io_bytes INTEGER,"
        "  network_bytes INTEGER"
        ");"
        ""
        "CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp "
        "  ON system_metrics(timestamp);"
        ""
        "CREATE INDEX IF NOT EXISTS idx_process_metrics_timestamp "
        "  ON process_metrics(timestamp);"
        ""
        "CREATE INDEX IF NOT EXISTS idx_process_metrics_pid "
        "  ON process_metrics(process_id);";

    char* errmsg = 0;
    int rc = sqlite3_exec(db->db, sql, 0, 0, &errmsg);

    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "SQL error: %s", errmsg);
        sqlite3_free(errmsg);
        return -1;
    }

    log_message(LOG_DEBUG, "Database tables created/verified");
    return 0;
}

/**
 * Insert system metrics into database
 */
int database_insert_system_metrics(Database* db, const SystemMetrics* metrics) {
    if (!db || !db->db || !metrics) {
        log_message(LOG_ERROR, "Invalid database or metrics pointer");
        return -1;
    }

    const char* sql = 
        "INSERT INTO system_metrics ("
        "  timestamp, cpu_usage_percent, memory_mb, memory_available_mb,"
        "  disk_read_bytes, disk_write_bytes, network_bytes_sent,"
        "  network_bytes_recv, process_count, cpu_temp_celsius"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);";

    sqlite3_stmt* stmt = NULL;
    int rc = sqlite3_prepare_v2(db->db, sql, -1, &stmt, NULL);

    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare SQL statement: %s", 
                   sqlite3_errmsg(db->db));
        return -1;
    }

    // Bind parameters
    sqlite3_bind_int64(stmt, 1, (sqlite3_int64)metrics->timestamp);
    sqlite3_bind_double(stmt, 2, metrics->cpu_usage_percent);
    sqlite3_bind_int64(stmt, 3, metrics->memory_mb);
    sqlite3_bind_int64(stmt, 4, metrics->memory_available_mb);
    sqlite3_bind_int64(stmt, 5, metrics->disk_read_bytes);
    sqlite3_bind_int64(stmt, 6, metrics->disk_write_bytes);
    sqlite3_bind_int64(stmt, 7, metrics->network_bytes_sent);
    sqlite3_bind_int64(stmt, 8, metrics->network_bytes_recv);
    sqlite3_bind_int(stmt, 9, metrics->process_count);
    sqlite3_bind_double(stmt, 10, metrics->cpu_temp_celsius);

    // Execute statement
    rc = sqlite3_step(stmt);
    if (rc != SQLITE_DONE) {
        log_message(LOG_WARN, "Failed to execute insert statement: %s",
                   sqlite3_errmsg(db->db));
        sqlite3_finalize(stmt);
        return -1;
    }

    sqlite3_finalize(stmt);
    return 0;
}

/**
 * Insert process metrics into database
 */
int database_insert_process_metrics(Database* db, const ProcessMetrics* metrics) {
    if (!db || !db->db || !metrics) {
        log_message(LOG_ERROR, "Invalid database or metrics pointer");
        return -1;
    }

    const char* sql = 
        "INSERT INTO process_metrics ("
        "  timestamp, process_id, process_name, cpu_usage_percent,"
        "  memory_mb, disk_io_bytes, network_bytes"
        ") VALUES (?, ?, ?, ?, ?, ?, ?);";

    sqlite3_stmt* stmt = NULL;
    int rc = sqlite3_prepare_v2(db->db, sql, -1, &stmt, NULL);

    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare SQL statement: %s",
                   sqlite3_errmsg(db->db));
        return -1;
    }

    // Bind parameters
    sqlite3_bind_int64(stmt, 1, (sqlite3_int64)metrics->timestamp);
    sqlite3_bind_int(stmt, 2, metrics->process_id);
    sqlite3_bind_text(stmt, 3, metrics->process_name, -1, SQLITE_STATIC);
    sqlite3_bind_double(stmt, 4, metrics->cpu_usage_percent);
    sqlite3_bind_int64(stmt, 5, metrics->memory_mb);
    sqlite3_bind_int64(stmt, 6, metrics->disk_io_bytes);
    sqlite3_bind_int64(stmt, 7, metrics->network_bytes);

    // Execute statement
    rc = sqlite3_step(stmt);
    if (rc != SQLITE_DONE) {
        log_message(LOG_WARN, "Failed to execute insert statement: %s",
                   sqlite3_errmsg(db->db));
        sqlite3_finalize(stmt);
        return -1;
    }

    sqlite3_finalize(stmt);
    return 0;
}

/**
 * Query metrics from a time range
 */
SystemMetrics* database_query_metrics(Database* db,
                                      time_t start_time,
                                      time_t end_time,
                                      int* count) {
    if (!db || !db->db || !count) {
        log_message(LOG_ERROR, "Invalid parameters");
        return NULL;
    }

    // First, count matching records
    const char* count_sql = 
        "SELECT COUNT(*) FROM system_metrics WHERE timestamp >= ? AND timestamp <= ?;";
    
    sqlite3_stmt* stmt = NULL;
    int rc = sqlite3_prepare_v2(db->db, count_sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare count query: %s",
                   sqlite3_errmsg(db->db));
        return NULL;
    }

    sqlite3_bind_int64(stmt, 1, (sqlite3_int64)start_time);
    sqlite3_bind_int64(stmt, 2, (sqlite3_int64)end_time);

    if (sqlite3_step(stmt) != SQLITE_ROW) {
        log_message(LOG_WARN, "Failed to count metrics");
        sqlite3_finalize(stmt);
        return NULL;
    }

    int record_count = sqlite3_column_int(stmt, 0);
    sqlite3_finalize(stmt);

    if (record_count == 0) {
        *count = 0;
        return NULL;
    }

    // Allocate memory for results
    SystemMetrics* metrics = (SystemMetrics*)malloc(record_count * sizeof(SystemMetrics));
    if (!metrics) {
        log_message(LOG_ERROR, "Failed to allocate memory for query results");
        return NULL;
    }

    // Execute query
    const char* query_sql = 
        "SELECT timestamp, cpu_usage_percent, memory_mb, memory_available_mb,"
        "       disk_read_bytes, disk_write_bytes, network_bytes_sent,"
        "       network_bytes_recv, process_count, cpu_temp_celsius "
        "FROM system_metrics WHERE timestamp >= ? AND timestamp <= ? "
        "ORDER BY timestamp ASC;";

    rc = sqlite3_prepare_v2(db->db, query_sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare query: %s",
                   sqlite3_errmsg(db->db));
        free(metrics);
        return NULL;
    }

    sqlite3_bind_int64(stmt, 1, (sqlite3_int64)start_time);
    sqlite3_bind_int64(stmt, 2, (sqlite3_int64)end_time);

    int index = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW && index < record_count) {
        metrics[index].timestamp = (time_t)sqlite3_column_int64(stmt, 0);
        metrics[index].cpu_usage_percent = (float)sqlite3_column_double(stmt, 1);
        metrics[index].memory_mb = (unsigned long)sqlite3_column_int64(stmt, 2);
        metrics[index].memory_available_mb = (unsigned long)sqlite3_column_int64(stmt, 3);
        metrics[index].disk_read_bytes = (unsigned long)sqlite3_column_int64(stmt, 4);
        metrics[index].disk_write_bytes = (unsigned long)sqlite3_column_int64(stmt, 5);
        metrics[index].network_bytes_sent = (unsigned long)sqlite3_column_int64(stmt, 6);
        metrics[index].network_bytes_recv = (unsigned long)sqlite3_column_int64(stmt, 7);
        metrics[index].process_count = sqlite3_column_int(stmt, 8);
        metrics[index].cpu_temp_celsius = (float)sqlite3_column_double(stmt, 9);
        index++;
    }

    sqlite3_finalize(stmt);
    *count = index;
    return metrics;
}

/**
 * Get latest metrics
 */
SystemMetrics* database_get_latest_metrics(Database* db) {
    if (!db || !db->db) {
        log_message(LOG_ERROR, "Invalid database pointer");
        return NULL;
    }

    const char* sql = 
        "SELECT timestamp, cpu_usage_percent, memory_mb, memory_available_mb,"
        "       disk_read_bytes, disk_write_bytes, network_bytes_sent,"
        "       network_bytes_recv, process_count, cpu_temp_celsius "
        "FROM system_metrics ORDER BY timestamp DESC LIMIT 1;";

    sqlite3_stmt* stmt = NULL;
    int rc = sqlite3_prepare_v2(db->db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare query: %s",
                   sqlite3_errmsg(db->db));
        return NULL;
    }

    SystemMetrics* metrics = NULL;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        metrics = (SystemMetrics*)malloc(sizeof(SystemMetrics));
        if (metrics) {
            metrics->timestamp = (time_t)sqlite3_column_int64(stmt, 0);
            metrics->cpu_usage_percent = (float)sqlite3_column_double(stmt, 1);
            metrics->memory_mb = (unsigned long)sqlite3_column_int64(stmt, 2);
            metrics->memory_available_mb = (unsigned long)sqlite3_column_int64(stmt, 3);
            metrics->disk_read_bytes = (unsigned long)sqlite3_column_int64(stmt, 4);
            metrics->disk_write_bytes = (unsigned long)sqlite3_column_int64(stmt, 5);
            metrics->network_bytes_sent = (unsigned long)sqlite3_column_int64(stmt, 6);
            metrics->network_bytes_recv = (unsigned long)sqlite3_column_int64(stmt, 7);
            metrics->process_count = sqlite3_column_int(stmt, 8);
            metrics->cpu_temp_celsius = (float)sqlite3_column_double(stmt, 9);
        }
    }

    sqlite3_finalize(stmt);
    return metrics;
}

/**
 * Cleanup old data (older than days_to_keep)
 */
int database_cleanup_old_data(Database* db, int days_to_keep) {
    if (!db || !db->db) {
        log_message(LOG_ERROR, "Invalid database pointer");
        return -1;
    }

    time_t cutoff_time = time(NULL) - (days_to_keep * 24 * 60 * 60);

    const char* sql = 
        "DELETE FROM system_metrics WHERE timestamp < ?;"
        "DELETE FROM process_metrics WHERE timestamp < ?;";

    sqlite3_stmt* stmt = NULL;

    // Delete from system_metrics
    int rc = sqlite3_prepare_v2(db->db, 
                               "DELETE FROM system_metrics WHERE timestamp < ?;",
                               -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare cleanup query: %s",
                   sqlite3_errmsg(db->db));
        return -1;
    }

    sqlite3_bind_int64(stmt, 1, (sqlite3_int64)cutoff_time);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        log_message(LOG_WARN, "Failed to cleanup system_metrics");
    }

    // Delete from process_metrics
    rc = sqlite3_prepare_v2(db->db,
                           "DELETE FROM process_metrics WHERE timestamp < ?;",
                           -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        log_message(LOG_ERROR, "Failed to prepare process cleanup query: %s",
                   sqlite3_errmsg(db->db));
        return -1;
    }

    sqlite3_bind_int64(stmt, 1, (sqlite3_int64)cutoff_time);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        log_message(LOG_WARN, "Failed to cleanup process_metrics");
    }

    log_message(LOG_INFO, "Cleanup completed (removed data older than %d days)", days_to_keep);
    return 0;
}

/**
 * Close database connection
 */
void database_close(Database* db) {
    if (db && db->db) {
        sqlite3_close(db->db);
        free(db);
        log_message(LOG_DEBUG, "Database closed");
    }
}
