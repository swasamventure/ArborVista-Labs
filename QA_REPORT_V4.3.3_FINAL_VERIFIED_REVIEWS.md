# Arbor Vista Retreat v4.3.3 — Final Verified Reviews QA

**Result: PASS — 138/138 checks passed**

This package was rebuilt after confirming that the previous patch still contained only a link to Airbnb reviews. The corrected homepage now contains a rendered **What Guests Say** section backed by a local review snapshot and a build-time Airbnb updater.

## Verified Airbnb snapshot

- Rating: **4.82/5**
- Reviews: **11**
- Five-star share: **91%**
- Communication: **5.0**
- Cleanliness / accuracy / check-in: **4.9 / 4.9 / 4.9**
- One featured guest excerpt is displayed because Airbnb currently exposes only one individual excerpt in the public server-rendered listing.

## Implementation verified

- The homepage directly contains the new section; it is not injected only at runtime.
- The browser loads `data/airbnb-reviews.json` and retains embedded fallback content.
- The browser does not make a direct cross-origin request to Airbnb.
- A weekly/manual GitHub Action refreshes the local snapshot.
- A failed update preserves the last verified JSON file.
- No guest names or invented review quotations are included.

## Browser verification

- Desktop: visible `True`, loaded `true`, overflow `False`.
- Mobile: visible `True`, loaded `true`, overflow `False`.
- No console errors were recorded.

## Check ledger

