-- Auth + audit trail: user_profiles + created_by/updated_by em definitions.
-- Idempotente: pode rodar múltiplas vezes sem erro.

CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'engineer' CHECK (role IN ('engineer', 'admin', 'system')),
    discipline TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON public.user_profiles(role);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = '00000000-0000-0000-0000-000000000001'::uuid) THEN
        INSERT INTO auth.users (id, instance_id, aud, role, email, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data, is_super_admin)
        VALUES (
            '00000000-0000-0000-0000-000000000001'::uuid,
            '00000000-0000-0000-0000-000000000000'::uuid,
            'authenticated',
            'authenticated',
            'system@thorus.com.br',
            NOW(),
            NOW(),
            NOW(),
            '{"provider":"system","providers":["system"]}'::jsonb,
            '{"full_name":"Sistema AI - Ingestão Automática"}'::jsonb,
            FALSE
        )
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

INSERT INTO public.user_profiles (id, email, name, role, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'system@thorus.com.br',
    'Sistema AI - Ingestão Automática',
    'system',
    TRUE
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active;

ALTER TABLE definitions
    ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES public.user_profiles(id),
    ADD COLUMN IF NOT EXISTS updated_by_user_id UUID REFERENCES public.user_profiles(id);

UPDATE definitions
SET created_by_user_id = '00000000-0000-0000-0000-000000000001'::uuid
WHERE created_by_user_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'definitions'
          AND column_name = 'created_by_user_id'
          AND is_nullable = 'YES'
    ) THEN
        EXECUTE 'ALTER TABLE definitions ALTER COLUMN created_by_user_id SET NOT NULL';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_definitions_created_by ON definitions(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_definitions_updated_by ON definitions(updated_by_user_id);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth_read_profiles" ON public.user_profiles;
CREATE POLICY "auth_read_profiles"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "auth_update_own_profile" ON public.user_profiles;
CREATE POLICY "auth_update_own_profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    domain TEXT;
    allowed_domain TEXT := 'thorus.com.br';
    derived_name TEXT;
BEGIN
    domain := split_part(new.email, '@', 2);
    IF domain IS DISTINCT FROM allowed_domain AND new.id <> '00000000-0000-0000-0000-000000000001'::uuid THEN
        RAISE EXCEPTION 'Domain % is not allowed; only @% can sign up', domain, allowed_domain
            USING ERRCODE = 'check_violation';
    END IF;

    derived_name := COALESCE(
        new.raw_user_meta_data->>'full_name',
        new.raw_user_meta_data->>'name',
        split_part(new.email, '@', 1)
    );

    INSERT INTO public.user_profiles (id, email, name)
    VALUES (new.id, new.email, derived_name)
    ON CONFLICT (id) DO NOTHING;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

CREATE OR REPLACE FUNCTION public.touch_user_last_login()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.user_profiles
    SET last_login_at = NOW()
    WHERE id = new.id;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS on_auth_user_signin ON auth.users;
CREATE TRIGGER on_auth_user_signin
    AFTER UPDATE OF last_sign_in_at ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.touch_user_last_login();
