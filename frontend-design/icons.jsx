// Minimal lucide-like SVG icons. Stroke-based, 1.5px, 14px default.
const I = ({ children, size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{children}</svg>
);

const Ic = {
  Home:     (p) => <I {...p}><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></I>,
  Monitor:  (p) => <I {...p}><rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/></I>,
  Clipboard:(p) => <I {...p}><rect x="6" y="4" width="12" height="17" rx="1.5"/><rect x="9" y="2" width="6" height="4" rx="1"/></I>,
  Wrench:   (p) => <I {...p}><path d="M14.7 6.3a4 4 0 1 0 5 5L16 15l-7 7-3-3 7-7 3.7-5.7z"/></I>,
  Box:      (p) => <I {...p}><path d="M3 7l9-4 9 4v10l-9 4-9-4V7z"/><path d="M3 7l9 4 9-4M12 11v10"/></I>,
  User:     (p) => <I {...p}><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></I>,
  LogOut:   (p) => <I {...p}><path d="M15 4h4v16h-4"/><path d="M10 8l-4 4 4 4M6 12h10"/></I>,
  Search:   (p) => <I {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></I>,
  Bell:     (p) => <I {...p}><path d="M6 8a6 6 0 1 1 12 0v5l2 3H4l2-3z"/><path d="M10 20a2 2 0 0 0 4 0"/></I>,
  Sparkles: (p) => <I {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l3 3M15 15l3 3M6 18l3-3M15 9l3-3"/></I>,
  Plus:     (p) => <I {...p}><path d="M12 5v14M5 12h14"/></I>,
  Check:    (p) => <I {...p}><path d="M4 12l5 5L20 6"/></I>,
  X:        (p) => <I {...p}><path d="M6 6l12 12M18 6L6 18"/></I>,
  ChevR:    (p) => <I {...p}><path d="M9 6l6 6-6 6"/></I>,
  ChevD:    (p) => <I {...p}><path d="M6 9l6 6 6-6"/></I>,
  ChevUp:   (p) => <I {...p}><path d="M6 15l6-6 6 6"/></I>,
  ArrowR:   (p) => <I {...p}><path d="M5 12h14M13 6l6 6-6 6"/></I>,
  MoreH:    (p) => <I {...p}><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></I>,
  Filter:   (p) => <I {...p}><path d="M3 5h18l-7 9v6l-4-2v-4L3 5z"/></I>,
  Refresh:  (p) => <I {...p}><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 4v4h-4"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 20v-4h4"/></I>,
  Camera:   (p) => <I {...p}><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7l2-3h4l2 3"/><circle cx="12" cy="13" r="3.5"/></I>,
  FileText: (p) => <I {...p}><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7M9 9h3"/></I>,
  Image:    (p) => <I {...p}><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/></I>,
  Zap:      (p) => <I {...p}><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/></I>,
  Cpu:      (p) => <I {...p}><rect x="5" y="5" width="14" height="14" rx="1"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></I>,
  Clock:    (p) => <I {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></I>,
  Map:      (p) => <I {...p}><path d="M9 4l-6 2v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/></I>,
  AlertTri: (p) => <I {...p}><path d="M12 3l10 17H2z"/><path d="M12 10v4M12 18v.5"/></I>,
  Activity: (p) => <I {...p}><path d="M3 12h4l3-9 4 18 3-9h4"/></I>,
  Pencil:   (p) => <I {...p}><path d="M4 20h4L20 8l-4-4L4 16z"/></I>,
  Eye:      (p) => <I {...p}><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></I>,
  Package:  (p) => <I {...p}><path d="M3 7l9-4 9 4v10l-9 4-9-4V7z"/><path d="M3 7l9 4 9-4M12 11v10M7.5 4.5l9 4"/></I>,
  Hash:     (p) => <I {...p}><path d="M5 9h14M5 15h14M9 3L7 21M17 3l-2 18"/></I>,
  Command:  (p) => <I {...p}><path d="M6 3a3 3 0 1 1 3 3h6a3 3 0 1 1-3 3v6a3 3 0 1 1-3-3V9a3 3 0 1 1-3-3"/></I>,
  Dot:      (p) => <I {...p}><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/></I>,
  Play:     (p) => <I {...p}><path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/></I>,
};

window.Ic = Ic;
