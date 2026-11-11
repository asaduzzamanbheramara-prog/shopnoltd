-- Idempotent model-backed schema provisioning for the exchange and social services.
-- The migration hook runs before application deployments. It must be safe to
-- execute repeatedly and must never drop or rewrite existing application rows.

\\connect payments

BEGIN;

CREATE TABLE IF NOT EXISTS public.rates (
    id VARCHAR(64) PRIMARY KEY,
    base VARCHAR(8) NOT NULL,
    quote VARCHAR(8) NOT NULL,
    rate NUMERIC(28,12) NOT NULL,
    source VARCHAR(32) NOT NULL,
    fetched_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_rates_base ON public.rates (base);
CREATE INDEX IF NOT EXISTS ix_rates_quote ON public.rates (quote);
CREATE INDEX IF NOT EXISTS ix_rates_fetched_at ON public.rates (fetched_at);
CREATE INDEX IF NOT EXISTS ix_rate_pair_time ON public.rates (base, quote, fetched_at);

CREATE TABLE IF NOT EXISTS public.conversions (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    from_currency VARCHAR(8) NOT NULL,
    to_currency VARCHAR(8) NOT NULL,
    from_amount NUMERIC(20,8) NOT NULL,
    to_amount NUMERIC(20,8) NOT NULL,
    rate NUMERIC(28,12) NOT NULL,
    fee NUMERIC(20,8) DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_conversions_tenant_id ON public.conversions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_conversions_user_id ON public.conversions (user_id);
CREATE INDEX IF NOT EXISTS ix_conversions_created_at ON public.conversions (created_at);

GRANT USAGE, CREATE ON SCHEMA public TO shopno;
GRANT SELECT, INSERT, UPDATE ON TABLE public.rates TO shopno;
GRANT SELECT, INSERT ON TABLE public.conversions TO shopno;

COMMIT;

\\connect social

BEGIN;

CREATE TABLE IF NOT EXISTS public.posts (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    media JSONB NOT NULL DEFAULT '[]'::jsonb,
    visibility VARCHAR(16) DEFAULT 'public',
    scheduled_at TIMESTAMP WITHOUT TIME ZONE,
    published_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    like_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_posts_tenant_id ON public.posts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_posts_user_id ON public.posts (user_id);
CREATE INDEX IF NOT EXISTS ix_posts_published_at ON public.posts (published_at);
CREATE INDEX IF NOT EXISTS ix_posts_created_at ON public.posts (created_at);

-- If an older social-service image created media as VARCHAR, convert only
-- valid JSON text. Invalid legacy values fail closed instead of being dropped.
DO $$
DECLARE
    media_type TEXT;
BEGIN
    SELECT data_type INTO media_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'posts' AND column_name = 'media';

    IF media_type IS NOT NULL AND media_type <> 'jsonb' THEN
        EXECUTE 'ALTER TABLE public.posts ALTER COLUMN media TYPE JSONB USING COALESCE(NULLIF(media::text, ''''), ''[]'')::jsonb';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.blog_posts (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    author_id VARCHAR(64) NOT NULL,
    title VARCHAR(300) NOT NULL,
    slug VARCHAR(320) NOT NULL,
    excerpt TEXT,
    content TEXT NOT NULL,
    cover_image VARCHAR(1024),
    status VARCHAR(16) NOT NULL DEFAULT 'draft',
    published_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_blog_posts_tenant_id ON public.blog_posts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_blog_posts_author_id ON public.blog_posts (author_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_blog_posts_slug ON public.blog_posts (slug);
CREATE INDEX IF NOT EXISTS ix_blog_posts_status ON public.blog_posts (status);
CREATE INDEX IF NOT EXISTS ix_blog_posts_published_at ON public.blog_posts (published_at);

CREATE TABLE IF NOT EXISTS public.blog_likes (
    id VARCHAR(64) PRIMARY KEY,
    blog_post_id VARCHAR(64) NOT NULL REFERENCES public.blog_posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_blog_likes_blog_post_id ON public.blog_likes (blog_post_id);
CREATE INDEX IF NOT EXISTS ix_blog_likes_user_id ON public.blog_likes (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_blog_like_post_user ON public.blog_likes (blog_post_id, user_id);

CREATE TABLE IF NOT EXISTS public.blog_comments (
    id VARCHAR(64) PRIMARY KEY,
    blog_post_id VARCHAR(64) NOT NULL REFERENCES public.blog_posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_blog_comments_blog_post_id ON public.blog_comments (blog_post_id);
CREATE INDEX IF NOT EXISTS ix_blog_comments_user_id ON public.blog_comments (user_id);
CREATE INDEX IF NOT EXISTS ix_blog_comments_created_at ON public.blog_comments (created_at);

CREATE TABLE IF NOT EXISTS public.blog_shares (
    id VARCHAR(64) PRIMARY KEY,
    blog_post_id VARCHAR(64) NOT NULL REFERENCES public.blog_posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    target VARCHAR(16) NOT NULL DEFAULT 'copy',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_blog_shares_blog_post_id ON public.blog_shares (blog_post_id);
CREATE INDEX IF NOT EXISTS ix_blog_shares_user_id ON public.blog_shares (user_id);

CREATE TABLE IF NOT EXISTS public.blog_saved_posts (
    id VARCHAR(64) PRIMARY KEY,
    blog_post_id VARCHAR(64) NOT NULL REFERENCES public.blog_posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_blog_saved_posts_blog_post_id ON public.blog_saved_posts (blog_post_id);
CREATE INDEX IF NOT EXISTS ix_blog_saved_posts_user_id ON public.blog_saved_posts (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_blog_saved_user_post ON public.blog_saved_posts (user_id, blog_post_id);

CREATE TABLE IF NOT EXISTS public.likes (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_likes_post_id ON public.likes (post_id);
CREATE INDEX IF NOT EXISTS ix_likes_user_id ON public.likes (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_like_post_user ON public.likes (post_id, user_id);

CREATE TABLE IF NOT EXISTS public.saved_posts (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_saved_posts_post_id ON public.saved_posts (post_id);
CREATE INDEX IF NOT EXISTS ix_saved_posts_user_id ON public.saved_posts (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_saved_post_user_post ON public.saved_posts (user_id, post_id);

CREATE TABLE IF NOT EXISTS public.reactions (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    reaction VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_reactions_post_id ON public.reactions (post_id);
CREATE INDEX IF NOT EXISTS ix_reactions_user_id ON public.reactions (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_reaction_post_user_type ON public.reactions (post_id, user_id, reaction);

CREATE TABLE IF NOT EXISTS public.shares (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    target VARCHAR(16) DEFAULT 'internal',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_shares_post_id ON public.shares (post_id);
CREATE INDEX IF NOT EXISTS ix_shares_user_id ON public.shares (user_id);

CREATE TABLE IF NOT EXISTS public.follows (
    id VARCHAR(64) PRIMARY KEY,
    follower_id VARCHAR(64) NOT NULL,
    followee_id VARCHAR(64) NOT NULL,
    status VARCHAR(16) DEFAULT 'accepted',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_follows_follower_id ON public.follows (follower_id);
CREATE INDEX IF NOT EXISTS ix_follows_followee_id ON public.follows (followee_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_follow_pair ON public.follows (follower_id, followee_id);

CREATE TABLE IF NOT EXISTS public.comments (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    parent_id VARCHAR(64) REFERENCES public.comments(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_comments_post_id ON public.comments (post_id);
CREATE INDEX IF NOT EXISTS ix_comments_user_id ON public.comments (user_id);
CREATE INDEX IF NOT EXISTS ix_comments_parent_id ON public.comments (parent_id);
CREATE INDEX IF NOT EXISTS ix_comments_created_at ON public.comments (created_at);

CREATE TABLE IF NOT EXISTS public.blog_admin_audit (
    id VARCHAR(64) PRIMARY KEY,
    actor_id VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    operation VARCHAR(32) NOT NULL,
    before_json TEXT,
    after_json TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_blog_admin_audit_actor_id ON public.blog_admin_audit (actor_id);
CREATE INDEX IF NOT EXISTS ix_blog_admin_audit_tenant_id ON public.blog_admin_audit (tenant_id);
CREATE INDEX IF NOT EXISTS ix_blog_admin_audit_action ON public.blog_admin_audit (action);
CREATE INDEX IF NOT EXISTS ix_blog_admin_audit_created_at ON public.blog_admin_audit (created_at);

CREATE TABLE IF NOT EXISTS public.post_views (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_post_views_post_id ON public.post_views (post_id);
CREATE INDEX IF NOT EXISTS ix_post_views_user_id ON public.post_views (user_id);
CREATE INDEX IF NOT EXISTS ix_post_views_created_at ON public.post_views (created_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_post_view_post_user ON public.post_views (post_id, user_id);

GRANT USAGE, CREATE ON SCHEMA public TO shopno;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.posts,
    public.blog_posts,
    public.blog_likes,
    public.blog_comments,
    public.blog_shares,
    public.blog_saved_posts,
    public.likes,
    public.saved_posts,
    public.reactions,
    public.shares,
    public.follows,
    public.comments
TO shopno;
GRANT SELECT, INSERT ON TABLE public.blog_admin_audit, public.post_views TO shopno;

COMMIT;
