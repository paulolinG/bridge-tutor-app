-- The previous migration (20260908000001) dropped student_profiles' primary
-- key constraint and re-added it, intending to also remove the `auth.users`
-- foreign key per docs/adr/0001-student-profiles-not-auth-users.md. It never
-- actually did — a PRIMARY KEY and a FOREIGN KEY are separate constraints,
-- and Postgres's default-named `student_profiles_id_fkey` survived,
-- silently blocking every student insert that isn't also an auth.users row.
alter table student_profiles drop constraint if exists student_profiles_id_fkey;
