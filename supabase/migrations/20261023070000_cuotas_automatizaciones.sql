-- Durable call budgets for background work; never stores tokens or prompts.
BEGIN;
CREATE TABLE IF NOT EXISTS public.despacho_automation_user_usage (
    usage_day date NOT NULL,
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    calls integer NOT NULL CHECK(calls>=0),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(usage_day,owner_id)
);
CREATE TABLE IF NOT EXISTS public.despacho_automation_global_usage (
    usage_day date PRIMARY KEY,
    calls integer NOT NULL CHECK(calls>=0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.despacho_automation_user_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_automation_global_usage ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_automation_user_usage,public.despacho_automation_global_usage FROM PUBLIC,anon,authenticated;
GRANT ALL ON public.despacho_automation_user_usage,public.despacho_automation_global_usage TO service_role;

CREATE OR REPLACE FUNCTION public.despacho_automation_reserve(p_owner uuid,p_user_limit integer,p_global_limit integer)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE today date=(now() AT TIME ZONE 'UTC')::date; reset_at timestamptz;
        personal integer=0; global_calls integer=0;
BEGIN
    IF auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'server only' USING ERRCODE='42501'; END IF;
    IF p_owner IS NULL OR p_user_limit IS NULL OR p_global_limit IS NULL OR p_user_limit NOT BETWEEN 0 AND 1000000
       OR p_global_limit NOT BETWEEN 0 AND 1000000 THEN RAISE EXCEPTION 'invalid quota' USING ERRCODE='22023'; END IF;
    -- All workers serialize the global and personal reservation for one day.
    -- A denied reservation increments neither counter; rollback cannot charge
    -- only one of them. UTC is independent from the connection's timezone.
    PERFORM pg_advisory_xact_lock(hashtextextended('automation-daily:'||today::text,0));
    reset_at=((today+1)::timestamp AT TIME ZONE 'UTC');
    SELECT calls INTO personal FROM public.despacho_automation_user_usage WHERE usage_day=today AND owner_id=p_owner;
    SELECT calls INTO global_calls FROM public.despacho_automation_global_usage WHERE usage_day=today;
    personal=coalesce(personal,0);global_calls=coalesce(global_calls,0);
    IF personal>=p_user_limit THEN
        RETURN jsonb_build_object('allowed',false,'scope','user','used',personal,'limit',p_user_limit,'reset_at',reset_at);
    END IF;
    IF global_calls>=p_global_limit THEN
        RETURN jsonb_build_object('allowed',false,'scope','global','used',global_calls,'limit',p_global_limit,'reset_at',reset_at);
    END IF;
    INSERT INTO public.despacho_automation_user_usage(usage_day,owner_id,calls) VALUES(today,p_owner,1)
        ON CONFLICT(usage_day,owner_id) DO UPDATE SET calls=despacho_automation_user_usage.calls+1,updated_at=now();
    INSERT INTO public.despacho_automation_global_usage(usage_day,calls) VALUES(today,1)
        ON CONFLICT(usage_day) DO UPDATE SET calls=despacho_automation_global_usage.calls+1,updated_at=now();
    RETURN jsonb_build_object('allowed',true,'user_used',personal+1,'global_used',global_calls+1,
        'user_limit',p_user_limit,'global_limit',p_global_limit,'reset_at',reset_at,'unit','logical_call');
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_automation_reserve(uuid,integer,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_automation_reserve(uuid,integer,integer) TO service_role;
COMMIT;
