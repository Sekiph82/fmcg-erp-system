-- M43 gate: expectations after upgrading the seeded 20261124_0071 database to 20261125_0073.
SELECT 'contacts_total=3', count(*) = 3 FROM crm_contacts;                                  -- asha (merged), grace, juma
SELECT 'asha_one_contact', count(*) = 1 FROM crm_contacts WHERE lower(email) = 'asha@povu-demo.test';
SELECT 'asha_customer_lifecycle', lifecycle_stage = 'CUSTOMER' FROM crm_contacts WHERE lower(email) = 'asha@povu-demo.test';
SELECT 'juma_name_only_kept', count(*) = 1 FROM crm_contacts WHERE full_name = 'Juma Shopkeeper' AND email IS NULL;
SELECT 'records_with_contact_linked', count(*) = 3 FROM crm_contact_associations
 WHERE object_type = 'crm_record' AND label = 'primary';
SELECT 'asha_linked_to_customer', count(*) >= 1 FROM crm_contact_associations a JOIN crm_contacts c ON c.id = a.contact_id
 WHERE lower(c.email) = 'asha@povu-demo.test' AND a.object_type = 'customer' AND a.object_id = '11111111-1111-1111-1111-111111111111';
SELECT 'grace_buyer_label', count(*) = 1 FROM crm_contact_associations a JOIN crm_contacts c ON c.id = a.contact_id
 WHERE c.full_name = 'Grace Finance' AND a.label = 'buyer';
SELECT 'account_contacts_linked', count(*) = 2 FROM crm_account_contacts WHERE contact_id IS NOT NULL;
SELECT 'lifecycle_history_written', count(*) = (SELECT count(*) FROM crm_contacts WHERE lifecycle_stage IS NOT NULL)
  FROM crm_lifecycle_history WHERE source = 'migration';
SELECT 'one_default_pipeline', count(*) = 1 FROM crm_pipelines WHERE is_default;
SELECT 'all_stages_in_pipeline', count(*) = 0 FROM crm_pipeline_stages WHERE pipeline_id IS NULL;
SELECT 'all_records_in_pipeline', count(*) = 0 FROM crm_records WHERE pipeline_id IS NULL;
SELECT 'teams_from_values', count(*) = 2 FROM crm_teams WHERE code IN ('NBO', 'MSA');
SELECT 'records_unchanged', count(*) = 4 FROM crm_records;
