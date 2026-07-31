# QA Report — Arbor Vista Platform Database v1.0

## Result

**Static package QA: PASS**

> A live PostgreSQL server was not available in the artifact-generation environment. The included GitHub Actions workflow starts PostgreSQL 16, applies all migrations and seeds, runs SQL regression tests, and creates a schema artifact.

## Checks

- `migration_file_count`: **10**
- `migration_versions`: **['001', '002', '003', '004', '005', '006', '007', '008', '009', '010']**
- `migration_versions_unique`: **True**
- `tables_detected`: **65**
- `table_names_unique`: **True**
- `all_migrations_have_transaction`: **True**
- `real_comp_count`: **83**
- `no_monthly_comp_seed`: **True**
- `pii_ciphertext_columns_present`: **True**
- `rls_enabled`: **True**
- `availability_lock_present`: **True**
- `reporting_view_avoids_join_multiplication`: **True**
- `email_placeholder_present`: **True**
- `ai_placeholder_present`: **True**
- `analytics_present`: **True**
- `supabase_optional_adapter_present`: **True**
- `github_ci_present`: **True**
- `dollar_quote_pairs_balanced`: **True**

## Included runtime tests

- Required-table smoke test
- Overlap prevention test
- Seven/eight-guest approval rule test
- Availability-function test
- Public-view protected-column test
- RLS-on-secure-guests test
- Exact 83-comp seed test
- No fabricated monthly competitor-performance test