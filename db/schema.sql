PRAGMA foreign_keys = ON;

-- Справочник 1 (главный): Отделы IT-компании (Departments)
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
  id            INTEGER PRIMARY KEY,          -- задаём id вручную (не полагаемся на авто-генерацию)
  name          TEXT    NOT NULL,             -- название отдела (допускаем одинаковые названия у разных id)
  description   TEXT    NOT NULL DEFAULT '',  -- многострочное описание
  founded_date  TEXT    NOT NULL,             -- дата в формате ISO: YYYY-MM-DD
  headcount     INTEGER NOT NULL CHECK (headcount >= 0),
  annual_budget NUMERIC(12,2) NOT NULL CHECK (annual_budget >= 0)
);

-- Справочник 2 (зависимый): Проекты (Projects)
CREATE TABLE projects (
  id               INTEGER PRIMARY KEY,          -- задаём id вручную
  department_id    INTEGER NOT NULL,
  title            TEXT    NOT NULL,
  summary          TEXT    NOT NULL DEFAULT '',
  start_date       TEXT    NOT NULL,             -- YYYY-MM-DD
  planned_end_date TEXT    NOT NULL,             -- YYYY-MM-DD
  priority         INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
  project_budget   NUMERIC(12,2) NOT NULL CHECK (project_budget >= 0),

  CONSTRAINT fk_projects_departments
    FOREIGN KEY (department_id)
    REFERENCES departments(id)
    ON UPDATE RESTRICT
    ON DELETE RESTRICT
);
