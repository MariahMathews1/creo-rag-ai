"""Normalize existing parser output into programmed-motion visualization data."""
from __future__ import annotations

from collections import Counter
from math import acos, atan2, cos, hypot, pi, sin, sqrt
from typing import Any, Iterable

from app.services.toolpath.models import ToolpathBounds, ToolpathPoint, ToolpathResponse, ToolpathSegment

AXES = ("X", "Y", "Z", "A", "B", "C", "U", "V", "W")
PLANES = {"G17": ("X", "Y", "I", "J", "Z"), "G18": ("X", "Z", "I", "K", "Y"), "G19": ("Y", "Z", "J", "K", "X")}


def value(item: Any, name: str, default=None):
    if isinstance(item, dict): return item.get(name, default)
    return getattr(item, name, default)


def point(position: dict[str, float]) -> ToolpathPoint:
    return ToolpathPoint(**{axis.lower(): position.get(axis) for axis in AXES})


def coordinates(item: Any) -> dict:
    return value(item, "coordinates", value(item, "coordinates_json", {})) or {}


def state(item: Any, before=False) -> dict:
    raw = value(item, "state_before" if before else "modal_state", None)
    if raw is None: raw = value(item, "state_before_json" if before else "state_after_json", {})
    if isinstance(raw, dict): return raw
    return {name: getattr(raw, name, None) for name in ("motion_mode", "distance_mode", "plane", "units", "work_offset", "feed_rate", "spindle_speed", "active_tool")}


def target_position(current: dict[str, float], coords: dict, distance_mode: str | None) -> dict[str, float]:
    result = dict(current)
    for axis in AXES:
        if axis in coords: result[axis] = result.get(axis, 0.0) + coords[axis] if distance_mode == "G91" else coords[axis]
    return result


def arc_points(start: dict, end: dict, offsets: dict, radius_word: float | None, plane: str, clockwise: bool):
    ax1, ax2, off1, off2, helix_axis = PLANES.get(plane, PLANES["G17"])
    sx, sy, ex, ey = start.get(ax1, 0.0), start.get(ax2, 0.0), end.get(ax1, 0.0), end.get(ax2, 0.0)
    center = None
    if off1 in offsets or off2 in offsets:
        center = (sx + offsets.get(off1, 0.0), sy + offsets.get(off2, 0.0))
    elif radius_word is not None and (sx != ex or sy != ey):
        chord = hypot(ex - sx, ey - sy); r = abs(radius_word)
        if chord <= 2 * r:
            mx, my = (sx + ex) / 2, (sy + ey) / 2; h = sqrt(max(0.0, r*r - chord*chord/4))
            nx, ny = -(ey-sy)/chord, (ex-sx)/chord
            candidates = [(mx + nx*h, my + ny*h), (mx - nx*h, my - ny*h)]
            def sweep(c):
                a0, a1 = atan2(sy-c[1], sx-c[0]), atan2(ey-c[1], ex-c[0]); d = a1-a0
                if clockwise and d >= 0: d -= 2*pi
                if not clockwise and d <= 0: d += 2*pi
                return d
            preferred = [c for c in candidates if (abs(sweep(c)) > pi) == (radius_word < 0)]
            center = (preferred or candidates)[0]
    if center is None: return None, [], None
    cx, cy = center; r = hypot(sx-cx, sy-cy); a0, a1 = atan2(sy-cy, sx-cx), atan2(ey-cy, ex-cx); delta = a1-a0
    if clockwise and delta >= 0: delta -= 2*pi
    if not clockwise and delta <= 0: delta += 2*pi
    count = max(8, min(96, int(abs(delta) / (pi/24)) + 1)); samples=[]
    for index in range(count+1):
        ratio=index/count; pos=dict(start); pos[ax1]=cx+r*cos(a0+delta*ratio); pos[ax2]=cy+r*sin(a0+delta*ratio)
        if helix_axis in start or helix_axis in end: pos[helix_axis]=start.get(helix_axis,0)+(end.get(helix_axis,0)-start.get(helix_axis,0))*ratio
        samples.append(point(pos))
    center_pos=dict(start); center_pos[ax1]=cx; center_pos[ax2]=cy
    return point(center_pos), samples, r


