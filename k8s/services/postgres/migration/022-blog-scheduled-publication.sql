\connect social
-- 022 — support explicit, approved blog scheduling without altering existing posts.
ALTER TABLE blog_posts ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_blog_posts_scheduled_publication
  ON blog_posts (scheduled_at)
  WHERE status = 'scheduled' AND scheduled_at IS NOT NULL;
