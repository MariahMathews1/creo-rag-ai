# Toolpath coordinate assumptions

The visualization shows programmed coordinates as tracked by the existing parser. G90/G91 are honored. G53 is identified as machine-coordinate motion; known work-offset selection is identified as work context. Offset values are not available, so the service never transforms work coordinates into machine coordinates and warns when context is mixed or unknown.

For lathes, X is rendered exactly as programmed. Without an explicit machine-profile diameter/radius setting, `DIAMETER_RADIUS_MODE_UNKNOWN` is displayed and no division or multiplication occurs. A/B/C and CL tool-axis/MULTAX data remain metadata; Phase 9 does not implement machine kinematics.