def from_cl(records: Iterable[Any], alignment_by_cl: dict[int, tuple[int, list[str]]] | None = None) -> tuple[list[ToolpathSegment], list[dict]]:
    segments=[]; warnings=[]; position: dict[str,float]={}; active_tool=None; feed=None; spindle=None; operation=None; multiaxis=False
    for sequence, row in enumerate(records):
        command=(value(row,"command",value(row,"original_command","UNKNOWN")) or "UNKNOWN").upper(); coords=coordinates(row); line=int(value(row,"line",value(row,"line_number",sequence+1))); index=int(value(row,"index",value(row,"record_index",sequence)))
        before=value(row,"state_before",value(row,"state_before_json",{})) or {}; after=value(row,"state_after",value(row,"state_after_json",{})) or {}
        active_tool=value(row,"tool",value(row,"tool_number",active_tool)) or active_tool; feed=value(row,"feed",value(row,"feed_rate",feed)) or feed; spindle=value(row,"rpm",value(row,"spindle_speed",spindle)) or spindle; operation=value(row,"operation_name",operation) or operation
        multiaxis=bool(after.get("multi_axis_mode",before.get("multi_axis_mode",multiaxis)))
        motion="non_motion"; visual=True; start=end=center=None; samples=[]; radius=None
        if command=="LOADTL": motion="tool_change"
        elif command=="FROM": position={k:v for k,v in coords.items() if k in AXES}; motion="non_motion"
        elif command=="GOTO":
            start=point(position); position=target_position(position,coords,None); end=point(position); motion="rapid" if value(row,"motion",value(row,"motion_type"))=="rapid" else "linear"
        elif command in {"CIRCLE","ARC"}:
            motion="unsupported"; visual=False; warnings.append({"code":"UNRESOLVED_ARC","source":"cl","line":line,"message":"ARC GEOMETRY UNRESOLVED; endpoint is retained without a straight-line approximation."})
        elif command in {"RAPID","PPRINT","FEDRAT","SPINDL","COOLNT"}: motion="non_motion"
        elif command in {"CYCLE"}: motion="cycle"
        elif command not in {"FINI","COMMENT","TLAXIS"}: motion="unsupported"; visual=False
        link_id, aligned = (alignment_by_cl or {}).get(index,(None,[]))
        axis=after.get("tool_axis") or before.get("tool_axis") or {}
        segments.append(ToolpathSegment(id=f"cl-{index}",source_type="cl",source_record_id=index,source_line_start=line,source_line_end=line,operation_id=operation,tool_number=active_tool,motion_type=motion,start_point=start,end_point=end,center_point=center,radius=radius,path_points=samples,feed_rate=feed,spindle_speed=spindle,rapid=motion=="rapid",tool_axis=ToolpathPoint(x=axis.get("I"),y=axis.get("J"),z=axis.get("K")) if axis else None,alignment_link_id=link_id,aligned_segment_ids=aligned,sequence_index=sequence,visualizable=visual,unmatched=link_id is None,metadata_json={"command":command,"multiaxis":multiaxis}))
    if multiaxis: warnings.append({"code":"MULTIAXIS_VISUALIZATION_LIMITED","message":"Multiaxis motion is shown only as XYZ position; tool-axis orientation is metadata."})
    return segments,warnings


def from_gcode(blocks: Iterable[Any], finding_by_line: dict[int,list[int]] | None=None, alignment_by_gc: dict[int,tuple[int,list[str]]] | None=None) -> tuple[list[ToolpathSegment],list[dict],str]:
    segments=[]; warnings=[]; position:dict[str,float]={}; coordinate_contexts=set(); work_offset_seen=False
    for sequence,row in enumerate(blocks):
        line=int(value(row,"line",value(row,"line_number",sequence+1))); index=int(value(row,"index",value(row,"block_index",sequence))); codes=value(row,"g_codes",value(row,"g_codes_json",[])) or []; mcodes=value(row,"m_codes",value(row,"m_codes_json",[])) or []; coords=coordinates(row); after=state(row); before=state(row,True)
        mode=value(row,"motion",value(row,"motion_mode",None)) or after.get("motion_mode"); distance=after.get("distance_mode"); plane=value(row,"plane",None) or after.get("plane") or "G17"; work=value(row,"work_offset",None) or after.get("work_offset")
        if "G53" in codes: coordinate_contexts.add("machine")
        else: coordinate_contexts.add("work" if work else "unknown")
        work_offset_seen |= bool(work)
        start=point(position); end=None; center=None; samples=[]; radius=None; visual=True; motion="non_motion"
        if coords and mode in {"G00","G01","G02","G03"}:
            destination=target_position(position,coords,distance); end=point(destination)
            if mode=="G00": motion="rapid"
            elif mode=="G01": motion="linear"
            else:
                motion="arc_cw" if mode=="G02" else "arc_ccw"; offsets=value(row,"arc_offsets",{}) or {}; radius_word=value(row,"arc_radius",None)
                center,samples,radius=arc_points(position,destination,offsets,radius_word,plane,mode=="G02")
                if center is None: visual=False; warnings.append({"code":"UNRESOLVED_ARC","source":"gcode","line":line,"message":"ARC GEOMETRY UNRESOLVED; endpoint is retained without a straight-line approximation."})
            position=destination
        elif value(row,"tool",value(row,"tool_number",None)) is not None or "M06" in mcodes: motion="tool_change"
        elif any(code.startswith(("G8","G7")) for code in codes): motion="cycle"
        link_id,aligned=(alignment_by_gc or {}).get(index,(None,[])); finding_ids=(finding_by_line or {}).get(line,[])
        segments.append(ToolpathSegment(id=f"gcode-{index}",source_type="gcode",source_record_id=index,source_line_start=line,source_line_end=line,tool_number=value(row,"tool",value(row,"active_tool",value(row,"tool_number",after.get("active_tool")))),motion_type=motion,start_point=start if end else None,end_point=end,center_point=center,radius=radius,path_points=samples,plane=plane,feed_rate=value(row,"feed",value(row,"feed_rate",after.get("feed_rate"))),spindle_speed=value(row,"rpm",value(row,"spindle_speed",after.get("spindle_speed"))),rapid=motion=="rapid",arc_direction="cw" if motion=="arc_cw" else "ccw" if motion=="arc_ccw" else None,helical=bool(samples and PLANES.get(plane,PLANES["G17"])[4] in coords),alignment_link_id=link_id,aligned_segment_ids=aligned,finding_ids=finding_ids,sequence_index=sequence,visualizable=visual,unmatched=link_id is None,metadata_json={"g_codes":codes,"m_codes":mcodes,"work_offset":work,"distance_mode":distance,"units":after.get("units")}))
    context="mixed" if len(coordinate_contexts)>1 else next(iter(coordinate_contexts),"unknown")
    if not work_offset_seen: warnings.append({"code":"UNKNOWN_WORK_OFFSET","message":"Work offset transformation not available; raw programmed coordinates are shown."})
    return segments,warnings,context


