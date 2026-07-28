# Profile field reference

The executable source of truth is
`backend/app/profile_extraction/registry.py`. Every definition carries its key,
display name, category, type, allowed units, normalization/validation rule,
required/safety flags, preferred document types, terms, option flag, and notes.
All fields use strict type/unit allowlists, preserve source text, and become
`not_found` when no evidence exists.

| Category | Field keys | Type / units | Preferred evidence and known ambiguity |
| --- | --- | --- | --- |
| Identity | `manufacturer`, `model`, `machine_series`, `machine_variant`, `serial_number_pattern`, `machine_type`, `document_revision`, `document_publication_date`, `machine_units` | strings | Machine/operator/specification documents. Family manuals do not prove an exact variant. Identity and type are required. |
| Controller | `controller_name`, `controller_model`, `controller_version` | strings | Controller/programming/operator manuals. Builder labels and software revisions may differ. Controller name is required. |
| Axes | `axis_count` | integer | Machine/specification sources; required. An option-ready axis is not necessarily installed. |
| Axes | `available_axes` | list | Machine/configuration sources. Preserve named axes and option context. |
| Coordinate limits | `x_min`, `x_max`, `y_min`, `y_max`, `z_min`, `z_max` | number: inch, mm, degrees | Safety relevant. Exact signed coordinate limits only; never inferred from total travel. |
| Rotary limits | `a_min`, `a_max`, `b_min`, `b_max`, `c_min`, `c_max`, `rotary_axis_limits` | number/object: degrees | Safety relevant and configuration dependent. |
| Travel | `x_travel`, `y_travel`, `z_travel` | number: inch, mm | Safety relevant total travel. Does not establish signed minima/maxima. |
| Homing | `axis_home_positions`, `reference_return_behavior` | object/string | Safety relevant; coordinate system and parameter context required. |
| Spindle | `min_spindle_rpm`, `max_spindle_rpm`, `maximum_live_tool_rpm` | number: rpm | Maximum is required/safety relevant. Spindle packages and live tools may vary. |
| Spindle | `spindle_power` | number: kW, hp | Preserve original; hp may normalize to kW. Rated/continuous/peak values differ. |
| Spindle | `spindle_torque` | number: N·m, lb-ft | Preserve speed/duty-cycle context. |
| Spindle | `spindle_direction_support` | list | Controller/manual evidence; syntax mention is not installed support. |
| Spindle | `spindle_orientation_support`, `constant_surface_speed_support` | boolean | Optional/configuration context retained. |
| Spindle | `maximum_css_value`, `spindle_override_range` | number/string | Do not confuse CSS with RPM or an override with a machine limit. |
| Feed | `max_feed_rate` | number: ipm, mm/min | Required/safety relevant maximum cutting feed. Never substitute rapid traverse. |
| Rapid | `rapid_traverse_rate`, `maximum_rapid_rate_x`, `maximum_rapid_rate_y`, `maximum_rapid_rate_z` | number: ipm, mm/min | Safety relevant; axis-specific and combined rates remain distinct. |
| Rotary rapid | `maximum_rapid_rate_rotary` | number: degrees/min | Safety relevant. |
| Motion quality | `feed_override_range`, `minimum_programmable_increment`, `positioning_accuracy`, `repeatability` | string or number: inch, mm | Keep specification conditions and tolerance conventions. |
| Lathe tooling | `turret_count`, `turret_station_count`, `tool_station_count`, `tool_capacity` | integer | Turret/station/capacity terms are not interchangeable. |
| Tool limits | `maximum_tool_size`, `maximum_tool_weight`, `maximum_tool_diameter`, `maximum_tool_length` | string/number: inch, mm, kg, lb | Toolchanger pockets/options and adjacent-tool restrictions may apply. |
| Tool behavior | `tool_change_position`, `tool_change_command` | string | Safety relevant; an example does not establish the required sequence. |
| Tool metadata | `tool_preselection_support`, `tool_offset_ranges`, `geometry_offset_ranges`, `wear_offset_ranges`, `tool_number_format`, `tool_call_examples` | boolean/string/list | Examples remain examples and option support remains unconfirmed. |
| Workholding | `chuck_size`, `maximum_bar_capacity`, `maximum_turning_diameter`, `maximum_turning_length`, `spindle_bore` | number: inch, mm | Physical configuration may differ by chuck/spindle package. |
| Lathe options | `main_spindle_present`, `sub_spindle_present`, `live_tooling_present`, `c_axis_present`, `y_axis_present`, `tailstock_present`, `steady_rest_support`, `part_catcher_present`, `bar_feeder_support` | boolean | Exact-machine verification required for optional capabilities. |
| Mill geometry | `vertical_or_horizontal`, `table_size`, `table_load_capacity` | string/number: inch, mm, kg, lb | Specification/configuration sources; fixture distribution affects load context. |
| Mill options | `rotary_table_present`, `fourth_axis_support`, `fifth_axis_support`, `through_spindle_coolant`, `probe_support`, `pallet_changer_present` | boolean | Interface availability does not prove hardware installation. |
| Tool interface | `spindle_taper`, `tool_holder_standard` | string | Machine/specification evidence; variants and regional standards may differ. |
| Work offsets | `supported_work_offsets`, `extended_work_offsets` | list/string | Required/safety relevant. Controller/programming evidence only; review before approval lists. |
| Coordinates | `machine_coordinate_command`, `local_coordinate_support`, `coordinate_rotation_support`, `scaling_support`, `polar_coordinate_support`, `programmable_data_input_support` | string | Controller syntax with mode/option context. |
| Positioning | `reference_return_commands`, `absolute_positioning_command`, `incremental_positioning_command`, `inch_units_command`, `metric_units_command` | string | Safety relevant commands; mention in an alarm/example is insufficient. |
| Command inventories | `supported_g_codes`, `supported_m_codes`, `unsupported_g_codes`, `unsupported_m_codes`, `optional_g_codes`, `optional_m_codes`, `machine_builder_m_codes`, `macro_commands` | lists | Every command remains informational until individually reviewed. |
| Cycles | `canned_cycles`, `threading_cycles`, `turning_cycles`, `drilling_cycles`, `probing_cycles` | lists | Controller, option, plane, and parameter dependencies apply. |
| Core templates | `safe_start_template`, `program_end_template` | string | Required/safety relevant; company standard preferred. Samples are not normative. |
| Program structure | `safe_start_commands`, `program_number_format`, `sequence_number_format`, `tool_change_template`, `spindle_start_template`, `coolant_start_template`, `work_offset_template`, `reference_return_template` | string | Safety relevant; distinguish required, recommended, example, syntax, and builder convention. |
| Program conventions | `optional_stop_behavior`, `block_delete_behavior`, `comment_format`, `subprogram_format`, `macro_call_format` | string | Company/controller sources; local policy and controller syntax have different authority. |

## Normalization

Allowlisted units are inch, mm, rpm, ipm, mm/min, degrees, degrees/min, kW,
hp, N·m, lb-ft, kg, and lb. Inch→mm, ipm→mm/min, and hp→kW conversions retain
the original value/unit and formula. Missing units produce ambiguity; unknown
units are rejected. Dimensionless parameters are never converted.

Required fields indicate review importance, not completeness or machine safety.
Safety-relevant fields still require exact-machine confirmation even at high
confidence.
