-- Smart Traffic Control System Database Schema
-- Supports both MySQL and SQLite with appropriate syntax

-- Intersection configuration
CREATE TABLE IF NOT EXISTS intersections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    num_lanes INTEGER DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Camera configuration per lane
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER,
    lane_direction VARCHAR(10) NOT NULL CHECK(lane_direction IN ('N','S','E','W')),
    camera_url VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active','inactive','error')),
    FOREIGN KEY (intersection_id) REFERENCES intersections(id)
);

-- Current signal state
CREATE TABLE IF NOT EXISTS traffic_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER,
    lane_direction VARCHAR(10) NOT NULL CHECK(lane_direction IN ('N','S','E','W')),
    current_phase VARCHAR(20) NOT NULL CHECK(current_phase IN ('red','yellow','green')),
    phase_duration INTEGER NOT NULL,
    remaining_time INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intersection_id) REFERENCES intersections(id)
);

-- Historical traffic data (logged every cycle)
CREATE TABLE IF NOT EXISTS traffic_data_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER,
    lane_direction VARCHAR(10) NOT NULL CHECK(lane_direction IN ('N','S','E','W')),
    vehicle_count INTEGER NOT NULL,
    car_count INTEGER DEFAULT 0,
    truck_count INTEGER DEFAULT 0,
    bus_count INTEGER DEFAULT 0,
    motorcycle_count INTEGER DEFAULT 0,
    density_score REAL,
    avg_speed REAL,
    queue_length INTEGER,
    waiting_time REAL,
    green_time_allocated INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intersection_id) REFERENCES intersections(id)
);

-- Emergency events
CREATE TABLE IF NOT EXISTS emergency_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intersection_id INTEGER,
    lane_direction VARCHAR(10) NOT NULL CHECK(lane_direction IN ('N','S','E','W')),
    vehicle_type VARCHAR(50),
    action_taken VARCHAR(100),
    response_time_ms INTEGER,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (intersection_id) REFERENCES intersections(id)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_traffic_logs_timestamp ON traffic_data_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_traffic_logs_lane ON traffic_data_logs(lane_direction);
CREATE INDEX IF NOT EXISTS idx_emergency_events_timestamp ON emergency_events(detected_at);
CREATE INDEX IF NOT EXISTS idx_signals_intersection ON traffic_signals(intersection_id, lane_direction);
