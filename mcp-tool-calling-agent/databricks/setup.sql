-- ============================================================
-- databricks/setup.sql
-- Setup script for ACME Technologies Unity Catalog tables
--
-- Run this once in your Databricks workspace to create the
-- tables needed for the MCP agent.
--
-- Replace:
--   your_catalog  → your Unity Catalog catalog name
--   acme_company  → your schema name (matches DATABRICKS_SCHEMA)
-- ============================================================

-- Create schema
CREATE SCHEMA IF NOT EXISTS your_catalog.acme_company
  COMMENT 'ACME Technologies company data for MCP agent demo';

-- ============================================================
-- EMPLOYEES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS your_catalog.acme_company.employees (
  employee_id   STRING  NOT NULL,
  name          STRING  NOT NULL,
  department    STRING  NOT NULL,
  role          STRING  NOT NULL,
  project_id    STRING,
  access_level  STRING  NOT NULL  -- employee, manager, admin
)
USING DELTA
COMMENT 'ACME Technologies employee directory'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- ============================================================
-- DEPARTMENTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS your_catalog.acme_company.departments (
  department_id    STRING  NOT NULL,
  department_name  STRING  NOT NULL,
  manager          STRING  NOT NULL,
  description      STRING
)
USING DELTA
COMMENT 'ACME Technologies department directory';

-- ============================================================
-- PROJECTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS your_catalog.acme_company.projects (
  project_id    STRING   NOT NULL,
  project_name  STRING   NOT NULL,
  department    STRING   NOT NULL,
  status        STRING   NOT NULL,  -- Active, Completed, In Progress
  description   STRING,
  team_size     INTEGER
)
USING DELTA
COMMENT 'ACME Technologies project registry';

-- ============================================================
-- LOAD SAMPLE DATA (employees)
-- ============================================================
INSERT INTO your_catalog.acme_company.employees VALUES
  ('E001', 'Alice Johnson',   'AI',          'Senior ML Engineer',    'P001', 'employee'),
  ('E002', 'Bob Martinez',    'AI',          'ML Engineer',           'P001', 'employee'),
  ('E003', 'Carol White',     'AI',          'Data Scientist',        'P002', 'employee'),
  ('E004', 'David Kim',       'Engineering', 'Backend Engineer',      'P003', 'employee'),
  ('E005', 'Eva Chen',        'Engineering', 'Frontend Engineer',     'P003', 'employee'),
  ('E006', 'Frank Patel',     'Engineering', 'DevOps Engineer',       'P004', 'employee'),
  ('E007', 'Grace Lee',       'Security',    'Security Analyst',      'P005', 'employee'),
  ('E008', 'Henry Brown',     'Security',    'Penetration Tester',    'P005', 'employee'),
  ('E009', 'Iris Thompson',   'HR',          'HR Manager',            'P006', 'manager'),
  ('E010', 'James Wilson',    'HR',          'HR Specialist',         'P006', 'employee'),
  ('E011', 'Karen Davis',     'AI',          'AI Research Lead',      'P002', 'manager'),
  ('E012', 'Leo Nguyen',      'Engineering', 'Engineering Manager',   'P003', 'manager'),
  ('E013', 'Mia Robinson',    'Security',    'Security Manager',      'P005', 'manager'),
  ('E014', 'Noah Clark',      'Finance',     'Financial Analyst',     'P007', 'employee'),
  ('E015', 'Olivia Scott',    'Finance',     'Finance Manager',       'P007', 'manager');

-- ============================================================
-- LOAD SAMPLE DATA (departments)
-- ============================================================
INSERT INTO your_catalog.acme_company.departments VALUES
  ('D001', 'AI',          'Karen Davis',   'Responsible for AI/ML solutions.'),
  ('D002', 'Engineering', 'Leo Nguyen',    'Software development and DevOps.'),
  ('D003', 'Security',    'Mia Robinson',  'Cybersecurity and compliance.'),
  ('D004', 'HR',          'Iris Thompson', 'People and culture.'),
  ('D005', 'Finance',     'Olivia Scott',  'Financial planning and analysis.');

-- ============================================================
-- LOAD SAMPLE DATA (projects)
-- ============================================================
INSERT INTO your_catalog.acme_company.projects VALUES
  ('P001', 'SmartAssist AI Platform',     'AI',          'Active',      'Internal AI-powered assistant using LLMs and RAG.',            5),
  ('P002', 'Predictive Analytics Engine', 'AI',          'Active',      'ML pipeline to predict customer churn.',                       3),
  ('P003', 'Unified API Gateway',         'Engineering', 'Active',      'Centralised API gateway for all services.',                    6),
  ('P004', 'Cloud Infrastructure Migration','Engineering','Completed',  'Migrated on-premise infra to cloud.',                          4),
  ('P005', 'Zero Trust Security Program', 'Security',    'Active',      'Zero-trust architecture across all systems.',                  3),
  ('P006', 'Employee Wellness Initiative','HR',          'Active',      'Comprehensive employee wellness program.',                     2),
  ('P007', 'Annual Budget Automation',    'Finance',     'In Progress', 'Automating annual budget planning and forecasting.',           2);

-- ============================================================
-- UNITY CATALOG ROW-LEVEL SECURITY (example)
-- Grant read access to all employees for non-sensitive tables
-- ============================================================
-- GRANT SELECT ON TABLE your_catalog.acme_company.departments TO `employees-group`;
-- GRANT SELECT ON TABLE your_catalog.acme_company.projects    TO `employees-group`;
-- GRANT SELECT ON TABLE your_catalog.acme_company.employees   TO `managers-group`;
-- GRANT ALL    ON TABLE your_catalog.acme_company.employees   TO `admin-group`;

-- ============================================================
-- NOTE ON UNITY CATALOG PERMISSIONS vs APPLICATION PERMISSIONS
-- ============================================================
-- The application-level role checks (employee/manager/admin in
-- mcp_server/permissions.py) enforce which fields the agent
-- SHOWS the user. They are a useful UX safeguard but are NOT
-- a substitute for proper Unity Catalog grants, which enforce
-- permissions at the data platform level regardless of the
-- application making the query.
-- Always configure both layers for real production use.
-- ============================================================
