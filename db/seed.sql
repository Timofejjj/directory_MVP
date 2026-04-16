PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Departments (Отделы)
INSERT INTO departments (id, name, description, founded_date, headcount, annual_budget) VALUES
  (10, 'QA', 'Тестирование продуктов компании (in-house).', '2020-02-15', 8, 250000.00),
  (20, 'QA', 'Тестирование (аутсорс-направление).', '2021-06-01', 5, 180000.00),
  (30, 'Backend', 'Разработка серверной части и API.', '2019-09-01', 12, 600000.50);

-- Projects (Проекты)
INSERT INTO projects (id, department_id, title, summary, start_date, planned_end_date, priority, project_budget) VALUES
  (100, 30, 'Billing API', 'Новый сервис выставления счетов и интеграции с платежными системами.', '2026-03-01', '2026-06-30', 5, 120000.00),
  (110, 10, 'Regression Pack', 'Набор регрессионных автотестов для ключевых сценариев.', '2026-03-10', '2026-05-15', 4, 25000.00),
  (120, 20, 'Mobile QA Support', 'Поддержка тестирования мобильного приложения в релизный период.', '2026-04-01', '2026-04-30', 3, 15000.75);

COMMIT;
