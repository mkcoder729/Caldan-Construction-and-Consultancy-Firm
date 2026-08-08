-- =====================================================================
-- CLEAR PROJECTS DATA
-- Safe variant: uses DELETE instead of TRUNCATE.
-- Works even if FOREIGN_KEY_CHECKS=0 is blocked or triggers exist.
-- Does NOT reset auto_increment — use ALTER TABLE...AUTO_INCREMENT=1 after.
-- Does NOT touch django_migrations or other apps.
-- =====================================================================

DELETE FROM project_service_links;
DELETE FROM project_gallery;
DELETE FROM project_milestones;
DELETE FROM projects;
