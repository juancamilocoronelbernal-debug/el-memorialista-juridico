-- El Memorialista V5: reviewed plans, durable steps and recurring assignments.
-- Browser actions are separate, single-use approvals. No user JWT is stored.
BEGIN;

CREATE TABLE IF NOT EXISTS public.despacho_agent_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    objective text NOT NULL CHECK (length(objective) BETWEEN 1 AND 12000),
    document_ids jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(document_ids)='array' AND jsonb_array_length(document_ids)<=20),
    matter_id uuid,
    playbook_id uuid,
    allowed_urls jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(allowed_urls)='array' AND jsonb_array_length(allowed_urls)<=8),
    plan jsonb NOT NULL CHECK (jsonb_typeof(plan)='array' AND jsonb_array_length(plan) BETWEEN 1 AND 8),
    plan_hash text NOT NULL CHECK (plan_hash ~ '^[0-9a-f]{64}$'),
    approved_hash text,
    approved_at timestamptz,
    state text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','approved','running','waiting_approval','completed','failed','cancelled')),
    version integer NOT NULL DEFAULT 1 CHECK (version>=1),
    cursor integer NOT NULL DEFAULT 0 CHECK (cursor BETWEEN 0 AND 8),
    results jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(results)='array' AND jsonb_array_length(results)<=8 AND octet_length(results::text)<=4000000),
    last_error text NOT NULL DEFAULT '' CHECK (length(last_error)<=1200),
    lease_token uuid,
    lease_until timestamptz,
    manual_control boolean NOT NULL DEFAULT false,
    schedule_id uuid,
    scheduled_for timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_id,id),
    UNIQUE(schedule_id,scheduled_for),
    CHECK (cursor<=jsonb_array_length(plan)),
    CHECK (jsonb_array_length(results)=cursor),
    FOREIGN KEY(owner_id,matter_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE NO ACTION DEFERRABLE INITIALLY IMMEDIATE,
    FOREIGN KEY(owner_id,playbook_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE NO ACTION DEFERRABLE INITIALLY IMMEDIATE
);
CREATE INDEX IF NOT EXISTS despacho_agent_jobs_owner ON public.despacho_agent_jobs(owner_id,created_at DESC);
CREATE INDEX IF NOT EXISTS despacho_agent_jobs_queue ON public.despacho_agent_jobs(state,lease_until,created_at) WHERE schedule_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.despacho_agent_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    at timestamptz NOT NULL DEFAULT now(),
    event text NOT NULL CHECK (length(event)<=80),
    detail jsonb NOT NULL DEFAULT '{}' CHECK (octet_length(detail::text)<=20000),
    FOREIGN KEY(owner_id,job_id) REFERENCES public.despacho_agent_jobs(owner_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS despacho_agent_events_owner ON public.despacho_agent_events(owner_id,job_id,at);

CREATE TABLE IF NOT EXISTS public.despacho_agent_schedules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    interval_minutes integer NOT NULL CHECK (interval_minutes BETWEEN 60 AND 10080),
    next_run_at timestamptz NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    version integer NOT NULL DEFAULT 1,
    last_run_at timestamptz,
    last_job_id uuid,
    last_error text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_id,id),
    FOREIGN KEY(owner_id,job_id) REFERENCES public.despacho_agent_jobs(owner_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS despacho_agent_schedules_due ON public.despacho_agent_schedules(next_run_at) WHERE enabled;

CREATE TABLE IF NOT EXISTS public.despacho_agent_browser_actions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    session_id uuid NOT NULL,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','executing','completed','failed','expired')),
    action jsonb NOT NULL CHECK (octet_length(action::text)<=12000),
    page_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    result jsonb NOT NULL DEFAULT '{}' CHECK (octet_length(result::text)<=100000),
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    FOREIGN KEY(owner_id,job_id) REFERENCES public.despacho_agent_jobs(owner_id,id) ON DELETE CASCADE
);

ALTER TABLE public.despacho_agent_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_agent_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_agent_browser_actions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_agent_jobs,public.despacho_agent_events,public.despacho_agent_schedules,public.despacho_agent_browser_actions FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.despacho_agent_jobs,public.despacho_agent_events,public.despacho_agent_schedules TO authenticated;
GRANT ALL ON public.despacho_agent_jobs,public.despacho_agent_events,public.despacho_agent_schedules,public.despacho_agent_browser_actions TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.despacho_agent_events_id_seq TO service_role;
DROP POLICY IF EXISTS agent_job_owner ON public.despacho_agent_jobs;
CREATE POLICY agent_job_owner ON public.despacho_agent_jobs FOR SELECT TO authenticated USING(owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS agent_events_owner ON public.despacho_agent_events;
CREATE POLICY agent_events_owner ON public.despacho_agent_events FOR SELECT TO authenticated USING(owner_id=(SELECT auth.uid()));
DROP POLICY IF EXISTS agent_schedule_owner ON public.despacho_agent_schedules;
CREATE POLICY agent_schedule_owner ON public.despacho_agent_schedules FOR SELECT TO authenticated USING(owner_id=(SELECT auth.uid()));

CREATE OR REPLACE FUNCTION public.despacho_agent_job_audit()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail)
    VALUES(NEW.owner_id,NEW.id,CASE WHEN TG_OP='INSERT' THEN 'plan_created' ELSE 'state_changed' END,
      jsonb_build_object('state',NEW.state,'cursor',NEW.cursor,'version',NEW.version,'plan_hash',NEW.plan_hash,'error',NEW.last_error));
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.despacho_agent_job_audit() FROM PUBLIC,anon,authenticated;
DROP TRIGGER IF EXISTS despacho_agent_job_audit ON public.despacho_agent_jobs;
CREATE TRIGGER despacho_agent_job_audit AFTER INSERT OR UPDATE ON public.despacho_agent_jobs FOR EACH ROW EXECUTE FUNCTION public.despacho_agent_job_audit();

CREATE OR REPLACE FUNCTION public.despacho_agent_control(p_owner uuid,p_id uuid,p_version integer,p_action text,p_data jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; plan_new jsonb;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_id AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.version<>p_version THEN RAISE EXCEPTION 'stale job' USING ERRCODE='40001'; END IF;
    IF p_action='edit' THEN
        IF j.state<>'draft' THEN RAISE EXCEPTION 'approved plans are immutable' USING ERRCODE='55000'; END IF;
        plan_new=p_data->'plan';
        IF jsonb_typeof(plan_new)<>'array' OR jsonb_array_length(plan_new) NOT BETWEEN 1 AND 8 THEN RAISE EXCEPTION 'invalid plan' USING ERRCODE='22023'; END IF;
        UPDATE public.despacho_agent_jobs SET plan=plan_new,plan_hash=p_data->>'plan_hash',approved_hash=NULL,approved_at=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSIF p_action='approve' THEN
        IF j.state<>'draft' THEN RAISE EXCEPTION 'not a draft' USING ERRCODE='55000'; END IF;
        UPDATE public.despacho_agent_jobs SET state='approved',approved_hash=plan_hash,approved_at=now(),version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSIF p_action='cancel' THEN
        IF j.state IN ('completed','cancelled') THEN RETURN to_jsonb(j); END IF;
        UPDATE public.despacho_agent_jobs SET state='cancelled',manual_control=false,lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
        UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_id AND owner_id=p_owner AND state='pending';
    ELSIF p_action='retry' THEN
        IF NOT (j.state='failed' OR (j.state='running' AND j.lease_until<now())) OR j.approved_hash IS DISTINCT FROM j.plan_hash THEN
            RAISE EXCEPTION 'not recoverable' USING ERRCODE='55000';
        END IF;
        UPDATE public.despacho_agent_jobs SET state='approved',last_error='',lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSE RAISE EXCEPTION 'invalid action' USING ERRCODE='22023'; END IF;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_claim_step(p_owner uuid,p_id uuid,p_version integer,p_lease uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_id AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.version<>p_version OR j.state NOT IN ('approved','running') OR j.manual_control OR j.cursor>=jsonb_array_length(j.plan)
       OR j.approved_hash IS DISTINCT FROM j.plan_hash OR (j.lease_until IS NOT NULL AND j.lease_until>now()) THEN
        RAISE EXCEPTION 'claim conflict' USING ERRCODE='40001';
    END IF;
    UPDATE public.despacho_agent_jobs SET state='running',lease_token=p_lease,lease_until=now()+interval '300 seconds',version=version+1,updated_at=now(),last_error='' WHERE id=p_id RETURNING * INTO j;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_finish_step(p_owner uuid,p_id uuid,p_lease uuid,p_cursor integer,p_result jsonb,p_error text DEFAULT '')
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_id AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'missing job' USING ERRCODE='40001'; END IF;
    IF j.state='cancelled' THEN RETURN to_jsonb(j); END IF;
    IF j.lease_token IS DISTINCT FROM p_lease OR j.cursor<>p_cursor OR j.state<>'running' THEN RAISE EXCEPTION 'stale completion' USING ERRCODE='40001'; END IF;
    IF p_error<>'' THEN
        UPDATE public.despacho_agent_jobs SET state='failed',last_error=left(p_error,1200),lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    ELSE
        IF p_result->>'step_id' IS DISTINCT FROM (j.plan->p_cursor)->>'id' OR p_result->>'tool' IS DISTINCT FROM (j.plan->p_cursor)->>'tool' THEN
            RAISE EXCEPTION 'wrong step result' USING ERRCODE='22023';
        END IF;
        UPDATE public.despacho_agent_jobs SET cursor=cursor+1,results=results||jsonb_build_array(p_result),state=CASE WHEN cursor+1=jsonb_array_length(plan) THEN 'completed' ELSE 'approved' END,
            last_error='',lease_token=NULL,lease_until=NULL,version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO j;
    END IF;
    IF j.schedule_id IS NOT NULL THEN UPDATE public.despacho_agent_schedules SET last_error=j.last_error,updated_at=now() WHERE id=j.schedule_id AND owner_id=p_owner; END IF;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_schedule_create(p_owner uuid,p_job uuid,p_interval integer,p_next timestamptz,p_enabled boolean DEFAULT true)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; s public.despacho_agent_schedules;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('agent-schedule:'||p_owner::text,0));
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE owner_id=p_owner AND id=p_job;
    IF NOT FOUND OR j.approved_hash IS DISTINCT FROM j.plan_hash OR j.state IN ('draft','cancelled','waiting_approval') THEN RAISE EXCEPTION 'not approved' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM jsonb_array_elements(j.plan) e WHERE e->>'tool' NOT IN ('read_documents','research','analyze','draft','timeline','fetch_source','save_document')) THEN
        RAISE EXCEPTION 'unsafe recurring tool' USING ERRCODE='22023'; END IF;
    IF (SELECT count(*) FROM public.despacho_agent_schedules WHERE owner_id=p_owner)>=10 THEN RAISE EXCEPTION 'schedule quota' USING ERRCODE='23514'; END IF;
    IF p_interval NOT BETWEEN 60 AND 10080 OR p_next<now()-interval '1 minute' THEN RAISE EXCEPTION 'invalid schedule' USING ERRCODE='22023'; END IF;
    INSERT INTO public.despacho_agent_schedules(owner_id,job_id,title,interval_minutes,next_run_at,enabled) VALUES(p_owner,p_job,j.title,p_interval,p_next,p_enabled) RETURNING * INTO s;
    RETURN to_jsonb(s);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_schedule_update(p_owner uuid,p_id uuid,p_version integer,p_data jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE s public.despacho_agent_schedules;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO s FROM public.despacho_agent_schedules WHERE owner_id=p_owner AND id=p_id FOR UPDATE;
    IF NOT FOUND OR s.version<>p_version THEN RAISE EXCEPTION 'stale schedule' USING ERRCODE='40001'; END IF;
    UPDATE public.despacho_agent_schedules SET enabled=CASE WHEN p_data?'enabled' THEN (p_data->>'enabled')::boolean ELSE enabled END,
        interval_minutes=CASE WHEN p_data?'interval_minutes' THEN (p_data->>'interval_minutes')::integer ELSE interval_minutes END,
        next_run_at=CASE WHEN p_data?'next_run_at' THEN (p_data->>'next_run_at')::timestamptz ELSE next_run_at END,
        version=version+1,updated_at=now() WHERE id=p_id RETURNING * INTO s;
    RETURN to_jsonb(s);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_enqueue_due()
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE s public.despacho_agent_schedules; j public.despacho_agent_jobs; new_id uuid; n integer=0;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    FOR s IN SELECT * FROM public.despacho_agent_schedules WHERE enabled AND next_run_at<=now() ORDER BY next_run_at LIMIT 5 FOR UPDATE SKIP LOCKED LOOP
        SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=s.job_id AND owner_id=s.owner_id;
        IF NOT FOUND OR j.approved_hash IS DISTINCT FROM j.plan_hash OR j.state IN ('draft','cancelled') THEN
            UPDATE public.despacho_agent_schedules SET enabled=false,last_error='El plan de origen ya no está disponible o aprobado.',version=version+1,updated_at=now() WHERE id=s.id;
            CONTINUE;
        END IF;
        -- Avoid overlapping runs for one recurring assignment.
        IF EXISTS(SELECT 1 FROM public.despacho_agent_jobs WHERE schedule_id=s.id AND state IN ('approved','running','waiting_approval')) THEN
            UPDATE public.despacho_agent_schedules SET next_run_at=now()+interval '5 minutes',last_error='La ejecución anterior sigue en curso.',version=version+1,updated_at=now() WHERE id=s.id;
            CONTINUE;
        END IF;
        new_id=gen_random_uuid();
        INSERT INTO public.despacho_agent_jobs(id,owner_id,title,objective,document_ids,matter_id,playbook_id,allowed_urls,plan,plan_hash,approved_hash,approved_at,state,schedule_id,scheduled_for)
            VALUES(new_id,j.owner_id,j.title,j.objective,j.document_ids,j.matter_id,j.playbook_id,j.allowed_urls,j.plan,j.plan_hash,j.plan_hash,j.approved_at,'approved',s.id,s.next_run_at);
        UPDATE public.despacho_agent_schedules SET last_run_at=now(),last_job_id=new_id,next_run_at=now()+make_interval(mins=>s.interval_minutes),last_error='',version=version+1,updated_at=now() WHERE id=s.id;
        n=n+1;
    END LOOP;
    RETURN n;
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_propose(p_owner uuid,p_job uuid,p_session uuid,p_action jsonb,p_hash text)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; a public.despacho_agent_browser_actions;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.state IN ('draft','running','cancelled') OR j.manual_control OR j.approved_hash IS DISTINCT FROM j.plan_hash THEN RAISE EXCEPTION 'job not available' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM public.despacho_agent_browser_actions WHERE job_id=p_job AND owner_id=p_owner AND state='executing') THEN RAISE EXCEPTION 'action in progress' USING ERRCODE='55000'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_job AND owner_id=p_owner AND state='pending';
    INSERT INTO public.despacho_agent_browser_actions(owner_id,job_id,session_id,action,page_hash,expires_at)
        VALUES(p_owner,p_job,p_session,p_action||jsonb_build_object('prior_state',CASE WHEN j.cursor=jsonb_array_length(j.plan) THEN 'completed' ELSE 'approved' END),p_hash,now()+interval '5 minutes') RETURNING * INTO a;
    UPDATE public.despacho_agent_jobs SET state='waiting_approval',version=version+1,updated_at=now() WHERE id=p_job;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail) VALUES(p_owner,p_job,'browser_action_proposed',jsonb_build_object('action_id',a.id,'action',p_action));
    RETURN to_jsonb(a);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_claim(p_owner uuid,p_job uuid,p_action uuid,p_session uuid,p_hash text,p_version integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE a public.despacho_agent_browser_actions; j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.version<>p_version OR j.state<>'waiting_approval' OR j.manual_control THEN RAISE EXCEPTION 'stale approval' USING ERRCODE='40001'; END IF;
    SELECT * INTO a FROM public.despacho_agent_browser_actions WHERE id=p_action AND job_id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR a.state<>'pending' OR a.session_id<>p_session OR a.page_hash<>p_hash OR a.expires_at<=now() THEN RAISE EXCEPTION 'approval expired or used' USING ERRCODE='55000'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state='executing',expires_at=now()+interval '2 minutes' WHERE id=a.id RETURNING * INTO a;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail) VALUES(p_owner,p_job,'browser_action_approved',jsonb_build_object('action_id',a.id,'action',a.action));
    RETURN to_jsonb(a);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_finish(p_owner uuid,p_job uuid,p_action uuid,p_result jsonb,p_error text DEFAULT '')
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE a public.despacho_agent_browser_actions; j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    SELECT * INTO a FROM public.despacho_agent_browser_actions WHERE id=p_action AND job_id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR a.state<>'executing' THEN RAISE EXCEPTION 'invalid completion' USING ERRCODE='40001'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state=CASE WHEN p_error='' THEN 'completed' ELSE 'failed' END,result=p_result||jsonb_build_object('error',left(p_error,1200)),finished_at=now() WHERE id=p_action;
    IF j.state<>'cancelled' THEN UPDATE public.despacho_agent_jobs SET state=coalesce(a.action->>'prior_state','approved'),last_error=left(p_error,1200),version=version+1,updated_at=now() WHERE id=p_job RETURNING * INTO j; END IF;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail) VALUES(p_owner,p_job,CASE WHEN p_error='' THEN 'browser_action_completed' ELSE 'browser_action_uncertain' END,jsonb_build_object('action_id',a.id,'error',left(p_error,1200)));
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_reset(p_owner uuid,p_job uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs; abandoned integer=0;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.state IN ('draft','running','cancelled') THEN RAISE EXCEPTION 'job unavailable' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM public.despacho_agent_browser_actions WHERE job_id=p_job AND owner_id=p_owner AND state='executing' AND expires_at>now()) THEN
        RAISE EXCEPTION 'action in progress' USING ERRCODE='55000'; END IF;
    -- Only an explicit close/recovery can abandon an expired in-flight action.
    -- Its effect is unknown; the single-use action is never made pending again.
    UPDATE public.despacho_agent_browser_actions SET state='failed',finished_at=now(),
        result=jsonb_build_object('error','La sesión se cerró o perdió; revisa el sitio. El resultado no se pudo confirmar.','result_verified',false)
        WHERE job_id=p_job AND owner_id=p_owner AND state='executing' AND expires_at<=now();
    GET DIAGNOSTICS abandoned=ROW_COUNT;
    UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_job AND owner_id=p_owner AND state='pending';
    IF j.state='waiting_approval' THEN
        UPDATE public.despacho_agent_jobs SET state=CASE WHEN cursor=jsonb_array_length(plan) THEN 'completed' ELSE 'approved' END,manual_control=false,
            last_error=CASE WHEN abandoned>0 THEN 'Se recuperó una sesión perdida. Revisa el sitio: el resultado de la interacción es incierto y no se repetirá.' ELSE last_error END,
            version=version+1,updated_at=now() WHERE id=p_job RETURNING * INTO j;
    END IF;
    IF abandoned>0 THEN INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail)
        VALUES(p_owner,p_job,'browser_action_abandoned',jsonb_build_object('count',abandoned,'result_verified',false)); END IF;
    RETURN to_jsonb(j);