def bounds_for(segments):
    points=[]
    for segment in segments:
        points.extend([p for p in [segment.start_point,segment.end_point,segment.center_point,*segment.path_points] if p])
    def range_for(axis):
        values=[getattr(p,axis) for p in points if getattr(p,axis) is not None]; return (min(values),max(values)) if values else (None,None)
    x,y,z=range_for("x"),range_for("y"),range_for("z"); return ToolpathBounds(min_x=x[0],max_x=x[1],min_y=y[0],max_y=y[1],min_z=z[0],max_z=z[1])


def compare_aligned_geometry(segments,tolerance=.001):
    by_id={s.id:s for s in segments}; counts=Counter()
    for segment in segments:
        if segment.source_type!="cl" or not segment.aligned_segment_ids: continue
        other=next((by_id.get(i) for i in segment.aligned_segment_ids if by_id.get(i)),None)
        if not other or not segment.end_point or not other.end_point: status="unresolved"
        else:
            pairs=[(getattr(segment.end_point,a),getattr(other.end_point,a)) for a in ("x","y","z")]
            if not any(left is not None or right is not None for left,right in pairs) or any((left is None)!=(right is None) for left,right in pairs):
                status="unresolved"
            else:
                values=[abs(left-right) for left,right in pairs if left is not None and right is not None]
                distance=sqrt(sum(v*v for v in values)); status="matching_geometry" if distance<=tolerance/10 else "within_tolerance" if distance<=tolerance else "different_geometry"
        segment.geometry_status=status; counts[status]+=1
    return {"aligned_motion_pairs":sum(counts.values()),**counts}


def build_toolpath(*,cl_records=(),gcode_blocks=(),machine_type="other",source="both",findings=(),alignment_by_cl=None,alignment_by_gc=None,tolerance=.001):
    segments=[]; warnings=[]; context="unknown"
    if source in {"cl","both"}: rows,notes=from_cl(cl_records,alignment_by_cl); segments+=rows; warnings+=notes
    finding_by_line: dict[int,list[int]] = {}
    for finding in findings:
        if value(finding,"line_number") is not None:
            finding_by_line.setdefault(int(value(finding,"line_number")),[]).append(int(value(finding,"id")))
    if source in {"gcode","both"}: rows,notes,context=from_gcode(gcode_blocks,finding_by_line,alignment_by_gc); segments+=rows; warnings+=notes
    if "lathe" in machine_type or "turning" in machine_type:
        default_view="XZ"; warnings.append({"code":"DIAMETER_RADIUS_MODE_UNKNOWN","message":"X interpretation: Unknown. Raw programmed X values are shown without diameter/radius conversion."})
    else: default_view="XY"
    comparison=compare_aligned_geometry(segments,tolerance)
    motions=Counter(s.motion_type for s in segments); tools={s.tool_number for s in segments if s.tool_number is not None}; operations={s.operation_id for s in segments if s.operation_id}
    summary={"segments":len(segments),"rapid":motions["rapid"],"feed":motions["linear"],"arcs":motions["arc_cw"]+motions["arc_ccw"],"tools":len(tools),"operations":len(operations),"unresolved_geometry":sum(not s.visualizable for s in segments),"visualization_simplified":len(segments)>10000}
    return ToolpathResponse(source=source,machine_type=machine_type,default_view=default_view,coordinate_context=context,segments=segments,bounds=bounds_for(segments),summary=summary,warnings=warnings,comparison_summary=comparison)
