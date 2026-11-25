-- M43 gate: synthetic pre-upgrade data at 20261124_0071 to prove the 0073 backfills keep every contact/team/stage.
-- All names are synthetic POVU test data (.test domain); never loaded into a real database.
INSERT INTO customers (id, code, name, channel, payment_terms_days, currency, is_active, is_prepaid, email)
VALUES ('11111111-1111-1111-1111-111111111111', 'SYN-C1', 'POVU Synthetic Outlet A', 'RETAIL', 30, 'KES', true, false, 'a@povu-demo.test'),
       ('22222222-2222-2222-2222-222222222222', 'SYN-C2', 'POVU Synthetic Outlet B', 'WHOLESALE', 30, 'KES', true, false, 'b@povu-demo.test');

INSERT INTO crm_pipeline_stages (id, stage_code, stage_name, stage_type, sequence_no, default_probability, active_flag)
VALUES ('33333333-3333-3333-3333-333333333331', 'SYN-NEW', 'New', 'LEAD', 1, 10, true),
       ('33333333-3333-3333-3333-333333333332', 'SYN-PROP', 'Proposal', 'OPPORTUNITY', 2, 50, true);

-- 1: e-mail contact, opportunity, team NBO; 2: same e-mail (one contact expected), won; 3: name only; 4: no contact
INSERT INTO crm_records (id, record_type, company_name, contact_person_name, contact_email, contact_phone, stage_id,
                         status, sales_team_id, assigned_customer_id, qualified_flag, created_at, updated_at)
VALUES ('44444444-4444-4444-4444-444444444441', 'OPPORTUNITY', 'POVU Synthetic Outlet A', 'Asha Buyer', 'Asha@povu-demo.test', '+254700000001',
        '33333333-3333-3333-3333-333333333332', 'OPEN', 'NBO', '11111111-1111-1111-1111-111111111111', true, now() - interval '2 days', now()),
       ('44444444-4444-4444-4444-444444444442', 'OPPORTUNITY', 'POVU Synthetic Outlet A', 'Asha B.', 'asha@povu-demo.test', NULL,
        '33333333-3333-3333-3333-333333333332', 'WON', 'NBO', '11111111-1111-1111-1111-111111111111', true, now() - interval '1 day', now()),
       ('44444444-4444-4444-4444-444444444443', 'LEAD', 'POVU Synthetic Kiosk', 'Juma Shopkeeper', NULL, '+254700000003',
        '33333333-3333-3333-3333-333333333331', 'OPEN', 'MSA', NULL, false, now(), now()),
       ('44444444-4444-4444-4444-444444444444', 'LEAD', 'POVU Synthetic Depot', NULL, NULL, NULL,
        '33333333-3333-3333-3333-333333333331', 'OPEN', NULL, NULL, false, now(), now());

INSERT INTO crm_account_contacts (id, customer_id, full_name, email, committee_role)
VALUES ('55555555-5555-5555-5555-555555555551', '22222222-2222-2222-2222-222222222222', 'Grace Finance', 'grace@povu-demo.test', 'BUYER'),
       ('55555555-5555-5555-5555-555555555552', '11111111-1111-1111-1111-111111111111', 'Asha Buyer', 'asha@povu-demo.test', 'DECISION_MAKER');
