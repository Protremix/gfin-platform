-- GFIN Investigation Lifecycle v2.0 — Database Migration
-- Replaces flat case model with proper investigation lifecycle

-- 1. Add lifecycle columns to cases table
ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_phase TEXT DEFAULT 'TRIAGE';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'MEDIUM';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS investigation_narrative TEXT DEFAULT '';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS attribution_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS risk_assessment JSONB DEFAULT '{}'::jsonb;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS action_plan JSONB DEFAULT '{}'::jsonb;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS monitoring_status TEXT DEFAULT 'ACTIVE';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS assigned_to_officer_id INTEGER;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_phase_updated TIMESTAMP WITH TIME ZONE DEFAULT now();
ALTER TABLE cases ADD COLUMN IF NOT EXISTS total_loss_usd REAL DEFAULT 0;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS jurisdiction_notes TEXT DEFAULT '';

-- Update existing cases to new phase system
UPDATE cases SET case_phase = 'ACTIVE_INVESTIGATION' WHERE status = 'INVESTIGATING';
UPDATE cases SET case_phase = 'CLOSED' WHERE status IN ('RESOLVED', 'CLOSED');

-- 2. Investigation steps table — proper lifecycle phases
CREATE TABLE IF NOT EXISTS investigation_steps (
    id SERIAL PRIMARY KEY,
    case_id TEXT NOT NULL,
    phase TEXT NOT NULL,  -- TRIAGE, ACTIVE_INVESTIGATION, ATTRIBUTION, RISK_ASSESSMENT, LEA_ROUTING, ACTION, MONITORING
    step_name TEXT NOT NULL,
    step_type TEXT DEFAULT 'AUTO',  -- AUTO or MANUAL
    status TEXT DEFAULT 'PENDING',  -- PENDING, IN_PROGRESS, COMPLETED, SKIPPED, BLOCKED
    result JSONB DEFAULT '{}'::jsonb,
    officer_id INTEGER,
    officer_name TEXT DEFAULT 'SYSTEM',
    order_num INTEGER DEFAULT 0,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT now(),
    completed_date TIMESTAMP WITH TIME ZONE,
    CONSTRAINT inv_steps_status_check CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED', 'BLOCKED'))
);
CREATE INDEX IF NOT EXISTS idx_inv_steps_case_id ON investigation_steps(case_id);
CREATE INDEX IF NOT EXISTS idx_inv_steps_phase ON investigation_steps(phase);

