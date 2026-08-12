# G-POST Review Semantics

Support status is not review status.

Review status records `pending`, `accepted`, `accepted_with_edit`, `rejected`, or `deferred`. Only applicable mappings marked `required_for_v1` count in primary progress; they are reviewed only when accepted or accepted with an explicit override.

Machine identity, controller identity, axes, limits, work offsets, and profile-owned document relationships are inherited from the immutable machine-profile revision. They remain visible as provenance and do not require duplicate G-POST acceptance.