END $$;

CREATE OR REPLACE FUNCTION public.despacho_agent_browser_manual(p_owner uuid,p_job uuid,p_manual boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE j public.despacho_agent_jobs;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    SELECT * INTO j FROM public.despacho_agent_jobs WHERE id=p_job AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND OR j.state IN ('draft','running','cancelled') OR j.approved_hash IS DISTINCT FROM j.plan_hash THEN RAISE EXCEPTION 'job unavailable' USING ERRCODE='55000'; END IF;
    IF EXISTS(SELECT 1 FROM public.despacho_agent_browser_actions WHERE job_id=p_job AND owner_id=p_owner AND state='executing') THEN RAISE EXCEPTION 'action in progress' USING ERRCODE='55000'; END IF;
    UPDATE public.despacho_agent_browser_actions SET state='expired' WHERE job_id=p_job AND owner_id=p_owner AND state='pending';
    UPDATE public.despacho_agent_jobs SET manual_control=p_manual,
        state=CASE WHEN p_manual THEN 'waiting_approval' WHEN cursor=jsonb_array_length(plan) THEN 'completed' ELSE 'approved' END,
        version=version+1,updated_at=now() WHERE id=p_job RETURNING * INTO j;
    INSERT INTO public.despacho_agent_events(owner_id,job_id,event,detail)
        VALUES(p_owner,p_job,CASE WHEN p_manual THEN 'manual_takeover_started' ELSE 'manual_takeover_finished' END,jsonb_build_object('manual',p_manual,'result_verified',false));
    RETURN to_jsonb(j);
END $$;

REVOKE ALL ON FUNCTION public.despacho_agent_control(uuid,uuid,integer,text,jsonb),public.despacho_agent_claim_step(uuid,uuid,integer,uuid),public.despacho_agent_finish_step(uuid,uuid,uuid,integer,jsonb,text),
    public.despacho_agent_schedule_create(uuid,uuid,integer,timestamptz,boolean),public.despacho_agent_schedule_update(uuid,uuid,integer,jsonb),public.despacho_agent_enqueue_due(),
    public.despacho_agent_browser_propose(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_claim(uuid,uuid,uuid,uuid,text,integer),public.despacho_agent_browser_finish(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_reset(uuid,uuid),public.despacho_agent_browser_manual(uuid,uuid,boolean)
    FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_agent_control(uuid,uuid,integer,text,jsonb),public.despacho_agent_claim_step(uuid,uuid,integer,uuid),public.despacho_agent_finish_step(uuid,uuid,uuid,integer,jsonb,text),
    public.despacho_agent_schedule_create(uuid,uuid,integer,timestamptz,boolean),public.despacho_agent_schedule_update(uuid,uuid,integer,jsonb),public.despacho_agent_enqueue_due(),
    public.despacho_agent_browser_propose(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_claim(uuid,uuid,uuid,uuid,text,integer),public.despacho_agent_browser_finish(uuid,uuid,uuid,jsonb,text),public.despacho_agent_browser_reset(uuid,uuid),public.despacho_agent_browser_manual(uuid,uuid,boolean)
    TO service_role;
COMMIT;
