-- Least-privilege runtime access for the external advertising policy API.
-- The ad-service connects as "shopno"; migrations run as the database owner.
\connect ads

BEGIN;

GRANT SELECT, INSERT, UPDATE
ON TABLE public.external_ad_policies
TO shopno;

GRANT SELECT, INSERT
ON TABLE public.external_ad_policy_audit
TO shopno;

GRANT USAGE, SELECT
ON SEQUENCE public.external_ad_policy_audit_id_seq
TO shopno;

COMMIT;
