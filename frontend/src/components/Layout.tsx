import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", glyph: "▦" },
  { to: "/machines", label: "Machines", glyph: "◆" },
  { to: "/documents", label: "Documents", glyph: "▤" },
  { to: "/analysis/new", label: "Analysis", glyph: "+" },
  { to: "/gpost", label: "G-POST Generator", glyph: "⚙" },
  { to: "/manual-assistant", label: "Manual Assistant", glyph: "?" },
];

export function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">C</span>
          <div>
            <strong>Creo NC</strong>
            <small>Post Assistant</small>
          </div>
        </div>
        <nav aria-label="Primary navigation">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <span aria-hidden="true">{link.glyph}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" />
          Local proof of concept
          <small>Decision support only</small>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
