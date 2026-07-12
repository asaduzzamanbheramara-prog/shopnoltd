--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4 (Debian 15.4-1.pgdg110+1)
-- Dumped by pg_dump version 15.4 (Debian 15.4-1.pgdg110+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tiger; Type: SCHEMA; Schema: -; Owner: kobo
--

CREATE SCHEMA tiger;


ALTER SCHEMA tiger OWNER TO kobo;

--
-- Name: tiger_data; Type: SCHEMA; Schema: -; Owner: kobo
--

CREATE SCHEMA tiger_data;


ALTER SCHEMA tiger_data OWNER TO kobo;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: kobo
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO kobo;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: kobo
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: postgis_tiger_geocoder; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder WITH SCHEMA tiger;


--
-- Name: EXTENSION postgis_tiger_geocoder; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_tiger_geocoder IS 'PostGIS tiger geocoder and reverse geocoder';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO kobo;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.auth_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO kobo;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO kobo;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.auth_group_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_permissions_id_seq OWNER TO kobo;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO kobo;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.auth_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO kobo;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(30) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO kobo;

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO kobo;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.auth_user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_groups_id_seq OWNER TO kobo;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.auth_user_groups_id_seq OWNED BY public.auth_user_groups.id;


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.auth_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_id_seq OWNER TO kobo;

--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO kobo;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.auth_user_user_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_user_permissions_id_seq OWNER TO kobo;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.auth_user_user_permissions_id_seq OWNED BY public.auth_user_user_permissions.id;


--
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.authtoken_token OWNER TO kobo;

--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO kobo;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_admin_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_admin_log_id_seq OWNER TO kobo;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


--
-- Name: django_celery_beat_clockedschedule; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_celery_beat_clockedschedule (
    id integer NOT NULL,
    clocked_time timestamp with time zone NOT NULL,
    enabled boolean NOT NULL
);


ALTER TABLE public.django_celery_beat_clockedschedule OWNER TO kobo;

--
-- Name: django_celery_beat_clockedschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_celery_beat_clockedschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_clockedschedule_id_seq OWNER TO kobo;

--
-- Name: django_celery_beat_clockedschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_celery_beat_clockedschedule_id_seq OWNED BY public.django_celery_beat_clockedschedule.id;


--
-- Name: django_celery_beat_crontabschedule; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_celery_beat_crontabschedule (
    id integer NOT NULL,
    minute character varying(240) NOT NULL,
    hour character varying(96) NOT NULL,
    day_of_week character varying(64) NOT NULL,
    day_of_month character varying(124) NOT NULL,
    month_of_year character varying(64) NOT NULL,
    timezone character varying(63) NOT NULL
);


ALTER TABLE public.django_celery_beat_crontabschedule OWNER TO kobo;

--
-- Name: django_celery_beat_crontabschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_celery_beat_crontabschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_crontabschedule_id_seq OWNER TO kobo;

--
-- Name: django_celery_beat_crontabschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_celery_beat_crontabschedule_id_seq OWNED BY public.django_celery_beat_crontabschedule.id;


--
-- Name: django_celery_beat_intervalschedule; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_celery_beat_intervalschedule (
    id integer NOT NULL,
    every integer NOT NULL,
    period character varying(24) NOT NULL
);


ALTER TABLE public.django_celery_beat_intervalschedule OWNER TO kobo;

--
-- Name: django_celery_beat_intervalschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_celery_beat_intervalschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_intervalschedule_id_seq OWNER TO kobo;

--
-- Name: django_celery_beat_intervalschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_celery_beat_intervalschedule_id_seq OWNED BY public.django_celery_beat_intervalschedule.id;


--
-- Name: django_celery_beat_periodictask; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_celery_beat_periodictask (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    task character varying(200) NOT NULL,
    args text NOT NULL,
    kwargs text NOT NULL,
    queue character varying(200),
    exchange character varying(200),
    routing_key character varying(200),
    expires timestamp with time zone,
    enabled boolean NOT NULL,
    last_run_at timestamp with time zone,
    total_run_count integer NOT NULL,
    date_changed timestamp with time zone NOT NULL,
    description text NOT NULL,
    crontab_id integer,
    interval_id integer,
    solar_id integer,
    one_off boolean NOT NULL,
    start_time timestamp with time zone,
    priority integer,
    headers text NOT NULL,
    clocked_id integer,
    expire_seconds integer,
    CONSTRAINT django_celery_beat_periodictask_expire_seconds_check CHECK ((expire_seconds >= 0)),
    CONSTRAINT django_celery_beat_periodictask_priority_check CHECK ((priority >= 0)),
    CONSTRAINT django_celery_beat_periodictask_total_run_count_check CHECK ((total_run_count >= 0))
);


ALTER TABLE public.django_celery_beat_periodictask OWNER TO kobo;

--
-- Name: django_celery_beat_periodictask_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_celery_beat_periodictask_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_periodictask_id_seq OWNER TO kobo;

--
-- Name: django_celery_beat_periodictask_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_celery_beat_periodictask_id_seq OWNED BY public.django_celery_beat_periodictask.id;


--
-- Name: django_celery_beat_periodictasks; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_celery_beat_periodictasks (
    ident smallint NOT NULL,
    last_update timestamp with time zone NOT NULL
);


ALTER TABLE public.django_celery_beat_periodictasks OWNER TO kobo;

--
-- Name: django_celery_beat_solarschedule; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_celery_beat_solarschedule (
    id integer NOT NULL,
    event character varying(24) NOT NULL,
    latitude numeric(9,6) NOT NULL,
    longitude numeric(9,6) NOT NULL
);


ALTER TABLE public.django_celery_beat_solarschedule OWNER TO kobo;

--
-- Name: django_celery_beat_solarschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_celery_beat_solarschedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_celery_beat_solarschedule_id_seq OWNER TO kobo;

--
-- Name: django_celery_beat_solarschedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_celery_beat_solarschedule_id_seq OWNED BY public.django_celery_beat_solarschedule.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO kobo;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_content_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_content_type_id_seq OWNER TO kobo;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


--
-- Name: django_digest_partialdigest; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_digest_partialdigest (
    id integer NOT NULL,
    login character varying(128) NOT NULL,
    partial_digest character varying(100) NOT NULL,
    confirmed boolean NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.django_digest_partialdigest OWNER TO kobo;

--
-- Name: django_digest_partialdigest_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_digest_partialdigest_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_digest_partialdigest_id_seq OWNER TO kobo;

--
-- Name: django_digest_partialdigest_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_digest_partialdigest_id_seq OWNED BY public.django_digest_partialdigest.id;


--
-- Name: django_digest_usernonce; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_digest_usernonce (
    id integer NOT NULL,
    nonce character varying(100) NOT NULL,
    count integer,
    last_used_at timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.django_digest_usernonce OWNER TO kobo;

--
-- Name: django_digest_usernonce_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_digest_usernonce_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_digest_usernonce_id_seq OWNER TO kobo;

--
-- Name: django_digest_usernonce_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_digest_usernonce_id_seq OWNED BY public.django_digest_usernonce.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO kobo;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_migrations_id_seq OWNER TO kobo;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO kobo;

--
-- Name: django_site; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.django_site (
    id integer NOT NULL,
    domain character varying(100) NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.django_site OWNER TO kobo;

--
-- Name: django_site_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.django_site_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_site_id_seq OWNER TO kobo;

--
-- Name: django_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.django_site_id_seq OWNED BY public.django_site.id;


--
-- Name: guardian_groupobjectpermission; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.guardian_groupobjectpermission (
    id integer NOT NULL,
    object_pk character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.guardian_groupobjectpermission OWNER TO kobo;

--
-- Name: guardian_groupobjectpermission_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.guardian_groupobjectpermission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.guardian_groupobjectpermission_id_seq OWNER TO kobo;

--
-- Name: guardian_groupobjectpermission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.guardian_groupobjectpermission_id_seq OWNED BY public.guardian_groupobjectpermission.id;


--
-- Name: guardian_userobjectpermission; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.guardian_userobjectpermission (
    id integer NOT NULL,
    object_pk character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    permission_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.guardian_userobjectpermission OWNER TO kobo;

--
-- Name: guardian_userobjectpermission_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.guardian_userobjectpermission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.guardian_userobjectpermission_id_seq OWNER TO kobo;

--
-- Name: guardian_userobjectpermission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.guardian_userobjectpermission_id_seq OWNED BY public.guardian_userobjectpermission.id;


--
-- Name: logger_attachment; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_attachment (
    id integer NOT NULL,
    media_file character varying(380) NOT NULL,
    mimetype character varying(100) NOT NULL,
    instance_id integer NOT NULL,
    media_file_basename character varying(260),
    media_file_size integer,
    CONSTRAINT logger_attachment_media_file_size_check CHECK ((media_file_size >= 0))
);


ALTER TABLE public.logger_attachment OWNER TO kobo;

--
-- Name: logger_attachment_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_attachment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_attachment_id_seq OWNER TO kobo;

--
-- Name: logger_attachment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_attachment_id_seq OWNED BY public.logger_attachment.id;


--
-- Name: logger_instance; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_instance (
    id integer NOT NULL,
    json text NOT NULL,
    xml text NOT NULL,
    date_created timestamp with time zone NOT NULL,
    date_modified timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    status character varying(20) NOT NULL,
    uuid character varying(249) NOT NULL,
    geom public.geometry(GeometryCollection,4326),
    survey_type_id integer NOT NULL,
    user_id integer,
    xform_id integer,
    xml_hash character varying(64),
    validation_status text,
    is_synced_with_mongo smallint,
    posted_to_kpi smallint,
    CONSTRAINT logger_instance_is_synced_with_mongo_check CHECK ((is_synced_with_mongo >= 0)),
    CONSTRAINT logger_instance_posted_to_kpi_check CHECK ((posted_to_kpi >= 0))
);


ALTER TABLE public.logger_instance OWNER TO kobo;

--
-- Name: logger_instance_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_instance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_instance_id_seq OWNER TO kobo;

--
-- Name: logger_instance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_instance_id_seq OWNED BY public.logger_instance.id;


--
-- Name: logger_instancehistory; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_instancehistory (
    id integer NOT NULL,
    xml text NOT NULL,
    uuid character varying(249) NOT NULL,
    date_created timestamp with time zone NOT NULL,
    date_modified timestamp with time zone NOT NULL,
    xform_instance_id integer NOT NULL
);


ALTER TABLE public.logger_instancehistory OWNER TO kobo;

--
-- Name: logger_instancehistory_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_instancehistory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_instancehistory_id_seq OWNER TO kobo;

--
-- Name: logger_instancehistory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_instancehistory_id_seq OWNED BY public.logger_instancehistory.id;


--
-- Name: logger_note; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_note (
    id integer NOT NULL,
    note text NOT NULL,
    date_created timestamp with time zone NOT NULL,
    date_modified timestamp with time zone NOT NULL,
    instance_id integer NOT NULL
);


ALTER TABLE public.logger_note OWNER TO kobo;

--
-- Name: logger_note_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_note_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_note_id_seq OWNER TO kobo;

--
-- Name: logger_note_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_note_id_seq OWNED BY public.logger_note.id;


--
-- Name: logger_submissioncounter; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_submissioncounter (
    id integer NOT NULL,
    count integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    user_id integer
);


ALTER TABLE public.logger_submissioncounter OWNER TO kobo;

--
-- Name: logger_submissioncounter_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_submissioncounter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_submissioncounter_id_seq OWNER TO kobo;

--
-- Name: logger_submissioncounter_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_submissioncounter_id_seq OWNED BY public.logger_submissioncounter.id;


--
-- Name: logger_surveytype; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_surveytype (
    id integer NOT NULL,
    slug character varying(100) NOT NULL
);


ALTER TABLE public.logger_surveytype OWNER TO kobo;

--
-- Name: logger_surveytype_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_surveytype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_surveytype_id_seq OWNER TO kobo;

--
-- Name: logger_surveytype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_surveytype_id_seq OWNED BY public.logger_surveytype.id;


--
-- Name: logger_xform; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.logger_xform (
    id integer NOT NULL,
    xls character varying(100),
    json text NOT NULL,
    description text,
    xml text NOT NULL,
    require_auth boolean NOT NULL,
    shared boolean NOT NULL,
    shared_data boolean NOT NULL,
    downloadable boolean NOT NULL,
    encrypted boolean NOT NULL,
    id_string character varying(100) NOT NULL,
    title character varying(255) NOT NULL,
    date_created timestamp with time zone NOT NULL,
    date_modified timestamp with time zone NOT NULL,
    last_submission_time timestamp with time zone,
    has_start_time boolean NOT NULL,
    uuid character varying(32) NOT NULL,
    instances_with_geopoints boolean NOT NULL,
    num_of_submissions integer NOT NULL,
    user_id integer,
    has_kpi_hooks smallint,
    kpi_asset_uid character varying(32),
    CONSTRAINT logger_xform_has_kpi_hooks_check CHECK ((has_kpi_hooks >= 0))
);


ALTER TABLE public.logger_xform OWNER TO kobo;

--
-- Name: logger_xform_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.logger_xform_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logger_xform_id_seq OWNER TO kobo;

--
-- Name: logger_xform_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.logger_xform_id_seq OWNED BY public.logger_xform.id;


--
-- Name: main_metadata; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.main_metadata (
    id integer NOT NULL,
    data_type character varying(255) NOT NULL,
    data_value character varying(255) NOT NULL,
    data_file character varying(100),
    data_file_type character varying(255),
    file_hash character varying(50),
    xform_id integer NOT NULL,
    from_kpi boolean NOT NULL
);


ALTER TABLE public.main_metadata OWNER TO kobo;

--
-- Name: main_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.main_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.main_metadata_id_seq OWNER TO kobo;

--
-- Name: main_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.main_metadata_id_seq OWNED BY public.main_metadata.id;


--
-- Name: main_userprofile; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.main_userprofile (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    city character varying(255) NOT NULL,
    country character varying(2) NOT NULL,
    organization character varying(255) NOT NULL,
    home_page character varying(255) NOT NULL,
    twitter character varying(255) NOT NULL,
    description character varying(255) NOT NULL,
    require_auth boolean NOT NULL,
    address character varying(255) NOT NULL,
    phonenumber character varying(30) NOT NULL,
    num_of_submissions integer NOT NULL,
    metadata text NOT NULL,
    created_by_id integer,
    user_id integer NOT NULL
);


ALTER TABLE public.main_userprofile OWNER TO kobo;

--
-- Name: main_userprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.main_userprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.main_userprofile_id_seq OWNER TO kobo;

--
-- Name: main_userprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.main_userprofile_id_seq OWNED BY public.main_userprofile.id;


--
-- Name: oauth2_provider_accesstoken; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.oauth2_provider_accesstoken (
    id bigint NOT NULL,
    token character varying(255) NOT NULL,
    expires timestamp with time zone NOT NULL,
    scope text NOT NULL,
    application_id bigint,
    user_id integer,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL,
    source_refresh_token_id bigint
);


ALTER TABLE public.oauth2_provider_accesstoken OWNER TO kobo;

--
-- Name: oauth2_provider_accesstoken_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.oauth2_provider_accesstoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth2_provider_accesstoken_id_seq OWNER TO kobo;

--
-- Name: oauth2_provider_accesstoken_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.oauth2_provider_accesstoken_id_seq OWNED BY public.oauth2_provider_accesstoken.id;


--
-- Name: oauth2_provider_application; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.oauth2_provider_application (
    id bigint NOT NULL,
    client_id character varying(100) NOT NULL,
    redirect_uris text NOT NULL,
    client_type character varying(32) NOT NULL,
    authorization_grant_type character varying(32) NOT NULL,
    client_secret character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    user_id integer,
    skip_authorization boolean NOT NULL,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL
);


ALTER TABLE public.oauth2_provider_application OWNER TO kobo;

--
-- Name: oauth2_provider_application_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.oauth2_provider_application_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth2_provider_application_id_seq OWNER TO kobo;

--
-- Name: oauth2_provider_application_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.oauth2_provider_application_id_seq OWNED BY public.oauth2_provider_application.id;


--
-- Name: oauth2_provider_grant; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.oauth2_provider_grant (
    id bigint NOT NULL,
    code character varying(255) NOT NULL,
    expires timestamp with time zone NOT NULL,
    redirect_uri character varying(255) NOT NULL,
    scope text NOT NULL,
    application_id bigint NOT NULL,
    user_id integer NOT NULL,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL,
    code_challenge character varying(128) NOT NULL,
    code_challenge_method character varying(10) NOT NULL
);


ALTER TABLE public.oauth2_provider_grant OWNER TO kobo;

--
-- Name: oauth2_provider_grant_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.oauth2_provider_grant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth2_provider_grant_id_seq OWNER TO kobo;

--
-- Name: oauth2_provider_grant_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.oauth2_provider_grant_id_seq OWNED BY public.oauth2_provider_grant.id;


--
-- Name: oauth2_provider_refreshtoken; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.oauth2_provider_refreshtoken (
    id bigint NOT NULL,
    token character varying(255) NOT NULL,
    access_token_id bigint,
    application_id bigint NOT NULL,
    user_id integer NOT NULL,
    created timestamp with time zone NOT NULL,
    updated timestamp with time zone NOT NULL,
    revoked timestamp with time zone
);


ALTER TABLE public.oauth2_provider_refreshtoken OWNER TO kobo;

--
-- Name: oauth2_provider_refreshtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.oauth2_provider_refreshtoken_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.oauth2_provider_refreshtoken_id_seq OWNER TO kobo;

--
-- Name: oauth2_provider_refreshtoken_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.oauth2_provider_refreshtoken_id_seq OWNED BY public.oauth2_provider_refreshtoken.id;


--
-- Name: registration_registrationprofile; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.registration_registrationprofile (
    id integer NOT NULL,
    activation_key character varying(64) NOT NULL,
    user_id integer NOT NULL,
    activated boolean NOT NULL
);


ALTER TABLE public.registration_registrationprofile OWNER TO kobo;

--
-- Name: registration_registrationprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.registration_registrationprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.registration_registrationprofile_id_seq OWNER TO kobo;

--
-- Name: registration_registrationprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.registration_registrationprofile_id_seq OWNED BY public.registration_registrationprofile.id;


--
-- Name: registration_supervisedregistrationprofile; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.registration_supervisedregistrationprofile (
    registrationprofile_ptr_id integer NOT NULL
);


ALTER TABLE public.registration_supervisedregistrationprofile OWNER TO kobo;

--
-- Name: restservice_restservice; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.restservice_restservice (
    id integer NOT NULL,
    service_url character varying(200) NOT NULL,
    name character varying(50) NOT NULL,
    xform_id integer NOT NULL
);


ALTER TABLE public.restservice_restservice OWNER TO kobo;

--
-- Name: restservice_restservice_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.restservice_restservice_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.restservice_restservice_id_seq OWNER TO kobo;

--
-- Name: restservice_restservice_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.restservice_restservice_id_seq OWNED BY public.restservice_restservice.id;


--
-- Name: reversion_revision; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.reversion_revision (
    id integer NOT NULL,
    date_created timestamp with time zone NOT NULL,
    comment text NOT NULL,
    user_id integer
);


ALTER TABLE public.reversion_revision OWNER TO kobo;

--
-- Name: reversion_revision_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.reversion_revision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reversion_revision_id_seq OWNER TO kobo;

--
-- Name: reversion_revision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.reversion_revision_id_seq OWNED BY public.reversion_revision.id;


--
-- Name: reversion_version; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.reversion_version (
    id integer NOT NULL,
    object_id character varying(191) NOT NULL,
    format character varying(255) NOT NULL,
    serialized_data text NOT NULL,
    object_repr text NOT NULL,
    content_type_id integer NOT NULL,
    revision_id integer NOT NULL,
    db character varying(191) NOT NULL
);


ALTER TABLE public.reversion_version OWNER TO kobo;

--
-- Name: reversion_version_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.reversion_version_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reversion_version_id_seq OWNER TO kobo;

--
-- Name: reversion_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.reversion_version_id_seq OWNED BY public.reversion_version.id;


--
-- Name: taggit_tag; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.taggit_tag (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    slug character varying(100) NOT NULL
);


ALTER TABLE public.taggit_tag OWNER TO kobo;

--
-- Name: taggit_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.taggit_tag_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.taggit_tag_id_seq OWNER TO kobo;

--
-- Name: taggit_tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.taggit_tag_id_seq OWNED BY public.taggit_tag.id;


--
-- Name: taggit_taggeditem; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.taggit_taggeditem (
    id integer NOT NULL,
    object_id integer NOT NULL,
    content_type_id integer NOT NULL,
    tag_id integer NOT NULL
);


ALTER TABLE public.taggit_taggeditem OWNER TO kobo;

--
-- Name: taggit_taggeditem_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.taggit_taggeditem_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.taggit_taggeditem_id_seq OWNER TO kobo;

--
-- Name: taggit_taggeditem_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.taggit_taggeditem_id_seq OWNED BY public.taggit_taggeditem.id;


--
-- Name: viewer_columnrename; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.viewer_columnrename (
    id integer NOT NULL,
    xpath character varying(255) NOT NULL,
    column_name character varying(32) NOT NULL
);


ALTER TABLE public.viewer_columnrename OWNER TO kobo;

--
-- Name: viewer_columnrename_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.viewer_columnrename_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.viewer_columnrename_id_seq OWNER TO kobo;

--
-- Name: viewer_columnrename_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.viewer_columnrename_id_seq OWNED BY public.viewer_columnrename.id;


--
-- Name: viewer_export; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.viewer_export (
    id integer NOT NULL,
    created_on timestamp with time zone NOT NULL,
    filename character varying(255),
    filedir character varying(255),
    export_type character varying(10) NOT NULL,
    task_id character varying(255),
    time_of_last_submission timestamp with time zone,
    internal_status smallint NOT NULL,
    export_url character varying(200),
    xform_id integer NOT NULL
);


ALTER TABLE public.viewer_export OWNER TO kobo;

--
-- Name: viewer_export_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.viewer_export_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.viewer_export_id_seq OWNER TO kobo;

--
-- Name: viewer_export_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.viewer_export_id_seq OWNED BY public.viewer_export.id;


--
-- Name: viewer_instancemodification; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.viewer_instancemodification (
    id integer NOT NULL,
    action character varying(50) NOT NULL,
    xpath character varying(50) NOT NULL,
    date_created timestamp with time zone NOT NULL,
    date_modified timestamp with time zone NOT NULL,
    instance_id integer NOT NULL,
    user_id integer
);


ALTER TABLE public.viewer_instancemodification OWNER TO kobo;

--
-- Name: viewer_instancemodification_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.viewer_instancemodification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.viewer_instancemodification_id_seq OWNER TO kobo;

--
-- Name: viewer_instancemodification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.viewer_instancemodification_id_seq OWNED BY public.viewer_instancemodification.id;


--
-- Name: viewer_parsedinstance; Type: TABLE; Schema: public; Owner: kobo
--

CREATE TABLE public.viewer_parsedinstance (
    id integer NOT NULL,
    start_time timestamp with time zone,
    end_time timestamp with time zone,
    lat double precision,
    lng double precision,
    instance_id integer NOT NULL
);


ALTER TABLE public.viewer_parsedinstance OWNER TO kobo;

--
-- Name: viewer_parsedinstance_id_seq; Type: SEQUENCE; Schema: public; Owner: kobo
--

CREATE SEQUENCE public.viewer_parsedinstance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.viewer_parsedinstance_id_seq OWNER TO kobo;

--
-- Name: viewer_parsedinstance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: kobo
--

ALTER SEQUENCE public.viewer_parsedinstance_id_seq OWNED BY public.viewer_parsedinstance.id;


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- Name: auth_user id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);


--
-- Name: auth_user_groups id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_groups ALTER COLUMN id SET DEFAULT nextval('public.auth_user_groups_id_seq'::regclass);


--
-- Name: auth_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_user_user_permissions_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


--
-- Name: django_celery_beat_clockedschedule id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_clockedschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_clockedschedule_id_seq'::regclass);


--
-- Name: django_celery_beat_crontabschedule id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_crontabschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_crontabschedule_id_seq'::regclass);


--
-- Name: django_celery_beat_intervalschedule id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_intervalschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_intervalschedule_id_seq'::regclass);


--
-- Name: django_celery_beat_periodictask id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_periodictask_id_seq'::regclass);


--
-- Name: django_celery_beat_solarschedule id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_solarschedule ALTER COLUMN id SET DEFAULT nextval('public.django_celery_beat_solarschedule_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- Name: django_digest_partialdigest id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_partialdigest ALTER COLUMN id SET DEFAULT nextval('public.django_digest_partialdigest_id_seq'::regclass);


--
-- Name: django_digest_usernonce id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_usernonce ALTER COLUMN id SET DEFAULT nextval('public.django_digest_usernonce_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- Name: django_site id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_site ALTER COLUMN id SET DEFAULT nextval('public.django_site_id_seq'::regclass);


--
-- Name: guardian_groupobjectpermission id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_groupobjectpermission ALTER COLUMN id SET DEFAULT nextval('public.guardian_groupobjectpermission_id_seq'::regclass);


--
-- Name: guardian_userobjectpermission id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_userobjectpermission ALTER COLUMN id SET DEFAULT nextval('public.guardian_userobjectpermission_id_seq'::regclass);


--
-- Name: logger_attachment id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_attachment ALTER COLUMN id SET DEFAULT nextval('public.logger_attachment_id_seq'::regclass);


--
-- Name: logger_instance id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instance ALTER COLUMN id SET DEFAULT nextval('public.logger_instance_id_seq'::regclass);


--
-- Name: logger_instancehistory id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instancehistory ALTER COLUMN id SET DEFAULT nextval('public.logger_instancehistory_id_seq'::regclass);


--
-- Name: logger_note id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_note ALTER COLUMN id SET DEFAULT nextval('public.logger_note_id_seq'::regclass);


--
-- Name: logger_submissioncounter id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_submissioncounter ALTER COLUMN id SET DEFAULT nextval('public.logger_submissioncounter_id_seq'::regclass);


--
-- Name: logger_surveytype id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_surveytype ALTER COLUMN id SET DEFAULT nextval('public.logger_surveytype_id_seq'::regclass);


--
-- Name: logger_xform id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_xform ALTER COLUMN id SET DEFAULT nextval('public.logger_xform_id_seq'::regclass);


--
-- Name: main_metadata id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_metadata ALTER COLUMN id SET DEFAULT nextval('public.main_metadata_id_seq'::regclass);


--
-- Name: main_userprofile id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_userprofile ALTER COLUMN id SET DEFAULT nextval('public.main_userprofile_id_seq'::regclass);


--
-- Name: oauth2_provider_accesstoken id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken ALTER COLUMN id SET DEFAULT nextval('public.oauth2_provider_accesstoken_id_seq'::regclass);


--
-- Name: oauth2_provider_application id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_application ALTER COLUMN id SET DEFAULT nextval('public.oauth2_provider_application_id_seq'::regclass);


--
-- Name: oauth2_provider_grant id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_grant ALTER COLUMN id SET DEFAULT nextval('public.oauth2_provider_grant_id_seq'::regclass);


--
-- Name: oauth2_provider_refreshtoken id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken ALTER COLUMN id SET DEFAULT nextval('public.oauth2_provider_refreshtoken_id_seq'::regclass);


--
-- Name: registration_registrationprofile id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.registration_registrationprofile ALTER COLUMN id SET DEFAULT nextval('public.registration_registrationprofile_id_seq'::regclass);


--
-- Name: restservice_restservice id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.restservice_restservice ALTER COLUMN id SET DEFAULT nextval('public.restservice_restservice_id_seq'::regclass);


--
-- Name: reversion_revision id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_revision ALTER COLUMN id SET DEFAULT nextval('public.reversion_revision_id_seq'::regclass);


--
-- Name: reversion_version id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_version ALTER COLUMN id SET DEFAULT nextval('public.reversion_version_id_seq'::regclass);


--
-- Name: taggit_tag id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_tag ALTER COLUMN id SET DEFAULT nextval('public.taggit_tag_id_seq'::regclass);


--
-- Name: taggit_taggeditem id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_taggeditem ALTER COLUMN id SET DEFAULT nextval('public.taggit_taggeditem_id_seq'::regclass);


--
-- Name: viewer_columnrename id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_columnrename ALTER COLUMN id SET DEFAULT nextval('public.viewer_columnrename_id_seq'::regclass);


--
-- Name: viewer_export id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_export ALTER COLUMN id SET DEFAULT nextval('public.viewer_export_id_seq'::regclass);


--
-- Name: viewer_instancemodification id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_instancemodification ALTER COLUMN id SET DEFAULT nextval('public.viewer_instancemodification_id_seq'::regclass);


--
-- Name: viewer_parsedinstance id; Type: DEFAULT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_parsedinstance ALTER COLUMN id SET DEFAULT nextval('public.viewer_parsedinstance_id_seq'::regclass);


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add Token	5	add_token
18	Can change Token	5	change_token
19	Can delete Token	5	delete_token
20	Can view Token	5	view_token
21	Can add content type	6	add_contenttype
22	Can change content type	6	change_contenttype
23	Can delete content type	6	delete_contenttype
24	Can view content type	6	view_contenttype
25	Can add crontab	7	add_crontabschedule
26	Can change crontab	7	change_crontabschedule
27	Can delete crontab	7	delete_crontabschedule
28	Can view crontab	7	view_crontabschedule
29	Can add interval	8	add_intervalschedule
30	Can change interval	8	change_intervalschedule
31	Can delete interval	8	delete_intervalschedule
32	Can view interval	8	view_intervalschedule
33	Can add periodic task	9	add_periodictask
34	Can change periodic task	9	change_periodictask
35	Can delete periodic task	9	delete_periodictask
36	Can view periodic task	9	view_periodictask
37	Can add periodic tasks	10	add_periodictasks
38	Can change periodic tasks	10	change_periodictasks
39	Can delete periodic tasks	10	delete_periodictasks
40	Can view periodic tasks	10	view_periodictasks
41	Can add solar event	11	add_solarschedule
42	Can change solar event	11	change_solarschedule
43	Can delete solar event	11	delete_solarschedule
44	Can view solar event	11	view_solarschedule
45	Can add clocked	12	add_clockedschedule
46	Can change clocked	12	change_clockedschedule
47	Can delete clocked	12	delete_clockedschedule
48	Can view clocked	12	view_clockedschedule
49	Can add partial digest	13	add_partialdigest
50	Can change partial digest	13	change_partialdigest
51	Can delete partial digest	13	delete_partialdigest
52	Can view partial digest	13	view_partialdigest
53	Can add user nonce	14	add_usernonce
54	Can change user nonce	14	change_usernonce
55	Can delete user nonce	14	delete_usernonce
56	Can view user nonce	14	view_usernonce
57	Can add post gis geometry columns	15	add_postgisgeometrycolumns
58	Can change post gis geometry columns	15	change_postgisgeometrycolumns
59	Can delete post gis geometry columns	15	delete_postgisgeometrycolumns
60	Can view post gis geometry columns	15	view_postgisgeometrycolumns
61	Can add post gis spatial ref sys	16	add_postgisspatialrefsys
62	Can change post gis spatial ref sys	16	change_postgisspatialrefsys
63	Can delete post gis spatial ref sys	16	delete_postgisspatialrefsys
64	Can view post gis spatial ref sys	16	view_postgisspatialrefsys
65	Can add group object permission	17	add_groupobjectpermission
66	Can change group object permission	17	change_groupobjectpermission
67	Can delete group object permission	17	delete_groupobjectpermission
68	Can view group object permission	17	view_groupobjectpermission
69	Can add user object permission	18	add_userobjectpermission
70	Can change user object permission	18	change_userobjectpermission
71	Can delete user object permission	18	delete_userobjectpermission
72	Can view user object permission	18	view_userobjectpermission
73	Can add attachment	19	add_attachment
74	Can change attachment	19	change_attachment
75	Can delete attachment	19	delete_attachment
76	Can view attachment	19	view_attachment
77	Can add instance	20	add_instance
78	Can change instance	20	change_instance
79	Can delete instance	20	delete_instance
80	Can view instance	20	view_instance
81	Can add instance history	21	add_instancehistory
82	Can change instance history	21	change_instancehistory
83	Can delete instance history	21	delete_instancehistory
84	Can view instance history	21	view_instancehistory
85	Can add note	22	add_note
86	Can change note	22	change_note
87	Can delete note	22	delete_note
88	Can view note	22	view_note
89	Can add survey type	23	add_surveytype
90	Can change survey type	23	change_surveytype
91	Can delete survey type	23	delete_surveytype
92	Can view survey type	23	view_surveytype
93	Can add XForm	24	add_xform
94	Can change XForm	24	change_xform
95	Can delete XForm	24	delete_xform
96	Can view XForm	24	view_xform
97	Can make submissions to the form	24	report_xform
98	Can move form between projects	24	move_xform
99	Can transfer form ownership	24	transfer_xform
100	Can validate submissions	24	validate_xform
101	Can delete submissions	24	delete_data_xform
102	Can add meta data	25	add_metadata
103	Can change meta data	25	change_metadata
104	Can delete meta data	25	delete_metadata
105	Can view meta data	25	view_metadata
106	Can add token storage model	26	add_tokenstoragemodel
107	Can change token storage model	26	change_tokenstoragemodel
108	Can delete token storage model	26	delete_tokenstoragemodel
109	Can view token storage model	26	view_tokenstoragemodel
110	Can add user profile	27	add_userprofile
111	Can change user profile	27	change_userprofile
112	Can delete user profile	27	delete_userprofile
113	Can view user profile	27	view_userprofile
114	Can add/upload an xform to user profile	27	can_add_xform
115	Can view user profile	27	view_profile
116	Can add tag	28	add_tag
117	Can change tag	28	change_tag
118	Can delete tag	28	delete_tag
119	Can view tag	28	view_tag
120	Can add tagged item	29	add_taggeditem
121	Can change tagged item	29	change_taggeditem
122	Can delete tagged item	29	delete_taggeditem
123	Can view tagged item	29	view_taggeditem
124	Can add session	30	add_session
125	Can change session	30	change_session
126	Can delete session	30	delete_session
127	Can view session	30	view_session
128	Can add site	31	add_site
129	Can change site	31	change_site
130	Can delete site	31	delete_site
131	Can view site	31	view_site
132	Can add registration profile	32	add_registrationprofile
133	Can change registration profile	32	change_registrationprofile
134	Can delete registration profile	32	delete_registrationprofile
135	Can view registration profile	32	view_registrationprofile
136	Can add supervised registration profile	33	add_supervisedregistrationprofile
137	Can change supervised registration profile	33	change_supervisedregistrationprofile
138	Can delete supervised registration profile	33	delete_supervisedregistrationprofile
139	Can view supervised registration profile	33	view_supervisedregistrationprofile
140	Can add revision	34	add_revision
141	Can change revision	34	change_revision
142	Can delete revision	34	delete_revision
143	Can view revision	34	view_revision
144	Can add version	35	add_version
145	Can change version	35	change_version
146	Can delete version	35	delete_version
147	Can view version	35	view_version
148	Can add application	36	add_application
149	Can change application	36	change_application
150	Can delete application	36	delete_application
151	Can view application	36	view_application
152	Can add access token	37	add_accesstoken
153	Can change access token	37	change_accesstoken
154	Can delete access token	37	delete_accesstoken
155	Can view access token	37	view_accesstoken
156	Can add grant	38	add_grant
157	Can change grant	38	change_grant
158	Can delete grant	38	delete_grant
159	Can view grant	38	view_grant
160	Can add refresh token	39	add_refreshtoken
161	Can change refresh token	39	change_refreshtoken
162	Can delete refresh token	39	delete_refreshtoken
163	Can view refresh token	39	view_refreshtoken
164	Can add submission counter	40	add_submissioncounter
165	Can change submission counter	40	change_submissioncounter
166	Can delete submission counter	40	delete_submissioncounter
167	Can view submission counter	40	view_submissioncounter
168	Can add column rename	41	add_columnrename
169	Can change column rename	41	change_columnrename
170	Can delete column rename	41	delete_columnrename
171	Can view column rename	41	view_columnrename
172	Can add export	42	add_export
173	Can change export	42	change_export
174	Can delete export	42	delete_export
175	Can view export	42	view_export
176	Can add instance modification	43	add_instancemodification
177	Can change instance modification	43	change_instancemodification
178	Can delete instance modification	43	delete_instancemodification
179	Can view instance modification	43	view_instancemodification
180	Can add parsed instance	44	add_parsedinstance
181	Can change parsed instance	44	change_parsedinstance
182	Can delete parsed instance	44	delete_parsedinstance
183	Can view parsed instance	44	view_parsedinstance
184	Can add data dictionary	45	add_datadictionary
185	Can change data dictionary	45	change_datadictionary
186	Can delete data dictionary	45	delete_datadictionary
187	Can view data dictionary	45	view_datadictionary
188	Can add rest service	46	add_restservice
189	Can change rest service	46	change_restservice
190	Can delete rest service	46	delete_restservice
191	Can view rest service	46	view_restservice
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
-1		\N	f	AnonymousUser				f	t	2026-07-10 08:29:17.53574+00
\.


--
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.auth_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.auth_user_user_permissions (id, user_id, permission_id) FROM stdin;
1	-1	110
2	-1	114
3	-1	111
4	-1	112
5	-1	115
6	-1	113
7	-1	93
8	-1	94
9	-1	101
10	-1	95
11	-1	98
12	-1	97
13	-1	99
14	-1	100
15	-1	96
16	-1	85
17	-1	86
18	-1	87
19	-1	88
\.


--
-- Data for Name: authtoken_token; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.authtoken_token (key, created, user_id) FROM stdin;
9d5f0b15e3495fda073e9ac8d3a47a39d6ebed79	2026-07-10 08:29:17.542461+00	-1
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
\.


--
-- Data for Name: django_celery_beat_clockedschedule; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_celery_beat_clockedschedule (id, clocked_time, enabled) FROM stdin;
\.


--
-- Data for Name: django_celery_beat_crontabschedule; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_celery_beat_crontabschedule (id, minute, hour, day_of_week, day_of_month, month_of_year, timezone) FROM stdin;
1	0	4	*	*	*	UTC
\.


--
-- Data for Name: django_celery_beat_intervalschedule; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_celery_beat_intervalschedule (id, every, period) FROM stdin;
1	21600	seconds
\.


--
-- Data for Name: django_celery_beat_periodictask; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_celery_beat_periodictask (id, name, task, args, kwargs, queue, exchange, routing_key, expires, enabled, last_run_at, total_run_count, date_changed, description, crontab_id, interval_id, solar_id, one_off, start_time, priority, headers, clocked_id, expire_seconds) FROM stdin;
1	celery.backend_cleanup	celery.backend_cleanup	[]	{}	\N	\N	\N	\N	t	\N	0	2026-07-10 09:20:49.679235+00		1	\N	\N	f	\N	\N	{}	\N	43200
2	log-stuck-exports-and-mark-failed	onadata.apps.viewer.tasks.log_stuck_exports_and_mark_failed	[]	{}	kobocat_queue	\N	\N	\N	t	\N	0	2026-07-10 09:20:49.727501+00		\N	1	\N	f	\N	\N	{}	\N	\N
\.


--
-- Data for Name: django_celery_beat_periodictasks; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_celery_beat_periodictasks (ident, last_update) FROM stdin;
1	2026-07-10 09:20:49.723229+00
\.


--
-- Data for Name: django_celery_beat_solarschedule; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_celery_beat_solarschedule (id, event, latitude, longitude) FROM stdin;
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	auth	user
5	authtoken	token
6	contenttypes	contenttype
7	django_celery_beat	crontabschedule
8	django_celery_beat	intervalschedule
9	django_celery_beat	periodictask
10	django_celery_beat	periodictasks
11	django_celery_beat	solarschedule
12	django_celery_beat	clockedschedule
13	django_digest	partialdigest
14	django_digest	usernonce
15	gis	postgisgeometrycolumns
16	gis	postgisspatialrefsys
17	guardian	groupobjectpermission
18	guardian	userobjectpermission
19	logger	attachment
20	logger	instance
21	logger	instancehistory
22	logger	note
23	logger	surveytype
24	logger	xform
25	main	metadata
26	main	tokenstoragemodel
27	main	userprofile
28	taggit	tag
29	taggit	taggeditem
30	sessions	session
31	sites	site
32	registration	registrationprofile
33	registration	supervisedregistrationprofile
34	reversion	revision
35	reversion	version
36	oauth2_provider	application
37	oauth2_provider	accesstoken
38	oauth2_provider	grant
39	oauth2_provider	refreshtoken
40	logger	submissioncounter
41	viewer	columnrename
42	viewer	export
43	viewer	instancemodification
44	viewer	parsedinstance
45	viewer	datadictionary
46	restservice	restservice
\.


--
-- Data for Name: django_digest_partialdigest; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_digest_partialdigest (id, login, partial_digest, confirmed, user_id) FROM stdin;
\.


--
-- Data for Name: django_digest_usernonce; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_digest_usernonce (id, nonce, count, last_used_at, user_id) FROM stdin;
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2026-07-10 08:29:06.087547+00
2	auth	0001_initial	2026-07-10 08:29:06.180855+00
3	admin	0001_initial	2026-07-10 08:29:06.277379+00
4	admin	0002_logentry_remove_auto_add	2026-07-10 08:29:06.313672+00
5	admin	0003_logentry_add_action_flag_choices	2026-07-10 08:29:06.337763+00
6	guardian	0001_initial	2026-07-10 08:29:06.445011+00
7	contenttypes	0002_remove_content_type_name	2026-07-10 08:29:06.560403+00
8	auth	0002_alter_permission_name_max_length	2026-07-10 08:29:06.579186+00
9	auth	0003_alter_user_email_max_length	2026-07-10 08:29:06.609421+00
10	auth	0004_alter_user_username_opts	2026-07-10 08:29:06.634011+00
11	auth	0005_alter_user_last_login_null	2026-07-10 08:29:06.666212+00
12	auth	0006_require_contenttypes_0002	2026-07-10 08:29:06.671063+00
13	taggit	0001_initial	2026-07-10 08:29:06.720749+00
14	taggit	0002_auto_20150616_2121	2026-07-10 08:29:06.778367+00
15	logger	0001_initial	2026-07-10 08:29:07.184451+00
16	main	0001_initial	2026-07-10 08:29:07.548575+00
17	api	0001_initial	2026-07-10 08:29:07.925588+00
18	api	0002_remove_not_used_models	2026-07-10 08:29:08.778955+00
19	auth	0007_alter_validators_add_error_messages	2026-07-10 08:29:08.817369+00
20	auth	0008_alter_user_username_max_length	2026-07-10 08:29:08.868065+00
21	auth	0009_alter_user_last_name_max_length	2026-07-10 08:29:08.931506+00
22	auth	0010_alter_group_name_max_length	2026-07-10 08:29:08.977118+00
23	auth	0011_update_proxy_permissions	2026-07-10 08:29:09.04195+00
24	authtoken	0001_initial	2026-07-10 08:29:09.080962+00
25	authtoken	0002_auto_20160226_1747	2026-07-10 08:29:09.389366+00
26	django_celery_beat	0001_initial	2026-07-10 08:29:09.469179+00
27	django_celery_beat	0002_auto_20161118_0346	2026-07-10 08:29:09.528687+00
28	django_celery_beat	0003_auto_20161209_0049	2026-07-10 08:29:09.570023+00
29	django_celery_beat	0004_auto_20170221_0000	2026-07-10 08:29:09.589145+00
30	django_celery_beat	0005_add_solarschedule_events_choices	2026-07-10 08:29:09.609139+00
31	django_celery_beat	0006_auto_20180322_0932	2026-07-10 08:29:09.698243+00
32	django_celery_beat	0007_auto_20180521_0826	2026-07-10 08:29:09.760163+00
33	django_celery_beat	0008_auto_20180914_1922	2026-07-10 08:29:09.821997+00
34	django_celery_beat	0006_auto_20180210_1226	2026-07-10 08:29:09.852606+00
35	django_celery_beat	0006_periodictask_priority	2026-07-10 08:29:09.87565+00
36	django_celery_beat	0009_periodictask_headers	2026-07-10 08:29:09.907117+00
37	django_celery_beat	0010_auto_20190429_0326	2026-07-10 08:29:10.482392+00
38	django_celery_beat	0011_auto_20190508_0153	2026-07-10 08:29:10.559261+00
39	django_celery_beat	0012_periodictask_expire_seconds	2026-07-10 08:29:10.620841+00
40	django_digest	0001_initial	2026-07-10 08:29:10.727632+00
41	guardian	0002_generic_permissions_index	2026-07-10 08:29:10.840436+00
42	logger	0002_attachment_filename_length	2026-07-10 08:29:10.889899+00
43	logger	0003_add-index-on-attachment-media-file	2026-07-10 08:29:10.959562+00
44	logger	0004_increase-length-of-attachment-mimetype-field	2026-07-10 08:29:10.999255+00
45	logger	0005_instance_xml_hash	2026-07-10 08:29:11.070563+00
46	logger	0006_add_validation_status_json_field_in_instance_table	2026-07-10 08:29:11.20366+00
47	logger	0007_add_validate_permission_on_xform	2026-07-10 08:29:11.251127+00
48	logger	0008_add_instance_is_synced_with_mongo_and_xform_has_kpi_hooks	2026-07-10 08:29:11.367814+00
49	logger	0009_add_posted_to_kpi_field_to_logger_instance	2026-07-10 08:29:11.461735+00
50	logger	0010_attachment_media_file_basename	2026-07-10 08:29:11.530271+00
51	logger	0011_add-index-to-instance-uuid_and_xform_uuid	2026-07-10 08:29:11.658111+00
52	logger	0012_add_asset_uid_to_xform	2026-07-10 08:29:11.686349+00
53	logger	0013_remove_bamboo_and_ziggy_instance	2026-07-10 08:29:11.871519+00
54	logger	0014_attachment_add_media_file_size	2026-07-10 08:29:11.921512+00
55	logger	0015_add_delete_data_permission	2026-07-10 08:29:12.264689+00
56	logger	0016_remove_conflicting_view_permissions	2026-07-10 08:29:12.334929+00
57	logger	0017_remove_xform_sms	2026-07-10 08:29:12.397633+00
58	logger	0018_add_submission_counter	2026-07-10 08:29:12.453958+00
59	logger	0019_purge_deleted_instances	2026-07-10 08:29:12.520616+00
60	main	0002_auto_20160205_1915	2026-07-10 08:29:12.568484+00
61	main	0003_add_field_from_kpi_to_metadata	2026-07-10 08:29:12.595111+00
62	main	0004_drop_tokenstoragemodel_table	2026-07-10 08:29:12.641451+00
63	oauth2_provider	0001_initial	2026-07-10 08:29:10.945609+00
64	oauth2_provider	0002_auto_20190406_1805	2026-07-10 08:29:15.975993+00
65	registration	0001_initial	2026-07-10 08:29:16.037398+00
66	registration	0002_registrationprofile_activated	2026-07-10 08:29:16.086078+00
67	registration	0003_migrate_activatedstatus	2026-07-10 08:29:16.176059+00
68	registration	0004_supervisedregistrationprofile	2026-07-10 08:29:16.235562+00
69	registration	0005_activation_key_sha256	2026-07-10 08:29:16.287535+00
70	restservice	0001_initial	2026-07-10 08:29:16.398772+00
71	restservice	0002_add_related_name_with_delete_on_cascade	2026-07-10 08:29:16.479445+00
72	restservice	0003_remove_deprecated_services	2026-07-10 08:29:16.509597+00
73	reversion	0001_initial	2026-07-10 08:29:16.651749+00
74	reversion	0002_auto_20141216_1509	2026-07-10 08:29:16.658222+00
75	reversion	0003_auto_20160601_1600	2026-07-10 08:29:16.662015+00
76	reversion	0004_auto_20160611_1202	2026-07-10 08:29:16.665651+00
77	sessions	0001_initial	2026-07-10 08:29:16.711404+00
78	sites	0001_initial	2026-07-10 08:29:16.739749+00
79	sites	0002_alter_domain_unique	2026-07-10 08:29:16.762492+00
80	taggit	0003_taggeditem_add_unique_index	2026-07-10 08:29:16.797292+00
81	viewer	0001_initial	2026-07-10 08:29:17.023799+00
82	viewer	0002_auto_20160205_1915	2026-07-10 08:29:17.079618+00
83	viewer	0003_auto_20171123_1521	2026-07-10 08:29:17.116152+00
84	viewer	0004_update_meta_data_export_types	2026-07-10 08:29:17.142855+00
85	reversion	0001_squashed_0004_auto_20160611_1202	2026-07-10 08:29:17.1515+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
\.


--
-- Data for Name: django_site; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.django_site (id, domain, name) FROM stdin;
1	example.com	example.com
\.


--
-- Data for Name: guardian_groupobjectpermission; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.guardian_groupobjectpermission (id, object_pk, content_type_id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: guardian_userobjectpermission; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.guardian_userobjectpermission (id, object_pk, content_type_id, permission_id, user_id) FROM stdin;
\.


--
-- Data for Name: logger_attachment; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_attachment (id, media_file, mimetype, instance_id, media_file_basename, media_file_size) FROM stdin;
\.


--
-- Data for Name: logger_instance; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_instance (id, json, xml, date_created, date_modified, deleted_at, status, uuid, geom, survey_type_id, user_id, xform_id, xml_hash, validation_status, is_synced_with_mongo, posted_to_kpi) FROM stdin;
\.


--
-- Data for Name: logger_instancehistory; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_instancehistory (id, xml, uuid, date_created, date_modified, xform_instance_id) FROM stdin;
\.


--
-- Data for Name: logger_note; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_note (id, note, date_created, date_modified, instance_id) FROM stdin;
\.


--
-- Data for Name: logger_submissioncounter; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_submissioncounter (id, count, "timestamp", user_id) FROM stdin;
\.


--
-- Data for Name: logger_surveytype; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_surveytype (id, slug) FROM stdin;
\.


--
-- Data for Name: logger_xform; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.logger_xform (id, xls, json, description, xml, require_auth, shared, shared_data, downloadable, encrypted, id_string, title, date_created, date_modified, last_submission_time, has_start_time, uuid, instances_with_geopoints, num_of_submissions, user_id, has_kpi_hooks, kpi_asset_uid) FROM stdin;
\.


--
-- Data for Name: main_metadata; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.main_metadata (id, data_type, data_value, data_file, data_file_type, file_hash, xform_id, from_kpi) FROM stdin;
\.


--
-- Data for Name: main_userprofile; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.main_userprofile (id, name, city, country, organization, home_page, twitter, description, require_auth, address, phonenumber, num_of_submissions, metadata, created_by_id, user_id) FROM stdin;
\.


--
-- Data for Name: oauth2_provider_accesstoken; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.oauth2_provider_accesstoken (id, token, expires, scope, application_id, user_id, created, updated, source_refresh_token_id) FROM stdin;
\.


--
-- Data for Name: oauth2_provider_application; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.oauth2_provider_application (id, client_id, redirect_uris, client_type, authorization_grant_type, client_secret, name, user_id, skip_authorization, created, updated) FROM stdin;
\.


--
-- Data for Name: oauth2_provider_grant; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.oauth2_provider_grant (id, code, expires, redirect_uri, scope, application_id, user_id, created, updated, code_challenge, code_challenge_method) FROM stdin;
\.


--
-- Data for Name: oauth2_provider_refreshtoken; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.oauth2_provider_refreshtoken (id, token, access_token_id, application_id, user_id, created, updated, revoked) FROM stdin;
\.


--
-- Data for Name: registration_registrationprofile; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.registration_registrationprofile (id, activation_key, user_id, activated) FROM stdin;
\.


--
-- Data for Name: registration_supervisedregistrationprofile; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.registration_supervisedregistrationprofile (registrationprofile_ptr_id) FROM stdin;
\.


--
-- Data for Name: restservice_restservice; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.restservice_restservice (id, service_url, name, xform_id) FROM stdin;
\.


--
-- Data for Name: reversion_revision; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.reversion_revision (id, date_created, comment, user_id) FROM stdin;
\.


--
-- Data for Name: reversion_version; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.reversion_version (id, object_id, format, serialized_data, object_repr, content_type_id, revision_id, db) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: taggit_tag; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.taggit_tag (id, name, slug) FROM stdin;
\.


--
-- Data for Name: taggit_taggeditem; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.taggit_taggeditem (id, object_id, content_type_id, tag_id) FROM stdin;
\.


--
-- Data for Name: viewer_columnrename; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.viewer_columnrename (id, xpath, column_name) FROM stdin;
\.


--
-- Data for Name: viewer_export; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.viewer_export (id, created_on, filename, filedir, export_type, task_id, time_of_last_submission, internal_status, export_url, xform_id) FROM stdin;
\.


--
-- Data for Name: viewer_instancemodification; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.viewer_instancemodification (id, action, xpath, date_created, date_modified, instance_id, user_id) FROM stdin;
\.


--
-- Data for Name: viewer_parsedinstance; Type: TABLE DATA; Schema: public; Owner: kobo
--

COPY public.viewer_parsedinstance (id, start_time, end_time, lat, lng, instance_id) FROM stdin;
\.


--
-- Data for Name: geocode_settings; Type: TABLE DATA; Schema: tiger; Owner: kobo
--

COPY tiger.geocode_settings (name, setting, unit, category, short_desc) FROM stdin;
\.


--
-- Data for Name: pagc_gaz; Type: TABLE DATA; Schema: tiger; Owner: kobo
--

COPY tiger.pagc_gaz (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_lex; Type: TABLE DATA; Schema: tiger; Owner: kobo
--

COPY tiger.pagc_lex (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_rules; Type: TABLE DATA; Schema: tiger; Owner: kobo
--

COPY tiger.pagc_rules (id, rule, is_custom) FROM stdin;
\.


--
-- Data for Name: topology; Type: TABLE DATA; Schema: topology; Owner: kobo
--

COPY topology.topology (id, name, srid, "precision", hasz) FROM stdin;
\.


--
-- Data for Name: layer; Type: TABLE DATA; Schema: topology; Owner: kobo
--

COPY topology.layer (topology_id, layer_id, schema_name, table_name, feature_column, feature_type, level, child_id) FROM stdin;
\.


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 191, true);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.auth_user_groups_id_seq', 1, false);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 1, false);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 38, true);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 1, false);


--
-- Name: django_celery_beat_clockedschedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_celery_beat_clockedschedule_id_seq', 1, false);


--
-- Name: django_celery_beat_crontabschedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_celery_beat_crontabschedule_id_seq', 1, true);


--
-- Name: django_celery_beat_intervalschedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_celery_beat_intervalschedule_id_seq', 1, true);


--
-- Name: django_celery_beat_periodictask_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_celery_beat_periodictask_id_seq', 2, true);


--
-- Name: django_celery_beat_solarschedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_celery_beat_solarschedule_id_seq', 1, false);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 46, true);


--
-- Name: django_digest_partialdigest_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_digest_partialdigest_id_seq', 1, false);


--
-- Name: django_digest_usernonce_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_digest_usernonce_id_seq', 1, false);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 85, true);


--
-- Name: django_site_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.django_site_id_seq', 1, true);


--
-- Name: guardian_groupobjectpermission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.guardian_groupobjectpermission_id_seq', 1, false);


--
-- Name: guardian_userobjectpermission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.guardian_userobjectpermission_id_seq', 1, false);


--
-- Name: logger_attachment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_attachment_id_seq', 1, false);


--
-- Name: logger_instance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_instance_id_seq', 1, false);


--
-- Name: logger_instancehistory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_instancehistory_id_seq', 1, false);


--
-- Name: logger_note_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_note_id_seq', 1, false);


--
-- Name: logger_submissioncounter_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_submissioncounter_id_seq', 1, false);


--
-- Name: logger_surveytype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_surveytype_id_seq', 1, false);


--
-- Name: logger_xform_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.logger_xform_id_seq', 1, false);


--
-- Name: main_metadata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.main_metadata_id_seq', 1, false);


--
-- Name: main_userprofile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.main_userprofile_id_seq', 1, false);


--
-- Name: oauth2_provider_accesstoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.oauth2_provider_accesstoken_id_seq', 1, false);


--
-- Name: oauth2_provider_application_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.oauth2_provider_application_id_seq', 1, false);


--
-- Name: oauth2_provider_grant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.oauth2_provider_grant_id_seq', 1, false);


--
-- Name: oauth2_provider_refreshtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.oauth2_provider_refreshtoken_id_seq', 1, false);


--
-- Name: registration_registrationprofile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.registration_registrationprofile_id_seq', 1, false);


--
-- Name: restservice_restservice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.restservice_restservice_id_seq', 1, false);


--
-- Name: reversion_revision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.reversion_revision_id_seq', 1, false);


--
-- Name: reversion_version_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.reversion_version_id_seq', 1, false);


--
-- Name: taggit_tag_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.taggit_tag_id_seq', 1, false);


--
-- Name: taggit_taggeditem_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.taggit_taggeditem_id_seq', 1, false);


--
-- Name: viewer_columnrename_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.viewer_columnrename_id_seq', 1, false);


--
-- Name: viewer_export_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.viewer_export_id_seq', 1, false);


--
-- Name: viewer_instancemodification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.viewer_instancemodification_id_seq', 1, false);


--
-- Name: viewer_parsedinstance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: kobo
--

SELECT pg_catalog.setval('public.viewer_parsedinstance_id_seq', 1, false);


--
-- Name: topology_id_seq; Type: SEQUENCE SET; Schema: topology; Owner: kobo
--

SELECT pg_catalog.setval('topology.topology_id_seq', 1, false);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_clockedschedule django_celery_beat_clockedschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_clockedschedule
    ADD CONSTRAINT django_celery_beat_clockedschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_crontabschedule django_celery_beat_crontabschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_crontabschedule
    ADD CONSTRAINT django_celery_beat_crontabschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_intervalschedule django_celery_beat_intervalschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_intervalschedule
    ADD CONSTRAINT django_celery_beat_intervalschedule_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_periodictask django_celery_beat_periodictask_name_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_periodictask_name_key UNIQUE (name);


--
-- Name: django_celery_beat_periodictask django_celery_beat_periodictask_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_periodictask_pkey PRIMARY KEY (id);


--
-- Name: django_celery_beat_periodictasks django_celery_beat_periodictasks_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictasks
    ADD CONSTRAINT django_celery_beat_periodictasks_pkey PRIMARY KEY (ident);


--
-- Name: django_celery_beat_solarschedule django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_solarschedule
    ADD CONSTRAINT django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq UNIQUE (event, latitude, longitude);


--
-- Name: django_celery_beat_solarschedule django_celery_beat_solarschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_solarschedule
    ADD CONSTRAINT django_celery_beat_solarschedule_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_digest_partialdigest django_digest_partialdigest_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_partialdigest
    ADD CONSTRAINT django_digest_partialdigest_pkey PRIMARY KEY (id);


--
-- Name: django_digest_usernonce django_digest_usernonce_nonce_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_usernonce
    ADD CONSTRAINT django_digest_usernonce_nonce_key UNIQUE (nonce);


--
-- Name: django_digest_usernonce django_digest_usernonce_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_usernonce
    ADD CONSTRAINT django_digest_usernonce_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: django_site django_site_domain_a2e37b91_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_site
    ADD CONSTRAINT django_site_domain_a2e37b91_uniq UNIQUE (domain);


--
-- Name: django_site django_site_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_site
    ADD CONSTRAINT django_site_pkey PRIMARY KEY (id);


--
-- Name: guardian_groupobjectpermission guardian_groupobjectperm_group_id_permission_id_o_3f189f7c_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobjectperm_group_id_permission_id_o_3f189f7c_uniq UNIQUE (group_id, permission_id, object_pk);


--
-- Name: guardian_groupobjectpermission guardian_groupobjectpermission_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobjectpermission_pkey PRIMARY KEY (id);


--
-- Name: guardian_userobjectpermission guardian_userobjectpermi_user_id_permission_id_ob_b0b3d2fc_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectpermi_user_id_permission_id_ob_b0b3d2fc_uniq UNIQUE (user_id, permission_id, object_pk);


--
-- Name: guardian_userobjectpermission guardian_userobjectpermission_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectpermission_pkey PRIMARY KEY (id);


--
-- Name: logger_attachment logger_attachment_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_attachment
    ADD CONSTRAINT logger_attachment_pkey PRIMARY KEY (id);


--
-- Name: logger_instance logger_instance_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instance
    ADD CONSTRAINT logger_instance_pkey PRIMARY KEY (id);


--
-- Name: logger_instancehistory logger_instancehistory_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instancehistory
    ADD CONSTRAINT logger_instancehistory_pkey PRIMARY KEY (id);


--
-- Name: logger_note logger_note_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_note
    ADD CONSTRAINT logger_note_pkey PRIMARY KEY (id);


--
-- Name: logger_submissioncounter logger_submissioncounter_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_submissioncounter
    ADD CONSTRAINT logger_submissioncounter_pkey PRIMARY KEY (id);


--
-- Name: logger_surveytype logger_surveytype_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_surveytype
    ADD CONSTRAINT logger_surveytype_pkey PRIMARY KEY (id);


--
-- Name: logger_surveytype logger_surveytype_slug_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_surveytype
    ADD CONSTRAINT logger_surveytype_slug_key UNIQUE (slug);


--
-- Name: logger_xform logger_xform_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_xform
    ADD CONSTRAINT logger_xform_pkey PRIMARY KEY (id);


--
-- Name: logger_xform logger_xform_user_id_id_string_72e5fbf8_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_xform
    ADD CONSTRAINT logger_xform_user_id_id_string_72e5fbf8_uniq UNIQUE (user_id, id_string);


--
-- Name: main_metadata main_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_metadata
    ADD CONSTRAINT main_metadata_pkey PRIMARY KEY (id);


--
-- Name: main_metadata main_metadata_xform_id_data_type_data_value_fd327038_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_metadata
    ADD CONSTRAINT main_metadata_xform_id_data_type_data_value_fd327038_uniq UNIQUE (xform_id, data_type, data_value);


--
-- Name: main_userprofile main_userprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_userprofile
    ADD CONSTRAINT main_userprofile_pkey PRIMARY KEY (id);


--
-- Name: main_userprofile main_userprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_userprofile
    ADD CONSTRAINT main_userprofile_user_id_key UNIQUE (user_id);


--
-- Name: oauth2_provider_accesstoken oauth2_provider_accesstoken_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken
    ADD CONSTRAINT oauth2_provider_accesstoken_pkey PRIMARY KEY (id);


--
-- Name: oauth2_provider_accesstoken oauth2_provider_accesstoken_source_refresh_token_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken
    ADD CONSTRAINT oauth2_provider_accesstoken_source_refresh_token_id_key UNIQUE (source_refresh_token_id);


--
-- Name: oauth2_provider_accesstoken oauth2_provider_accesstoken_token_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken
    ADD CONSTRAINT oauth2_provider_accesstoken_token_key UNIQUE (token);


--
-- Name: oauth2_provider_application oauth2_provider_application_client_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_application
    ADD CONSTRAINT oauth2_provider_application_client_id_key UNIQUE (client_id);


--
-- Name: oauth2_provider_application oauth2_provider_application_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_application
    ADD CONSTRAINT oauth2_provider_application_pkey PRIMARY KEY (id);


--
-- Name: oauth2_provider_grant oauth2_provider_grant_code_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_grant
    ADD CONSTRAINT oauth2_provider_grant_code_key UNIQUE (code);


--
-- Name: oauth2_provider_grant oauth2_provider_grant_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_grant
    ADD CONSTRAINT oauth2_provider_grant_pkey PRIMARY KEY (id);


--
-- Name: oauth2_provider_refreshtoken oauth2_provider_refreshtoken_access_token_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken
    ADD CONSTRAINT oauth2_provider_refreshtoken_access_token_id_key UNIQUE (access_token_id);


--
-- Name: oauth2_provider_refreshtoken oauth2_provider_refreshtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken
    ADD CONSTRAINT oauth2_provider_refreshtoken_pkey PRIMARY KEY (id);


--
-- Name: oauth2_provider_refreshtoken oauth2_provider_refreshtoken_token_revoked_af8a5134_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken
    ADD CONSTRAINT oauth2_provider_refreshtoken_token_revoked_af8a5134_uniq UNIQUE (token, revoked);


--
-- Name: registration_registrationprofile registration_registrationprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.registration_registrationprofile
    ADD CONSTRAINT registration_registrationprofile_pkey PRIMARY KEY (id);


--
-- Name: registration_registrationprofile registration_registrationprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.registration_registrationprofile
    ADD CONSTRAINT registration_registrationprofile_user_id_key UNIQUE (user_id);


--
-- Name: registration_supervisedregistrationprofile registration_supervisedregistrationprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.registration_supervisedregistrationprofile
    ADD CONSTRAINT registration_supervisedregistrationprofile_pkey PRIMARY KEY (registrationprofile_ptr_id);


--
-- Name: restservice_restservice restservice_restservice_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.restservice_restservice
    ADD CONSTRAINT restservice_restservice_pkey PRIMARY KEY (id);


--
-- Name: restservice_restservice restservice_restservice_service_url_xform_id_name_bef535b2_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.restservice_restservice
    ADD CONSTRAINT restservice_restservice_service_url_xform_id_name_bef535b2_uniq UNIQUE (service_url, xform_id, name);


--
-- Name: reversion_revision reversion_revision_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_revision
    ADD CONSTRAINT reversion_revision_pkey PRIMARY KEY (id);


--
-- Name: reversion_version reversion_version_db_content_type_id_objec_b2c54f65_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_version
    ADD CONSTRAINT reversion_version_db_content_type_id_objec_b2c54f65_uniq UNIQUE (db, content_type_id, object_id, revision_id);


--
-- Name: reversion_version reversion_version_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_version
    ADD CONSTRAINT reversion_version_pkey PRIMARY KEY (id);


--
-- Name: taggit_tag taggit_tag_name_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_tag
    ADD CONSTRAINT taggit_tag_name_key UNIQUE (name);


--
-- Name: taggit_tag taggit_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_tag
    ADD CONSTRAINT taggit_tag_pkey PRIMARY KEY (id);


--
-- Name: taggit_tag taggit_tag_slug_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_tag
    ADD CONSTRAINT taggit_tag_slug_key UNIQUE (slug);


--
-- Name: taggit_taggeditem taggit_taggeditem_content_type_id_object_i_4bb97a8e_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_taggeditem
    ADD CONSTRAINT taggit_taggeditem_content_type_id_object_i_4bb97a8e_uniq UNIQUE (content_type_id, object_id, tag_id);


--
-- Name: taggit_taggeditem taggit_taggeditem_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_taggeditem
    ADD CONSTRAINT taggit_taggeditem_pkey PRIMARY KEY (id);


--
-- Name: viewer_columnrename viewer_columnrename_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_columnrename
    ADD CONSTRAINT viewer_columnrename_pkey PRIMARY KEY (id);


--
-- Name: viewer_columnrename viewer_columnrename_xpath_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_columnrename
    ADD CONSTRAINT viewer_columnrename_xpath_key UNIQUE (xpath);


--
-- Name: viewer_export viewer_export_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_export
    ADD CONSTRAINT viewer_export_pkey PRIMARY KEY (id);


--
-- Name: viewer_export viewer_export_xform_id_filename_c38e6b2d_uniq; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_export
    ADD CONSTRAINT viewer_export_xform_id_filename_c38e6b2d_uniq UNIQUE (xform_id, filename);


--
-- Name: viewer_instancemodification viewer_instancemodification_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_instancemodification
    ADD CONSTRAINT viewer_instancemodification_pkey PRIMARY KEY (id);


--
-- Name: viewer_parsedinstance viewer_parsedinstance_instance_id_key; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_parsedinstance
    ADD CONSTRAINT viewer_parsedinstance_instance_id_key UNIQUE (instance_id);


--
-- Name: viewer_parsedinstance viewer_parsedinstance_pkey; Type: CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_parsedinstance
    ADD CONSTRAINT viewer_parsedinstance_pkey PRIMARY KEY (id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_celery_beat_periodictask_clocked_id_47a69f82; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_celery_beat_periodictask_clocked_id_47a69f82 ON public.django_celery_beat_periodictask USING btree (clocked_id);


--
-- Name: django_celery_beat_periodictask_crontab_id_d3cba168; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_celery_beat_periodictask_crontab_id_d3cba168 ON public.django_celery_beat_periodictask USING btree (crontab_id);


--
-- Name: django_celery_beat_periodictask_interval_id_a8ca27da; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_celery_beat_periodictask_interval_id_a8ca27da ON public.django_celery_beat_periodictask USING btree (interval_id);


--
-- Name: django_celery_beat_periodictask_name_265a36b7_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_celery_beat_periodictask_name_265a36b7_like ON public.django_celery_beat_periodictask USING btree (name varchar_pattern_ops);


--
-- Name: django_celery_beat_periodictask_solar_id_a87ce72c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_celery_beat_periodictask_solar_id_a87ce72c ON public.django_celery_beat_periodictask USING btree (solar_id);


--
-- Name: django_digest_partialdigest_login_7e0a27ae; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_digest_partialdigest_login_7e0a27ae ON public.django_digest_partialdigest USING btree (login);


--
-- Name: django_digest_partialdigest_login_7e0a27ae_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_digest_partialdigest_login_7e0a27ae_like ON public.django_digest_partialdigest USING btree (login varchar_pattern_ops);


--
-- Name: django_digest_partialdigest_user_id_b2be56d6; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_digest_partialdigest_user_id_b2be56d6 ON public.django_digest_partialdigest USING btree (user_id);


--
-- Name: django_digest_usernonce_nonce_1d44c3d9_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_digest_usernonce_nonce_1d44c3d9_like ON public.django_digest_usernonce USING btree (nonce varchar_pattern_ops);


--
-- Name: django_digest_usernonce_user_id_34b0f1e4; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_digest_usernonce_user_id_34b0f1e4 ON public.django_digest_usernonce USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: django_site_domain_a2e37b91_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX django_site_domain_a2e37b91_like ON public.django_site USING btree (domain varchar_pattern_ops);


--
-- Name: guardian_gr_content_ae6aec_idx; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_gr_content_ae6aec_idx ON public.guardian_groupobjectpermission USING btree (content_type_id, object_pk);


--
-- Name: guardian_groupobjectpermission_content_type_id_7ade36b8; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_groupobjectpermission_content_type_id_7ade36b8 ON public.guardian_groupobjectpermission USING btree (content_type_id);


--
-- Name: guardian_groupobjectpermission_group_id_4bbbfb62; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_groupobjectpermission_group_id_4bbbfb62 ON public.guardian_groupobjectpermission USING btree (group_id);


--
-- Name: guardian_groupobjectpermission_permission_id_36572738; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_groupobjectpermission_permission_id_36572738 ON public.guardian_groupobjectpermission USING btree (permission_id);


--
-- Name: guardian_us_content_179ed2_idx; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_us_content_179ed2_idx ON public.guardian_userobjectpermission USING btree (content_type_id, object_pk);


--
-- Name: guardian_userobjectpermission_content_type_id_2e892405; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_userobjectpermission_content_type_id_2e892405 ON public.guardian_userobjectpermission USING btree (content_type_id);


--
-- Name: guardian_userobjectpermission_permission_id_71807bfc; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_userobjectpermission_permission_id_71807bfc ON public.guardian_userobjectpermission USING btree (permission_id);


--
-- Name: guardian_userobjectpermission_user_id_d5c1e964; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX guardian_userobjectpermission_user_id_d5c1e964 ON public.guardian_userobjectpermission USING btree (user_id);


--
-- Name: logger_attachment_instance_id_780c30f1; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_attachment_instance_id_780c30f1 ON public.logger_attachment USING btree (instance_id);


--
-- Name: logger_attachment_media_file_18cea505; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_attachment_media_file_18cea505 ON public.logger_attachment USING btree (media_file);


--
-- Name: logger_attachment_media_file_18cea505_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_attachment_media_file_18cea505_like ON public.logger_attachment USING btree (media_file varchar_pattern_ops);


--
-- Name: logger_attachment_media_file_basename_164242ca; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_attachment_media_file_basename_164242ca ON public.logger_attachment USING btree (media_file_basename);


--
-- Name: logger_attachment_media_file_basename_164242ca_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_attachment_media_file_basename_164242ca_like ON public.logger_attachment USING btree (media_file_basename varchar_pattern_ops);


--
-- Name: logger_instance_geom_id; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_geom_id ON public.logger_instance USING gist (geom);


--
-- Name: logger_instance_survey_type_id_eb7f102c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_survey_type_id_eb7f102c ON public.logger_instance USING btree (survey_type_id);


--
-- Name: logger_instance_user_id_af74680c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_user_id_af74680c ON public.logger_instance USING btree (user_id);


--
-- Name: logger_instance_uuid_9b502899; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_uuid_9b502899 ON public.logger_instance USING btree (uuid);


--
-- Name: logger_instance_uuid_9b502899_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_uuid_9b502899_like ON public.logger_instance USING btree (uuid varchar_pattern_ops);


--
-- Name: logger_instance_xform_id_ebcfcca3; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_xform_id_ebcfcca3 ON public.logger_instance USING btree (xform_id);


--
-- Name: logger_instance_xml_hash_7b018af4; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_xml_hash_7b018af4 ON public.logger_instance USING btree (xml_hash);


--
-- Name: logger_instance_xml_hash_7b018af4_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instance_xml_hash_7b018af4_like ON public.logger_instance USING btree (xml_hash varchar_pattern_ops);


--
-- Name: logger_instancehistory_xform_instance_id_b64256cc; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_instancehistory_xform_instance_id_b64256cc ON public.logger_instancehistory USING btree (xform_instance_id);


--
-- Name: logger_note_instance_id_9526aca3; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_note_instance_id_9526aca3 ON public.logger_note USING btree (instance_id);


--
-- Name: logger_submissioncounter_user_id_cd2aa59c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_submissioncounter_user_id_cd2aa59c ON public.logger_submissioncounter USING btree (user_id);


--
-- Name: logger_surveytype_slug_33269157_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_surveytype_slug_33269157_like ON public.logger_surveytype USING btree (slug varchar_pattern_ops);


--
-- Name: logger_xform_id_string_267b9795; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_xform_id_string_267b9795 ON public.logger_xform USING btree (id_string);


--
-- Name: logger_xform_id_string_267b9795_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_xform_id_string_267b9795_like ON public.logger_xform USING btree (id_string varchar_pattern_ops);


--
-- Name: logger_xform_user_id_bc44bbd4; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_xform_user_id_bc44bbd4 ON public.logger_xform USING btree (user_id);


--
-- Name: logger_xform_uuid_5a0c2524; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_xform_uuid_5a0c2524 ON public.logger_xform USING btree (uuid);


--
-- Name: logger_xform_uuid_5a0c2524_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX logger_xform_uuid_5a0c2524_like ON public.logger_xform USING btree (uuid varchar_pattern_ops);


--
-- Name: main_metadata_xform_id_a4a4df7b; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX main_metadata_xform_id_a4a4df7b ON public.main_metadata USING btree (xform_id);


--
-- Name: main_userprofile_created_by_id_c4fdbaa8; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX main_userprofile_created_by_id_c4fdbaa8 ON public.main_userprofile USING btree (created_by_id);


--
-- Name: oauth2_provider_accesstoken_application_id_b22886e1; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_accesstoken_application_id_b22886e1 ON public.oauth2_provider_accesstoken USING btree (application_id);


--
-- Name: oauth2_provider_accesstoken_token_8af090f8_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_accesstoken_token_8af090f8_like ON public.oauth2_provider_accesstoken USING btree (token varchar_pattern_ops);


--
-- Name: oauth2_provider_accesstoken_user_id_6e4c9a65; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_accesstoken_user_id_6e4c9a65 ON public.oauth2_provider_accesstoken USING btree (user_id);


--
-- Name: oauth2_provider_application_client_id_03f0cc84_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_application_client_id_03f0cc84_like ON public.oauth2_provider_application USING btree (client_id varchar_pattern_ops);


--
-- Name: oauth2_provider_application_client_secret_53133678; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_application_client_secret_53133678 ON public.oauth2_provider_application USING btree (client_secret);


--
-- Name: oauth2_provider_application_client_secret_53133678_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_application_client_secret_53133678_like ON public.oauth2_provider_application USING btree (client_secret varchar_pattern_ops);


--
-- Name: oauth2_provider_application_user_id_79829054; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_application_user_id_79829054 ON public.oauth2_provider_application USING btree (user_id);


--
-- Name: oauth2_provider_grant_application_id_81923564; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_grant_application_id_81923564 ON public.oauth2_provider_grant USING btree (application_id);


--
-- Name: oauth2_provider_grant_code_49ab4ddf_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_grant_code_49ab4ddf_like ON public.oauth2_provider_grant USING btree (code varchar_pattern_ops);


--
-- Name: oauth2_provider_grant_user_id_e8f62af8; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_grant_user_id_e8f62af8 ON public.oauth2_provider_grant USING btree (user_id);


--
-- Name: oauth2_provider_refreshtoken_application_id_2d1c311b; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_refreshtoken_application_id_2d1c311b ON public.oauth2_provider_refreshtoken USING btree (application_id);


--
-- Name: oauth2_provider_refreshtoken_user_id_da837fce; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX oauth2_provider_refreshtoken_user_id_da837fce ON public.oauth2_provider_refreshtoken USING btree (user_id);


--
-- Name: restservice_restservice_xform_id_220bcd79; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX restservice_restservice_xform_id_220bcd79 ON public.restservice_restservice USING btree (xform_id);


--
-- Name: reversion_revision_date_created_96f7c20c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX reversion_revision_date_created_96f7c20c ON public.reversion_revision USING btree (date_created);


--
-- Name: reversion_revision_user_id_17095f45; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX reversion_revision_user_id_17095f45 ON public.reversion_revision USING btree (user_id);


--
-- Name: reversion_version_content_type_id_7d0ff25c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX reversion_version_content_type_id_7d0ff25c ON public.reversion_version USING btree (content_type_id);


--
-- Name: reversion_version_revision_id_af9f6a9d; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX reversion_version_revision_id_af9f6a9d ON public.reversion_version USING btree (revision_id);


--
-- Name: taggit_tag_name_58eb2ed9_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX taggit_tag_name_58eb2ed9_like ON public.taggit_tag USING btree (name varchar_pattern_ops);


--
-- Name: taggit_tag_slug_6be58b2c_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX taggit_tag_slug_6be58b2c_like ON public.taggit_tag USING btree (slug varchar_pattern_ops);


--
-- Name: taggit_taggeditem_content_type_id_9957a03c; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX taggit_taggeditem_content_type_id_9957a03c ON public.taggit_taggeditem USING btree (content_type_id);


--
-- Name: taggit_taggeditem_content_type_id_object_id_196cc965_idx; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX taggit_taggeditem_content_type_id_object_id_196cc965_idx ON public.taggit_taggeditem USING btree (content_type_id, object_id);


--
-- Name: taggit_taggeditem_object_id_e2d7d1df; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX taggit_taggeditem_object_id_e2d7d1df ON public.taggit_taggeditem USING btree (object_id);


--
-- Name: taggit_taggeditem_tag_id_f4f5b767; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX taggit_taggeditem_tag_id_f4f5b767 ON public.taggit_taggeditem USING btree (tag_id);


--
-- Name: viewer_columnrename_xpath_8c390aa3_like; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX viewer_columnrename_xpath_8c390aa3_like ON public.viewer_columnrename USING btree (xpath varchar_pattern_ops);


--
-- Name: viewer_export_xform_id_51550a2d; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX viewer_export_xform_id_51550a2d ON public.viewer_export USING btree (xform_id);


--
-- Name: viewer_instancemodification_instance_id_3b07ee23; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX viewer_instancemodification_instance_id_3b07ee23 ON public.viewer_instancemodification USING btree (instance_id);


--
-- Name: viewer_instancemodification_user_id_293e6bc2; Type: INDEX; Schema: public; Owner: kobo
--

CREATE INDEX viewer_instancemodification_user_id_293e6bc2 ON public.viewer_instancemodification USING btree (user_id);


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_clocked_id_47a69f82_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_clocked_id_47a69f82_fk_django_ce FOREIGN KEY (clocked_id) REFERENCES public.django_celery_beat_clockedschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_crontab_id_d3cba168_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_crontab_id_d3cba168_fk_django_ce FOREIGN KEY (crontab_id) REFERENCES public.django_celery_beat_crontabschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_interval_id_a8ca27da_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_interval_id_a8ca27da_fk_django_ce FOREIGN KEY (interval_id) REFERENCES public.django_celery_beat_intervalschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_celery_beat_periodictask django_celery_beat_p_solar_id_a87ce72c_fk_django_ce; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_celery_beat_periodictask
    ADD CONSTRAINT django_celery_beat_p_solar_id_a87ce72c_fk_django_ce FOREIGN KEY (solar_id) REFERENCES public.django_celery_beat_solarschedule(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_digest_partialdigest django_digest_partialdigest_user_id_b2be56d6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_partialdigest
    ADD CONSTRAINT django_digest_partialdigest_user_id_b2be56d6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_digest_usernonce django_digest_usernonce_user_id_34b0f1e4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.django_digest_usernonce
    ADD CONSTRAINT django_digest_usernonce_user_id_34b0f1e4_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_groupobjectpermission guardian_groupobject_content_type_id_7ade36b8_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobject_content_type_id_7ade36b8_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_groupobjectpermission guardian_groupobject_group_id_4bbbfb62_fk_auth_grou; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobject_group_id_4bbbfb62_fk_auth_grou FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_groupobjectpermission guardian_groupobject_permission_id_36572738_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_groupobjectpermission
    ADD CONSTRAINT guardian_groupobject_permission_id_36572738_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_userobjectpermission guardian_userobjectp_content_type_id_2e892405_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectp_content_type_id_2e892405_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_userobjectpermission guardian_userobjectp_permission_id_71807bfc_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectp_permission_id_71807bfc_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: guardian_userobjectpermission guardian_userobjectpermission_user_id_d5c1e964_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.guardian_userobjectpermission
    ADD CONSTRAINT guardian_userobjectpermission_user_id_d5c1e964_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_attachment logger_attachment_instance_id_780c30f1_fk_logger_instance_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_attachment
    ADD CONSTRAINT logger_attachment_instance_id_780c30f1_fk_logger_instance_id FOREIGN KEY (instance_id) REFERENCES public.logger_instance(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_instance logger_instance_survey_type_id_eb7f102c_fk_logger_surveytype_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instance
    ADD CONSTRAINT logger_instance_survey_type_id_eb7f102c_fk_logger_surveytype_id FOREIGN KEY (survey_type_id) REFERENCES public.logger_surveytype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_instance logger_instance_user_id_af74680c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instance
    ADD CONSTRAINT logger_instance_user_id_af74680c_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_instance logger_instance_xform_id_ebcfcca3_fk_logger_xform_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instance
    ADD CONSTRAINT logger_instance_xform_id_ebcfcca3_fk_logger_xform_id FOREIGN KEY (xform_id) REFERENCES public.logger_xform(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_instancehistory logger_instancehisto_xform_instance_id_b64256cc_fk_logger_in; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_instancehistory
    ADD CONSTRAINT logger_instancehisto_xform_instance_id_b64256cc_fk_logger_in FOREIGN KEY (xform_instance_id) REFERENCES public.logger_instance(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_note logger_note_instance_id_9526aca3_fk_logger_instance_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_note
    ADD CONSTRAINT logger_note_instance_id_9526aca3_fk_logger_instance_id FOREIGN KEY (instance_id) REFERENCES public.logger_instance(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_submissioncounter logger_submissioncounter_user_id_cd2aa59c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_submissioncounter
    ADD CONSTRAINT logger_submissioncounter_user_id_cd2aa59c_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: logger_xform logger_xform_user_id_bc44bbd4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.logger_xform
    ADD CONSTRAINT logger_xform_user_id_bc44bbd4_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: main_metadata main_metadata_xform_id_a4a4df7b_fk_logger_xform_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_metadata
    ADD CONSTRAINT main_metadata_xform_id_a4a4df7b_fk_logger_xform_id FOREIGN KEY (xform_id) REFERENCES public.logger_xform(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: main_userprofile main_userprofile_created_by_id_c4fdbaa8_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_userprofile
    ADD CONSTRAINT main_userprofile_created_by_id_c4fdbaa8_fk_auth_user_id FOREIGN KEY (created_by_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: main_userprofile main_userprofile_user_id_15c416f4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.main_userprofile
    ADD CONSTRAINT main_userprofile_user_id_15c416f4_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_accesstoken oauth2_provider_acce_application_id_b22886e1_fk_oauth2_pr; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken
    ADD CONSTRAINT oauth2_provider_acce_application_id_b22886e1_fk_oauth2_pr FOREIGN KEY (application_id) REFERENCES public.oauth2_provider_application(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_accesstoken oauth2_provider_acce_source_refresh_token_e66fbc72_fk_oauth2_pr; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken
    ADD CONSTRAINT oauth2_provider_acce_source_refresh_token_e66fbc72_fk_oauth2_pr FOREIGN KEY (source_refresh_token_id) REFERENCES public.oauth2_provider_refreshtoken(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_accesstoken oauth2_provider_accesstoken_user_id_6e4c9a65_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_accesstoken
    ADD CONSTRAINT oauth2_provider_accesstoken_user_id_6e4c9a65_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_application oauth2_provider_application_user_id_79829054_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_application
    ADD CONSTRAINT oauth2_provider_application_user_id_79829054_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_grant oauth2_provider_gran_application_id_81923564_fk_oauth2_pr; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_grant
    ADD CONSTRAINT oauth2_provider_gran_application_id_81923564_fk_oauth2_pr FOREIGN KEY (application_id) REFERENCES public.oauth2_provider_application(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_grant oauth2_provider_grant_user_id_e8f62af8_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_grant
    ADD CONSTRAINT oauth2_provider_grant_user_id_e8f62af8_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_refreshtoken oauth2_provider_refr_access_token_id_775e84e8_fk_oauth2_pr; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken
    ADD CONSTRAINT oauth2_provider_refr_access_token_id_775e84e8_fk_oauth2_pr FOREIGN KEY (access_token_id) REFERENCES public.oauth2_provider_accesstoken(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_refreshtoken oauth2_provider_refr_application_id_2d1c311b_fk_oauth2_pr; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken
    ADD CONSTRAINT oauth2_provider_refr_application_id_2d1c311b_fk_oauth2_pr FOREIGN KEY (application_id) REFERENCES public.oauth2_provider_application(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: oauth2_provider_refreshtoken oauth2_provider_refreshtoken_user_id_da837fce_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.oauth2_provider_refreshtoken
    ADD CONSTRAINT oauth2_provider_refreshtoken_user_id_da837fce_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: registration_registrationprofile registration_registr_user_id_5fcbf725_fk_auth_user; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.registration_registrationprofile
    ADD CONSTRAINT registration_registr_user_id_5fcbf725_fk_auth_user FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: registration_supervisedregistrationprofile registration_supervi_registrationprofile__0a59f3b2_fk_registrat; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.registration_supervisedregistrationprofile
    ADD CONSTRAINT registration_supervi_registrationprofile__0a59f3b2_fk_registrat FOREIGN KEY (registrationprofile_ptr_id) REFERENCES public.registration_registrationprofile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: restservice_restservice restservice_restservice_xform_id_220bcd79_fk_logger_xform_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.restservice_restservice
    ADD CONSTRAINT restservice_restservice_xform_id_220bcd79_fk_logger_xform_id FOREIGN KEY (xform_id) REFERENCES public.logger_xform(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: reversion_revision reversion_revision_user_id_17095f45_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_revision
    ADD CONSTRAINT reversion_revision_user_id_17095f45_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: reversion_version reversion_version_content_type_id_7d0ff25c_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_version
    ADD CONSTRAINT reversion_version_content_type_id_7d0ff25c_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: reversion_version reversion_version_revision_id_af9f6a9d_fk_reversion_revision_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.reversion_version
    ADD CONSTRAINT reversion_version_revision_id_af9f6a9d_fk_reversion_revision_id FOREIGN KEY (revision_id) REFERENCES public.reversion_revision(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: taggit_taggeditem taggit_taggeditem_content_type_id_9957a03c_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_taggeditem
    ADD CONSTRAINT taggit_taggeditem_content_type_id_9957a03c_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: taggit_taggeditem taggit_taggeditem_tag_id_f4f5b767_fk_taggit_tag_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.taggit_taggeditem
    ADD CONSTRAINT taggit_taggeditem_tag_id_f4f5b767_fk_taggit_tag_id FOREIGN KEY (tag_id) REFERENCES public.taggit_tag(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: viewer_export viewer_export_xform_id_51550a2d_fk_logger_xform_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_export
    ADD CONSTRAINT viewer_export_xform_id_51550a2d_fk_logger_xform_id FOREIGN KEY (xform_id) REFERENCES public.logger_xform(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: viewer_instancemodification viewer_instancemodif_instance_id_3b07ee23_fk_logger_in; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_instancemodification
    ADD CONSTRAINT viewer_instancemodif_instance_id_3b07ee23_fk_logger_in FOREIGN KEY (instance_id) REFERENCES public.logger_instance(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: viewer_instancemodification viewer_instancemodification_user_id_293e6bc2_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_instancemodification
    ADD CONSTRAINT viewer_instancemodification_user_id_293e6bc2_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: viewer_parsedinstance viewer_parsedinstanc_instance_id_7cccee77_fk_logger_in; Type: FK CONSTRAINT; Schema: public; Owner: kobo
--

ALTER TABLE ONLY public.viewer_parsedinstance
    ADD CONSTRAINT viewer_parsedinstanc_instance_id_7cccee77_fk_logger_in FOREIGN KEY (instance_id) REFERENCES public.logger_instance(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

