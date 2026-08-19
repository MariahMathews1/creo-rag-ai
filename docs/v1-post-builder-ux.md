# V1 Post Builder UX

The Post Builder presents one machine-specific R&D post configuration as the primary object. Its workflow is:

`Machine → Machine Knowledge → Build Post → Review → Versions`

The landing page supports search, machine and status filters, Active/Archived/All views, sorting, and a consistent More menu. Rename and duplicate are reversible management actions. Archive is preferred for retention; permanent deletion is available only when the post is not part of a version lineage.

The workspace keeps governance visible without repeating large warnings. The primary tabs are Overview, Machine Knowledge, Build Post, Review, Versions, and Sources. Provider and internal implementation details are disclosed separately.

Internally, configuration areas remain section drafts. The primary interface calls them components or configuration areas so users understand they are assembling one post rather than creating unrelated products.

This interface does not claim native Creo G-POST compatibility. Native export remains a future, explicitly unconfigured capability.
