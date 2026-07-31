# Supabase adapter

1. Apply all files in `migrations/` in order.
2. Apply `supabase/001_auth_adapter.sql`.
3. Create backend service secrets outside the database.
4. Use Supabase project backups/PITR as appropriate for the selected plan.
5. Keep private object-storage buckets for signed agreements, exports, and private guest-guide files.

The adapter replaces `app.current_user_id()` with `auth.uid()` and mirrors Supabase Auth users into `app.users`. The portable schema itself does not depend on Supabase.
