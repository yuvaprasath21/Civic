-- =============================================================
-- Smart Civic Issue Management System — MySQL Schema
-- =============================================================
-- Auto-generated from backend/app/models/*.py via SQLAlchemy
-- metadata (MySQL dialect). This file is a readable reference
-- and a fallback for environments not using Alembic migrations.
-- The source of truth is the SQLAlchemy models; regenerate this
-- file after any model change rather than hand-editing it.
--
-- Regenerate with:
--   cd backend && python -m app.utils.export_schema
-- =============================================================

CREATE DATABASE IF NOT EXISTS civic_issues_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE civic_issues_db;

CREATE TABLE departments (
	name VARCHAR(100) NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	description VARCHAR(500), 
	contact_email VARCHAR(150), 
	contact_phone VARCHAR(20), 
	sla_hours INTEGER NOT NULL, 
	is_active BOOL NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	uuid VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	UNIQUE (code)
);

CREATE TABLE locations (
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	address_text VARCHAR(500), 
	landmark VARCHAR(255), 
	ward VARCHAR(100), 
	city VARCHAR(100), 
	pincode VARCHAR(10), 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE TABLE otp_verifications (
	channel VARCHAR(10) NOT NULL, 
	destination VARCHAR(150) NOT NULL, 
	code_hash VARCHAR(64) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	attempts INTEGER NOT NULL, 
	is_used BOOL NOT NULL, 
	verified_at DATETIME, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE TABLE permissions (
	code VARCHAR(100) NOT NULL, 
	description VARCHAR(255), 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE risk_zones (
	zone_type VARCHAR(50) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	radius_meters FLOAT NOT NULL, 
	risk_weight FLOAT NOT NULL, 
	is_active BOOL NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE TABLE roles (
	name VARCHAR(50) NOT NULL, 
	description VARCHAR(255), 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE users (
	full_name VARCHAR(150) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	phone_number VARCHAR(20), 
	hashed_password VARCHAR(255) NOT NULL, 
	`role` ENUM('CITIZEN','FIELD_STAFF','DEPARTMENT_ADMIN','SUPER_ADMIN') NOT NULL, 
	profile_image_url VARCHAR(500), 
	is_active BOOL NOT NULL, 
	is_email_verified BOOL NOT NULL, 
	is_phone_verified BOOL NOT NULL, 
	last_login_at DATETIME, 
	reset_token VARCHAR(255), 
	reset_token_expires_at DATETIME, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	uuid VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	is_deleted BOOL NOT NULL, 
	deleted_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE audit_logs (
	actor_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id INTEGER, 
	details JSON, 
	ip_address VARCHAR(45), 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE citizen_profiles (
	user_id INTEGER NOT NULL, 
	address_line VARCHAR(255), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	pincode VARCHAR(10), 
	default_latitude FLOAT, 
	default_longitude FLOAT, 
	total_reports_submitted INTEGER NOT NULL, 
	reputation_score INTEGER NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE civic_issues (
	reference_code VARCHAR(20) NOT NULL, 
	reporter_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	department_id INTEGER, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	video_path VARCHAR(500), 
	category ENUM('POTHOLE','GARBAGE','BROKEN_STREETLIGHT','WATER_LEAKAGE','DRAINAGE','WATERLOGGING','FALLEN_TREE','DAMAGED_SIGN','ILLEGAL_DUMPING','CONSTRUCTION_OBSTRUCTION','OTHER') NOT NULL, 
	severity ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL, 
	status ENUM('REPORTED','AI_ANALYZED','VERIFIED','ASSIGNED','ACCEPTED','IN_PROGRESS','RESOLVED','REJECTED','REOPENED','CLOSED','POTENTIAL_DUPLICATE') NOT NULL, 
	priority_score FLOAT NOT NULL, 
	priority_level ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL, 
	is_ai_verified BOOL NOT NULL, 
	is_citizen_edited_category BOOL NOT NULL, 
	master_issue_id INTEGER, 
	duplicate_count INTEGER NOT NULL, 
	resolved_at DATETIME, 
	sla_due_at DATETIME, 
	is_sla_breached BOOL NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	uuid VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	is_deleted BOOL NOT NULL, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reporter_id) REFERENCES users (id) ON DELETE RESTRICT, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE RESTRICT, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL, 
	FOREIGN KEY(master_issue_id) REFERENCES civic_issues (id) ON DELETE SET NULL
);

CREATE TABLE issue_categories (
	category VARCHAR(50) NOT NULL, 
	display_name VARCHAR(100) NOT NULL, 
	department_id INTEGER NOT NULL, 
	default_severity VARCHAR(20) NOT NULL, 
	is_active BOOL NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (category), 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT
);

CREATE TABLE role_permissions (
	role_id INTEGER NOT NULL, 
	permission_id INTEGER NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE staff_profiles (
	user_id INTEGER NOT NULL, 
	department_id INTEGER, 
	employee_code VARCHAR(30) NOT NULL, 
	designation VARCHAR(100), 
	is_available BOOL NOT NULL, 
	current_workload INTEGER NOT NULL, 
	total_resolved_count INTEGER NOT NULL, 
	average_resolution_hours FLOAT, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL, 
	UNIQUE (employee_code)
);

CREATE TABLE user_roles (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE issue_assignments (
	issue_id INTEGER NOT NULL, 
	staff_id INTEGER NOT NULL, 
	assigned_by_id INTEGER NOT NULL, 
	department_id INTEGER, 
	status ENUM('PENDING','ACCEPTED','IN_PROGRESS','COMPLETED','REASSIGNED') NOT NULL, 
	accepted_at DATETIME, 
	started_at DATETIME, 
	completed_at DATETIME, 
	staff_notes TEXT, 
	progress_percent INTEGER NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(staff_id) REFERENCES users (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assigned_by_id) REFERENCES users (id) ON DELETE RESTRICT, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL
);

CREATE TABLE issue_comments (
	issue_id INTEGER NOT NULL, 
	author_id INTEGER NOT NULL, 
	body TEXT NOT NULL, 
	is_internal BOOL NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE issue_duplicates (
	master_issue_id INTEGER NOT NULL, 
	duplicate_issue_id INTEGER NOT NULL, 
	distance_meters FLOAT, 
	time_delta_hours FLOAT, 
	image_similarity_score FLOAT, 
	matched_automatically BOOL NOT NULL, 
	merged_by_id INTEGER, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(master_issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	UNIQUE (duplicate_issue_id), 
	FOREIGN KEY(duplicate_issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(merged_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE issue_feedback (
	issue_id INTEGER NOT NULL, 
	citizen_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	comment TEXT, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (issue_id), 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(citizen_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE issue_images (
	issue_id INTEGER NOT NULL, 
	uploaded_by_id INTEGER NOT NULL, 
	image_type ENUM('REPORT','BEFORE_WORK','AFTER_WORK','PROFILE') NOT NULL, 
	file_path VARCHAR(500) NOT NULL, 
	original_filename VARCHAR(255), 
	content_type VARCHAR(100) NOT NULL, 
	file_size_bytes INTEGER NOT NULL, 
	width INTEGER, 
	height INTEGER, 
	perceptual_hash VARCHAR(16), 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploaded_by_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE issue_status_history (
	issue_id INTEGER NOT NULL, 
	changed_by_id INTEGER, 
	from_status ENUM('REPORTED','AI_ANALYZED','VERIFIED','ASSIGNED','ACCEPTED','IN_PROGRESS','RESOLVED','REJECTED','REOPENED','CLOSED','POTENTIAL_DUPLICATE'), 
	to_status ENUM('REPORTED','AI_ANALYZED','VERIFIED','ASSIGNED','ACCEPTED','IN_PROGRESS','RESOLVED','REJECTED','REOPENED','CLOSED','POTENTIAL_DUPLICATE') NOT NULL, 
	note TEXT, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(changed_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE notifications (
	recipient_id INTEGER NOT NULL, 
	issue_id INTEGER, 
	type ENUM('ISSUE_SUBMITTED','AI_ANALYSIS_COMPLETE','ISSUE_VERIFIED','ISSUE_ASSIGNED','ASSIGNMENT_CHANGED','PRIORITY_INCREASED','WORK_STARTED','ISSUE_RESOLVED','ISSUE_REJECTED','ISSUE_REOPENED','CRITICAL_ISSUE_REPORTED','SLA_EXCEEDED','DUPLICATE_DETECTED') NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	metadata_json JSON, 
	is_read BOOL NOT NULL, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(recipient_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE
);

CREATE TABLE ai_predictions (
	issue_id INTEGER NOT NULL, 
	issue_image_id INTEGER, 
	predicted_category ENUM('POTHOLE','GARBAGE','BROKEN_STREETLIGHT','WATER_LEAKAGE','DRAINAGE','WATERLOGGING','FALLEN_TREE','DAMAGED_SIGN','ILLEGAL_DUMPING','CONSTRUCTION_OBSTRUCTION','OTHER') NOT NULL, 
	confidence FLOAT NOT NULL, 
	predicted_severity ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL, 
	detected_objects JSON NOT NULL, 
	model_version VARCHAR(50) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	raw_output JSON, 
	inference_time_ms FLOAT, 
	id INTEGER NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT now(), 
	updated_at DATETIME NOT NULL DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES civic_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(issue_image_id) REFERENCES issue_images (id) ON DELETE SET NULL
);
