"""Backfill G-POST V1 semantics and repair legacy machine snapshots.

Revision ID: 20260812_02
Revises: 20260812_01
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "20260812_02"
down_revision = "20260812_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    drafts = connection.execute(sa.text("""
        SELECT d.id, d.machine_profile_id, d.machine_profile_revision_id, d.templates_json,
               lower(m.machine_type) canonical_machine_type, r.machine_type revision_machine_type,
               m.name machine_name, m.manufacturer machine_manufacturer, m.model machine_model,
               m.controller_name machine_controller_name,
               m.controller_manufacturer machine_controller_manufacturer,
               m.controller_model machine_controller_model, m.controller_version machine_controller_version,
               m.axis_count machine_axis_count, m.x_min machine_x_min, m.x_max machine_x_max,
               m.y_min machine_y_min, m.y_max machine_y_max, m.z_min machine_z_min, m.z_max machine_z_max,
               m.max_spindle_rpm machine_max_spindle_rpm, m.max_feed_rate machine_max_feed_rate,
               m.supported_work_offsets machine_work_offsets, m.approved_g_codes machine_g_codes,
               m.approved_m_codes machine_m_codes, m.restricted_commands machine_restricted_commands,
               m.safe_start_template machine_safe_start, m.tool_change_template machine_tool_change,
               m.program_end_template machine_program_end,
               r.manufacturer revision_manufacturer, r.model revision_model,
               r.controller_name revision_controller_name
        FROM gpost_drafts d
        JOIN machine_profiles m ON m.id=d.machine_profile_id
        JOIN machine_profile_revisions r ON r.id=d.machine_profile_revision_id
    """)).mappings().all()
    for draft in drafts:
        canonical = draft["canonical_machine_type"]
        # Repair the known legacy import defect where a fictional sample VMC
        # revision was attached to the owning KLS machine profile. This is a
        # correction of corrupt imported identity, not a normal revision edit.
        identity_mismatch = any((draft[machine_key] or "") != (draft[revision_key] or "") for machine_key, revision_key in (
            ("machine_manufacturer", "revision_manufacturer"),
            ("machine_model", "revision_model"),
            ("machine_controller_name", "revision_controller_name"),
        ))
        if identity_mismatch or (canonical and canonical != str(draft["revision_machine_type"]).lower()):
            connection.execute(sa.text("""
                UPDATE machine_profile_revisions SET
                  name=:name, manufacturer=:manufacturer, model=:model,
                  controller_name=:controller_name, controller_manufacturer=:controller_manufacturer,
                  controller_model=:controller_model, controller_version=:controller_version,
                  machine_type=:machine_type, axis_count=:axis_count,
                  x_min=:x_min, x_max=:x_max, y_min=:y_min, y_max=:y_max, z_min=:z_min, z_max=:z_max,
                  max_spindle_rpm=:max_spindle_rpm, max_feed_rate=:max_feed_rate,
                  supported_work_offsets_json=:work_offsets, approved_g_codes_json=:g_codes,
                  approved_m_codes_json=:m_codes, restricted_commands_json=:restricted_commands,
                  safe_start_template=:safe_start, tool_change_template=:tool_change,
                  program_end_template=:program_end,
                  notes='Legacy cross-profile import repaired from owning machine profile.'
                WHERE id=:id
            """), {
                "name": draft["machine_name"], "manufacturer": draft["machine_manufacturer"],
                "model": draft["machine_model"], "controller_name": draft["machine_controller_name"],
                "controller_manufacturer": draft["machine_controller_manufacturer"],
                "controller_model": draft["machine_controller_model"],
                "controller_version": draft["machine_controller_version"], "machine_type": canonical,
                "axis_count": draft["machine_axis_count"], "x_min": draft["machine_x_min"],
                "x_max": draft["machine_x_max"], "y_min": draft["machine_y_min"], "y_max": draft["machine_y_max"],
                "z_min": draft["machine_z_min"], "z_max": draft["machine_z_max"],
                "max_spindle_rpm": draft["machine_max_spindle_rpm"], "max_feed_rate": draft["machine_max_feed_rate"],
                "work_offsets": draft["machine_work_offsets"], "g_codes": draft["machine_g_codes"],
                "m_codes": draft["machine_m_codes"], "restricted_commands": draft["machine_restricted_commands"],
                "safe_start": draft["machine_safe_start"], "tool_change": draft["machine_tool_change"],
                "program_end": draft["machine_program_end"], "id": draft["machine_profile_revision_id"],
            })
        connection.execute(sa.text("UPDATE gpost_drafts SET machine_type=:value WHERE id=:id"),
                           {"value": canonical, "id": draft["id"]})
        templates = json.loads(draft["templates_json"] or "{}")
        if "feed_rate" not in templates:
            templates["feed_rate"] = "F{feed:g}"
        if "comment" not in templates:
            templates["comment"] = "({text})"
        if templates.get("linear_feed_move") == "G01 {coordinates}{feed}":
            templates["linear_feed_move"] = "G01 {coordinates} F{feed:g}"
        connection.execute(sa.text("UPDATE gpost_drafts SET templates_json=:templates WHERE id=:id"),
                           {"templates": json.dumps(templates), "id": draft["id"]})

    definitions = {
        "loadtl": ("tool_change", "Tool selection / load", True, '{}'),
        "fedrat": ("feed_rate", "Feed rate command", True, '{}'),
        "rapid": ("rapid_move", "Enable rapid positioning", True, '{}'),
        "goto": ("linear_feed_move", "Positioning / cutting move", True, '{}'),
        "fini": ("program_end", "End of CL program", True, '{}'),
        "pprint": ("comment", "Program comment", False, '{}'),
        "from": (None, "Initial positioning context", False, '{}'),
        "spindl": ("spindle_start_cw", "Clockwise spindle start", True, '{"direction":"CLW","category":"Spindle"}'),
        "coolnt": ("coolant_on", "Coolant on", True, '{"mode":"ON","category":"Coolant"}'),
    }
    for old_key, (template_key, description, required, conditions) in definitions.items():
        new_key = {"spindl": "spindl_cw", "coolnt": "coolnt_on"}.get(old_key, old_key)
        connection.execute(sa.text("""
            UPDATE gpost_mappings SET mapping_key=:new_key, template_key=:template_key,
              output_template=NULL, description=:description, required_for_v1=:required, conditions_json=:conditions,
              support_status='supported'
            WHERE mapping_key=:old_key
        """), {"new_key": new_key, "template_key": template_key, "description": description,
                 "required": required, "conditions": conditions, "old_key": old_key})
    connection.execute(sa.text("""
        UPDATE gpost_mappings SET output_template=NULL
        WHERE template_key IS NOT NULL AND uses_override=0
    """))
    connection.execute(sa.text("""
        UPDATE gpost_mappings SET support_status=CASE WHEN cl_command IN ('MULTAX','TLAXIS')
          THEN 'not_applicable' ELSE 'not_implemented' END, required_for_v1=0,
          description=CASE cl_command WHEN 'MULTAX' THEN 'Multiaxis mode'
            WHEN 'TLAXIS' THEN 'Tool-axis orientation' ELSE 'Advanced CL behavior' END
        WHERE supported=0 OR mapping_type='unsupported'
    """))
    for key, template_key, description, conditions in (
        ("spindl_ccw", "spindle_start_ccw", "Counter-clockwise spindle start", '{"direction":"CCLW","category":"Spindle"}'),
        ("spindl_off", "spindle_stop", "Spindle stop", '{"direction":"OFF","category":"Spindle"}'),
        ("coolnt_off", "coolant_off", "Coolant off", '{"mode":"OFF","category":"Coolant"}'),
    ):
        source_key = "spindl_cw" if key.startswith("spindl") else "coolnt_on"
        connection.execute(sa.text("""
            INSERT INTO gpost_mappings (
              gpost_draft_id, mapping_key, cl_command, mapping_type, output_template, template_key,
              template_override, uses_override, support_status, required_for_v1, description,
              conditions_json, required_state_json, resulting_state_json, machine_type_scope,
              dialect_scope, supported, confidence, source_type, source_document_id, source_chunk_id,
              source_page, source_section, source_excerpt, source_authority, review_status, review_note,
              created_at, updated_at)
            SELECT gpost_draft_id, :key, cl_command, 'conditional', NULL, :template_key,
              NULL, 0, 'supported', 1, :description, :conditions, required_state_json,
              resulting_state_json, machine_type_scope, dialect_scope, 1, confidence, source_type,
              source_document_id, source_chunk_id, source_page, source_section, source_excerpt,
              source_authority, 'pending', NULL, created_at, updated_at
            FROM gpost_mappings source WHERE source.mapping_key=:source_key
              AND NOT EXISTS (SELECT 1 FROM gpost_mappings existing
                WHERE existing.gpost_draft_id=source.gpost_draft_id AND existing.mapping_key=:key)
        """), {"key": key, "template_key": template_key, "description": description,
                 "conditions": conditions, "source_key": source_key})

    # Normalize scope and derived summaries after all mapping variants exist.
    connection.execute(sa.text("""
        UPDATE gpost_mappings SET
          machine_type_scope=(SELECT machine_type FROM gpost_drafts
            WHERE gpost_drafts.id=gpost_mappings.gpost_draft_id),
          dialect_scope=(SELECT controller_family FROM gpost_drafts
            WHERE gpost_drafts.id=gpost_mappings.gpost_draft_id)
    """))
    draft_ids = connection.execute(sa.text("SELECT id FROM gpost_drafts")).scalars().all()
    for draft_id in draft_ids:
        rows = connection.execute(sa.text("""
            SELECT required_for_v1, support_status, review_status
            FROM gpost_mappings WHERE gpost_draft_id=:draft_id
        """), {"draft_id": draft_id}).mappings().all()
        required = [row for row in rows if row["required_for_v1"] and row["support_status"] != "not_applicable"]
        reviewed = [row for row in required if row["review_status"] in {"accepted", "accepted_with_edit"}]
        summary = {
            "required": len(required), "reviewed": len(reviewed), "needs_review": len(required) - len(reviewed),
            "not_applicable": sum(row["support_status"] == "not_applicable" for row in rows),
            "not_implemented": sum(row["support_status"] == "not_implemented" for row in rows),
            "blocking": sum(row["support_status"] == "unsupported_required" for row in rows),
            "percent": round(len(reviewed) / max(1, len(required)) * 100), "total_known": len(rows),
        }
        connection.execute(sa.text("UPDATE gpost_drafts SET review_summary_json=:summary WHERE id=:draft_id"),
                           {"summary": json.dumps(summary), "draft_id": draft_id})


def downgrade() -> None:
    # This is a corrective data migration. Schema rollback is handled by 20260812_01.
    pass
