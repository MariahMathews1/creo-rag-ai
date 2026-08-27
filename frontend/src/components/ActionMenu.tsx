import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

export interface ActionMenuItem {
  label: string;
  to?: string;
  onSelect?: () => void;
  danger?: boolean;
  divider?: boolean;
  active?: boolean;
}

interface MenuPosition { top: number; left: number; minWidth: number; }

export function ActionMenu({ label, triggerLabel, items, align = "right", active = false }: { label: string; triggerLabel?: string; items: ActionMenuItem[]; align?: "left" | "right"; active?: boolean }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<MenuPosition>({ top: 0, left: 0, minWidth: 240 });
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  function placeMenu() {
    if (!trigger.current) return;
    const anchor = trigger.current.getBoundingClientRect();
    const width = Math.max(240, menu.current?.offsetWidth ?? 0);
    const height = menu.current?.offsetHeight ?? items.length * 38 + 12;
    const gap = 6; const edge = 8;
    const below = anchor.bottom + gap;
    const top = below + height <= window.innerHeight - edge || anchor.top < height + gap
      ? below : Math.max(edge, anchor.top - height - gap);
    const idealLeft = align === "left" ? anchor.left : anchor.right - width;
    const left = Math.min(Math.max(edge, idealLeft), Math.max(edge, window.innerWidth - width - edge));
    setPosition({ top, left, minWidth: width });
  }

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: MouseEvent) => {
      const node = event.target as Node;
      if (!trigger.current?.contains(node) && !menu.current?.contains(node)) setOpen(false);
    };
    const closeEscape = (event: KeyboardEvent) => { if (event.key === "Escape") { setOpen(false); trigger.current?.focus(); } };
    const reposition = () => placeMenu();
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      document.removeEventListener("mousedown", closeOutside); document.removeEventListener("keydown", closeEscape);
      window.removeEventListener("resize", reposition); window.removeEventListener("scroll", reposition, true);
    };
  }, [open, align, items.length]);
  useLayoutEffect(() => {
    if (!open) return;
    placeMenu();
    menu.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
  }, [open]);
  function keyDown(event: React.KeyboardEvent) {
    const entries = [...(menu.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? [])];
    const index = entries.indexOf(document.activeElement as HTMLElement);
    if (event.key === "ArrowDown") { event.preventDefault(); entries[(index + 1) % entries.length]?.focus(); }
    if (event.key === "ArrowUp") { event.preventDefault(); entries[(index - 1 + entries.length) % entries.length]?.focus(); }
    if (event.key === "Home") { event.preventDefault(); entries[0]?.focus(); }
    if (event.key === "End") { event.preventDefault(); entries.at(-1)?.focus(); }
  }
  const popover = open ? createPortal(<div ref={menu} className="action-menu-popover" role="menu" aria-label={label} onKeyDown={keyDown} style={{ top: position.top, left: position.left, minWidth: position.minWidth }}>{items.map((item) => item.to
    ? <Link role="menuitem" aria-current={item.active ? "page" : undefined} tabIndex={-1} className={`${item.active ? "active" : ""} ${item.danger ? "danger" : ""} ${item.divider ? "divider" : ""}`} key={item.label} to={item.to} onClick={() => setOpen(false)}>{item.label}</Link>
    : <button role="menuitem" aria-current={item.active ? "page" : undefined} tabIndex={-1} className={`${item.active ? "active" : ""} ${item.danger ? "danger" : ""} ${item.divider ? "divider" : ""}`} key={item.label} onClick={() => { setOpen(false); item.onSelect?.(); }}>{item.label}</button>)}</div>, document.body) : null;
  return <div className={`action-menu align-${align}`}>
    <button ref={trigger} type="button" className={`button tertiary action-menu-trigger ${active ? "active" : ""}`} aria-label={label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((value) => !value)}>{triggerLabel || label}<span aria-hidden="true">⌄</span></button>
    {popover}
  </div>;
}