-- 3. Case entities — all entities linked to a case with metadata
CREATE TABLE IF NOT EXISTS case_entities (
    id SERIAL PRIMARY KEY,
    case_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- DOMAIN, IP, WALLET, PHONE, EMAIL, PERSON, COMPANY, HOSTING_PROVIDER, REGISTRAR, CDN, SSL_CERT
    entity_value TEXT NOT NULL,
    entity_metadata JSONB DEFAULT '{}'::jsonb,  -- WHOIS data, wallet balance, hosting details, etc.
    source TEXT DEFAULT 'AUTO',  -- AUTO, MANUAL, TELEGRAM, HUNTER, COMPLAINT
    confidence TEXT DEFAULT 'MEDIUM',  -- LOW, MEDIUM, HIGH, CONFIRMED
    status TEXT DEFAULT 'IDENTIFIED',  -- IDENTIFIED, INVESTIGATING, CONFIRMED, DISMISSED
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_case_entities_case_id ON case_entities(case_id);
CREATE INDEX IF NOT EXISTS idx_case_entities_value ON case_entities(entity_value);
CREATE INDEX IF NOT EXISTS idx_case_entities_type ON case_entities(entity_type);

-- 4. Entity links — cross-case correlation
CREATE TABLE IF NOT EXISTS entity_links (
    id SERIAL PRIMARY KEY,
    entity_value TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    case_ids TEXT[] DEFAULT '{}',
    link_type TEXT DEFAULT 'SHARED_ENTITY',  -- SHARED_ENTITY, SHARED_WALLET, SHARED_PHONE, SHARED_HOSTING, SHARED_REGISTRAR
    mention_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_entity_links_value ON entity_links(entity_value);
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_links_unique ON entity_links(entity_value, entity_type);

-- 5. Case timeline — chronological event log
CREATE TABLE IF NOT EXISTS case_timeline (
    id SERIAL PRIMARY KEY,
    case_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- CASE_OPENED, EVIDENCE_ADDED, PHASE_CHANGED, NOTE_ADDED, ENTITY_FOUND, STATUS_CHANGED, OFFICER_ASSIGNED, ALERT_SENT, TAKEDOWN_REQUESTED, etc.
    event_title TEXT NOT NULL,
    event_description TEXT,
    event_metadata JSONB DEFAULT '{}'::jsonb,
    officer_name TEXT DEFAULT 'SYSTEM',
    created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_case_timeline_case_id ON case_timeline(case_id);

-- 6. Case actions — track LEA actions, takedowns, alerts
CREATE TABLE IF NOT EXISTS case_actions (
    id SERIAL PRIMARY KEY,
    case_id TEXT NOT NULL,
    action_type TEXT NOT NULL,  -- TAKEDOWN_REQUEST, LEA_REFERRAL, PUBLIC_ALERT, VICTIM_NOTIFICATION, PROSECUTION_PACKAGE, DOMAIN_REPORT
    action_status TEXT DEFAULT 'PENDING',  -- PENDING, SENT, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, FAILED
    target_agency TEXT,  -- which LEA/provider was contacted
    target_contact TEXT,  -- email/URL
    action_metadata JSONB DEFAULT '{}'::jsonb,
    officer_id INTEGER,
    officer_name TEXT DEFAULT 'SYSTEM',
    created_date TIMESTAMP WITH TIME ZONE DEFAULT now(),
    response_date TIMESTAMP WITH TIME ZONE,
    response_notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_case_actions_case_id ON case_actions(case_id);

-- 7. Insert initial timeline events for existing cases
INSERT INTO case_timeline (case_id, event_type, event_title, event_description, officer_name)
SELECT case_id, 'CASE_OPENED', 'Case opened', 'Case created with status: ' || status, created_by_officer
FROM cases ON CONFLICT DO NOTHING;

-- 8. Insert default investigation steps for existing cases
INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'TRIAGE', 
    'Initial evidence assessment', 
    'AUTO', 
    'COMPLETED', 
    1,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id);

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'TRIAGE', 
    'Evidence gate validation', 
    'AUTO', 
    'COMPLETED', 
    2,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Evidence gate validation');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ACTIVE_INVESTIGATION', 
    'Domain analysis (WHOIS, DNS, SSL)', 
    'AUTO', 
    'COMPLETED', 
    3,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Domain analysis (WHOIS, DNS, SSL)');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ACTIVE_INVESTIGATION', 
    'Financial tracing (wallet analysis)', 
    'AUTO', 
    CASE WHEN c.financial_indicators != '[]'::jsonb THEN 'COMPLETED' ELSE 'PENDING' END,
    4,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Financial tracing (wallet analysis)');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ACTIVE_INVESTIGATION', 
    'Infrastructure mapping', 
    'AUTO', 
    CASE WHEN c.physical_locations != '[]'::jsonb THEN 'COMPLETED' ELSE 'PENDING' END,
    5,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Infrastructure mapping');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ACTIVE_INVESTIGATION', 
    'Entity correlation (cross-case)', 
    'AUTO', 
    'PENDING',
    6,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Entity correlation (cross-case)');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ATTRIBUTION', 
    'Operator identification', 
    'AUTO', 
    'PENDING',
    7,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Operator identification');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ATTRIBUTION', 
    'Attribution assessment', 
    'MANUAL', 
    'PENDING',
    8,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Attribution assessment');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'RISK_ASSESSMENT', 
    'Risk scoring (victims, loss, severity)', 
    'AUTO', 
    'PENDING',
    9,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Risk scoring (victims, loss, severity)');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'LEA_ROUTING', 
    'Jurisdiction analysis & routing', 
    'AUTO', 
    CASE WHEN c.routed_to_countries IS NOT NULL AND array_length(c.routed_to_countries, 1) > 0 THEN 'COMPLETED' ELSE 'PENDING' END,
    10,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Jurisdiction analysis & routing');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'ACTION', 
    'Action plan (takedown/referral/alert)', 
    'MANUAL', 
    'PENDING',
    11,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Action plan (takedown/referral/alert)');

INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, order_num, officer_name)
SELECT 
    c.case_id, 
    'MONITORING', 
    'Continuous monitoring setup', 
    'AUTO', 
    'PENDING',
    12,
    'SYSTEM'
FROM cases c
WHERE NOT EXISTS (SELECT 1 FROM investigation_steps WHERE case_id = c.case_id AND step_name = 'Continuous monitoring setup');

-- 9. Insert existing evidence as case entities
INSERT INTO case_entities (case_id, entity_type, entity_value, source, confidence, status)
SELECT 
    e.case_id,
    'EVIDENCE',
    e.evidence_id,
    'AUTO',
    CASE WHEN e.confidence = 'HIGH' THEN 'HIGH' ELSE 'MEDIUM' END,
    'CONFIRMED'
FROM evidence e
WHERE e.case_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- 10. Insert existing case entities from evidence_chain
INSERT INTO case_entities (case_id, entity_type, entity_value, source, confidence, status)
SELECT 
    c.case_id,
    'DOMAIN',
    c.target,
    'COMPLAINT',
    'HIGH',
    'IDENTIFIED'
FROM cases c
WHERE c.target_type = 'DOMAIN'
ON CONFLICT DO NOTHING;
