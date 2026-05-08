-- Compatibility patch for restoring an older prod dump into the current codebase.
-- Apply after pg_restore, before running the app against the restored DB.

UPDATE django_migrations
SET name = '0001_initial_state_import'
WHERE app = 'user' AND name = '0001_initial';

INSERT INTO django_migrations (app, name, applied)
SELECT 'core_references', '0001_initial_state_import', NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM django_migrations
    WHERE app = 'core_references' AND name = '0001_initial_state_import'
);

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS max_id varchar(50);

ALTER TABLE display DROP CONSTRAINT IF EXISTS display_city_id_21080318_fk_city_name;
ALTER TABLE panel DROP CONSTRAINT IF EXISTS panel_application_status_id_d5e89b0b_fk_application_status_name;
ALTER TABLE panel DROP CONSTRAINT IF EXISTS panel_condition_id_12b1a585_fk_condition_name;
ALTER TABLE panel DROP CONSTRAINT IF EXISTS panel_department_id_d47663ed_fk_department_name;
ALTER TABLE panel DROP CONSTRAINT IF EXISTS panel_display_id_36368d17_fk_display_name;
ALTER TABLE cell DROP CONSTRAINT IF EXISTS cell_display_id_3314090f_fk_display_name;
ALTER TABLE cell DROP CONSTRAINT IF EXISTS cell_panel_id_676cbe77_fk_panel_name;
ALTER TABLE application DROP CONSTRAINT IF EXISTS application_status_id_f8c35cc7_fk_application_status_name;
ALTER TABLE condition DROP CONSTRAINT IF EXISTS condition_color_id_d2e6aafe_fk_color_name;
ALTER TABLE condition DROP CONSTRAINT IF EXISTS condition_color_text_id_ceddec82_fk_color_name;
ALTER TABLE condition DROP CONSTRAINT IF EXISTS condition_icon_id_0ccb5dbc_fk_smile_smile_icon;
ALTER TABLE department DROP CONSTRAINT IF EXISTS department_color_id_80e3d735_fk_color_name;
ALTER TABLE department DROP CONSTRAINT IF EXISTS department_color_text_id_75151f2f_fk_color_name;
ALTER TABLE department DROP CONSTRAINT IF EXISTS department_icon_id_b3e59d6a_fk_smile_smile_icon;
ALTER TABLE application_status DROP CONSTRAINT IF EXISTS application_status_color_id_2e9e710f_fk_color_name;
ALTER TABLE application_status DROP CONSTRAINT IF EXISTS application_status_color_text_id_b91c9ea2_fk_color_name;
ALTER TABLE application_status DROP CONSTRAINT IF EXISTS application_status_icon_id_9228f9b8_fk_smile_smile_icon;

DROP INDEX IF EXISTS display_city_id_21080318;
DROP INDEX IF EXISTS display_city_id_21080318_like;
DROP INDEX IF EXISTS panel_application_status_id_d5e89b0b;
DROP INDEX IF EXISTS panel_application_status_id_d5e89b0b_like;
DROP INDEX IF EXISTS panel_condition_id_12b1a585;
DROP INDEX IF EXISTS panel_condition_id_12b1a585_like;
DROP INDEX IF EXISTS panel_department_id_d47663ed;
DROP INDEX IF EXISTS panel_department_id_d47663ed_like;
DROP INDEX IF EXISTS panel_display_id_36368d17;
DROP INDEX IF EXISTS panel_display_id_36368d17_like;
DROP INDEX IF EXISTS cell_display_id_3314090f;
DROP INDEX IF EXISTS cell_display_id_3314090f_like;
DROP INDEX IF EXISTS cell_panel_id_676cbe77;
DROP INDEX IF EXISTS cell_panel_id_676cbe77_like;
DROP INDEX IF EXISTS application_status_id_f8c35cc7;
DROP INDEX IF EXISTS application_status_id_f8c35cc7_like;
DROP INDEX IF EXISTS condition_color_id_d2e6aafe;
DROP INDEX IF EXISTS condition_color_id_d2e6aafe_like;
DROP INDEX IF EXISTS condition_color_text_id_ceddec82;
DROP INDEX IF EXISTS condition_color_text_id_ceddec82_like;
DROP INDEX IF EXISTS condition_icon_id_0ccb5dbc;
DROP INDEX IF EXISTS condition_icon_id_0ccb5dbc_like;
DROP INDEX IF EXISTS department_color_id_80e3d735;
DROP INDEX IF EXISTS department_color_id_80e3d735_like;
DROP INDEX IF EXISTS department_color_text_id_75151f2f;
DROP INDEX IF EXISTS department_color_text_id_75151f2f_like;
DROP INDEX IF EXISTS department_icon_id_b3e59d6a;
DROP INDEX IF EXISTS department_icon_id_b3e59d6a_like;
DROP INDEX IF EXISTS application_status_color_id_2e9e710f;
DROP INDEX IF EXISTS application_status_color_id_2e9e710f_like;
DROP INDEX IF EXISTS application_status_color_text_id_b91c9ea2;
DROP INDEX IF EXISTS application_status_color_text_id_b91c9ea2_like;
DROP INDEX IF EXISTS application_status_icon_id_9228f9b8;
DROP INDEX IF EXISTS application_status_icon_id_9228f9b8_like;

