PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS projects_history;
DROP TABLE IF EXISTS departments_history;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
  id            INTEGER PRIMARY KEY,
  name          TEXT    NOT NULL,
  description   TEXT    NOT NULL DEFAULT '',
  founded_date  TEXT    NOT NULL,
  headcount     INTEGER NOT NULL CHECK (headcount >= 0),
  annual_budget NUMERIC(12,2) NOT NULL CHECK (annual_budget >= 0),
  is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE projects (
  id               INTEGER PRIMARY KEY,
  department_id    INTEGER NOT NULL,
  title            TEXT    NOT NULL,
  summary          TEXT    NOT NULL DEFAULT '',
  start_date       TEXT    NOT NULL,
  planned_end_date TEXT    NOT NULL,
  priority         INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
  project_budget   NUMERIC(12,2) NOT NULL CHECK (project_budget >= 0),
  is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),

  CONSTRAINT fk_projects_departments
    FOREIGN KEY (department_id)
    REFERENCES departments(id)
    ON UPDATE RESTRICT
    ON DELETE RESTRICT
);

CREATE TABLE departments_history (
  history_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id     INTEGER NOT NULL,
  operation     TEXT    NOT NULL,
  changed_at    TEXT    NOT NULL,
  name          TEXT    NOT NULL,
  description   TEXT    NOT NULL,
  founded_date  TEXT    NOT NULL,
  headcount     INTEGER NOT NULL,
  annual_budget NUMERIC(12,2) NOT NULL,
  is_active     INTEGER NOT NULL
);

CREATE TABLE projects_history (
  history_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id        INTEGER NOT NULL,
  operation        TEXT    NOT NULL,
  changed_at       TEXT    NOT NULL,
  department_id    INTEGER NOT NULL,
  title            TEXT    NOT NULL,
  summary          TEXT    NOT NULL,
  start_date       TEXT    NOT NULL,
  planned_end_date TEXT    NOT NULL,
  priority         INTEGER NOT NULL,
  project_budget   NUMERIC(12,2) NOT NULL,
  is_active        INTEGER NOT NULL
);