- PASS — `source_baseline_recorded`
- PASS — `base_commit_recorded`
- PASS — `base_index_blob_recorded`
- PASS — `release_remains_v4_3_3`
- PASS — `scope_mentions_reviews`
- PASS — `index_exists`
- PASS — `index_parses`
- PASS — `single_doctype` — 1
- PASS — `redundant_utility_removed`
- PASS — `temporary_hero_note_removed`
- PASS — `what_guests_say_section_present`
- PASS — `what_guests_say_heading_exact`
- PASS — `old_link_only_review_section_removed`
- PASS — `review_section_before_footer`
- PASS — `three_review_summary_cards` — 3
- PASS — `featured_review_card_present`
- PASS — `rating_summary_present`
- PASS — `review_count_present`
- PASS — `five_star_percentage_present`
- PASS — `four_category_scores_present`
- PASS — `five_review_themes_present`
- PASS — `airbnb_all_reviews_link_present`
- PASS — `airbnb_reviews_link_correct`
- PASS — `review_snapshot_date_present`
- PASS — `review_loader_linked`
- PASS — `review_loader_cache_busted`
- PASS — `cleanup_css_linked`
- PASS — `cleanup_css_cache_busted`
- PASS — `header_footer_use_approved_logo` — 2
- PASS — `no_pause_control_reintroduced`
- PASS — `host_console_absent`
- PASS — `review_json_exists`
- PASS — `review_json_valid`
- PASS — `review_listing_id_correct`
- PASS — `review_source_airbnb`
- PASS — `review_source_url_correct`
- PASS — `rating_is_4_82` — 4.82
- PASS — `review_count_is_11` — 11
- PASS — `guest_favorite_true`
- PASS — `five_star_share_is_91`
- PASS — `communication_is_5_0`
- PASS — `cleanliness_is_4_9`
- PASS — `accuracy_is_4_9`
- PASS — `checkin_is_4_9`
- PASS — `location_is_4_6`
- PASS — `value_is_4_6`
- PASS — `five_review_themes_in_json`
- PASS — `one_verified_featured_excerpt`
- PASS — `featured_excerpt_is_short` — 15
- PASS — `featured_excerpt_matches_public_listing`
- PASS — `no_guest_name_fields`
- PASS — `last_checked_timestamp_present`
- PASS — `integrity_note_present`
- PASS — `review_js_exists`
- PASS — `browser_fetches_local_json`
- PASS — `browser_does_not_call_airbnb`
- PASS — `browser_uses_no_store_cache`
- PASS — `browser_updates_rating`
- PASS — `browser_updates_review_count`
- PASS — `browser_updates_featured_review`
- PASS — `browser_updates_categories`
- PASS — `browser_updates_themes`
- PASS — `browser_updates_checked_date`
- PASS — `browser_preserves_fallback`
- PASS — `browser_marks_loaded_state`
- PASS — `browser_marks_fallback_state`
- PASS — `review_css_exists`
- PASS — `review_css_section_present`
- PASS — `review_css_desktop_three_columns`
- PASS — `review_css_mobile_stack`
- PASS — `featured_card_dark_background`
- PASS — `featured_card_white_text`
- PASS — `review_button_self_styled`
- PASS — `review_section_uses_page_background`
- PASS — `review_cards_have_borders`
- PASS — `review_mobile_breakpoint`
- PASS — `updater_exists`
- PASS — `updater_targets_correct_listing`
- PASS — `updater_uses_airbnb_public_page`
- PASS — `updater_parses_rating`
- PASS — `updater_parses_review_count`
- PASS — `updater_parses_featured_excerpt`
- PASS — `updater_parses_category_scores`
- PASS — `updater_requires_rating_and_count`
- PASS — `updater_writes_only_after_fetch`
- PASS — `updater_preserves_existing_featured_reviews`
- PASS — `workflow_exists`
- PASS — `workflow_manual_dispatch`
- PASS — `workflow_weekly_schedule`
- PASS — `workflow_contents_write`
- PASS — `workflow_installs_beautifulsoup`
- PASS — `workflow_runs_updater`
- PASS — `workflow_commits_snapshot_only`
- PASS — `python_syntax_apply_v433_final_cleanup.py`
- PASS — `python_syntax_verify_v433_final_cleanup.py`
- PASS — `python_syntax_update_airbnb_reviews.py`
- PASS — `javascript_syntax_v43.js`
- PASS — `javascript_syntax_airbnb-reviews-v433.js`
- PASS — `css_braces_balanced` — 59 / 59
- PASS — `desktop_review_section_visible`
- PASS — `desktop_heading_correct` — What Guests Say
- PASS — `desktop_rating_loaded` — 4.82
- PASS — `desktop_review_count_loaded` — 11
- PASS — `desktop_snapshot_loaded` — true
- PASS — `desktop_featured_excerpt_loaded`
- PASS — `desktop_theme_count_is_5` — 5
- PASS — `desktop_no_horizontal_overflow`
- PASS — `desktop_no_console_errors` — []
- PASS — `mobile_review_section_visible`
- PASS — `mobile_heading_correct` — What Guests Say
- PASS — `mobile_rating_loaded` — 4.82
- PASS — `mobile_review_count_loaded` — 11
- PASS — `mobile_snapshot_loaded` — true
- PASS — `mobile_featured_excerpt_loaded`
- PASS — `mobile_theme_count_is_5` — 5
- PASS — `mobile_no_horizontal_overflow`
- PASS — `mobile_no_console_errors` — []
- PASS — `screenshot_home-v433-what-guests-say-desktop.png` — 136154
- PASS — `screenshot_home-v433-what-guests-say-mobile.png` — 54315
- PASS — `screenshot_what-guests-say-section-desktop.png` — 111534
- PASS — `screenshot_what-guests-say-section-mobile.png` — 93827
- PASS — `screenshot_home-v433-final-top-desktop.png` — 1779370
- PASS — `screenshot_home-v433-final-scrolled-desktop.png` — 653881
- PASS — `screenshot_home-v433-final-top-mobile.png` — 452954
- PASS — `screenshot_interior-v433-final-logo-desktop.png` — 839966
- PASS — `integration_verifier_passes` — PASS — v4.3.3 final verified cleanup and What Guests Say snapshot are installed.Spreadsheet runtime warmup failed during python startup
Traceback (most recent call last):
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/patches/warm_spreadsheet_runtime_on_startup.py", line 26, in warm_spreadsheet_runtime_on_startup
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/spreadsheet_warmup.py", line 785, in warm_spreadsheet_runtime
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/spreadsheet_warmup.py", line 720, in _warm_feature_flows
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/spreadsheet_warmup.py", line 704, in _warm_collaboration_flows
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/generated/interface/models.py", line 30820, in hydrate_crdt_from_proto
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/rpc/remote.py", line 749, in __call__
  File "/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/artifact_tool/rpc/client.py", line 150, in call
artifact_tool.rpc.client.RemoteError: hydrateCrdtFromProto requires an empty collaborative document.
- PASS — `integration_single_doctype`
- PASS — `integration_installs_what_guests_say`
- PASS — `integration_removes_old_review_prompt`
- PASS — `integration_links_review_loader`
- PASS — `integration_installs_snapshot`
- PASS — `integration_installs_updater`
- PASS — `integration_installs_workflow`
- PASS — `failed_updater_returns_nonzero` — 1
- PASS — `failed_updater_preserves_last_snapshot` — 06ead2aa284d06207130363843db1392a76a27d9a71bcf769298b52089ec6670 -> 06ead2aa284d06207130363843db1392a76a27d9a71bcf769298b52089ec6670

## Packaging verification

- PASS — `manifest_created` — 30
- PASS — `manifest_entries_hash_valid`
- PASS — `zip_integrity` — testzip returned no corrupt member