UPDATE display d SET city_id = c.id::text FROM city c WHERE d.city_id = c.name;
ALTER TABLE display ALTER COLUMN city_id TYPE bigint USING city_id::bigint;

UPDATE panel p SET display_id = d.id::text FROM display d WHERE p.display_id = d.name;
ALTER TABLE panel ALTER COLUMN display_id TYPE bigint USING display_id::bigint;

UPDATE cell c1 SET display_id = d.id::text FROM display d WHERE c1.display_id = d.name;
ALTER TABLE cell ALTER COLUMN display_id TYPE bigint USING display_id::bigint;

UPDATE cell c1 SET panel_id = p.id::text FROM panel p WHERE c1.panel_id = p.name;
ALTER TABLE cell ALTER COLUMN panel_id TYPE bigint USING panel_id::bigint;

UPDATE panel p SET condition_id = c.id::text FROM condition c WHERE p.condition_id = c.name;
ALTER TABLE panel ALTER COLUMN condition_id TYPE bigint USING condition_id::bigint;

UPDATE panel p SET department_id = d.id::text FROM department d WHERE p.department_id = d.name;
ALTER TABLE panel ALTER COLUMN department_id TYPE bigint USING department_id::bigint;

UPDATE application a SET status_id = s.id::text FROM application_status s WHERE a.status_id = s.name;
ALTER TABLE application ALTER COLUMN status_id TYPE bigint USING status_id::bigint;

UPDATE panel p SET application_status_id = s.id::text FROM application_status s WHERE p.application_status_id = s.name;
ALTER TABLE panel ALTER COLUMN application_status_id TYPE bigint USING application_status_id::bigint;

UPDATE condition c SET color_id = clr.id::text FROM color clr WHERE c.color_id = clr.name;
ALTER TABLE condition ALTER COLUMN color_id TYPE bigint USING color_id::bigint;

UPDATE condition c SET color_text_id = clr.id::text FROM color clr WHERE c.color_text_id = clr.name;
ALTER TABLE condition ALTER COLUMN color_text_id TYPE bigint USING color_text_id::bigint;

UPDATE condition c SET icon_id = s.id::text FROM smile s WHERE c.icon_id = s.smile_icon;
ALTER TABLE condition ALTER COLUMN icon_id TYPE bigint USING icon_id::bigint;

UPDATE department dpt SET color_id = clr.id::text FROM color clr WHERE dpt.color_id = clr.name;
ALTER TABLE department ALTER COLUMN color_id TYPE bigint USING color_id::bigint;

UPDATE department dpt SET color_text_id = clr.id::text FROM color clr WHERE dpt.color_text_id = clr.name;
ALTER TABLE department ALTER COLUMN color_text_id TYPE bigint USING color_text_id::bigint;

UPDATE department dpt SET icon_id = s.id::text FROM smile s WHERE dpt.icon_id = s.smile_icon;
ALTER TABLE department ALTER COLUMN icon_id TYPE bigint USING icon_id::bigint;

UPDATE application_status ast SET color_id = clr.id::text FROM color clr WHERE ast.color_id = clr.name;
ALTER TABLE application_status ALTER COLUMN color_id TYPE bigint USING color_id::bigint;

UPDATE application_status ast SET color_text_id = clr.id::text FROM color clr WHERE ast.color_text_id = clr.name;
ALTER TABLE application_status ALTER COLUMN color_text_id TYPE bigint USING color_text_id::bigint;

UPDATE application_status ast SET icon_id = s.id::text FROM smile s WHERE ast.icon_id = s.smile_icon;
ALTER TABLE application_status ALTER COLUMN icon_id TYPE bigint USING icon_id::bigint;
