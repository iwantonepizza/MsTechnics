const MsLogo = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <rect x="2" y="2" width="20" height="20" rx="4" fill="var(--brand)"/>
    <path d="M6 17V8l3 5 3-5v9M14 17V8h3a2.5 2.5 0 0 1 0 5h-3" stroke="var(--brand-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const NavItem = ({ icon: Icon, label, active, disabled, count }) => (
  <button className="nav-item" disabled={disabled} data-active={active || undefined}>
    <Icon size={14} />
    <span>{label}</span>
    {count != null && <span className="nav-count">{count}</span>}
  </button>
);

const Header = ({ active = 'service', crumb }) => {
  const { Ic } = window;
  return (
    <header className="app-header">
      <style>{`
        .app-header {
          height: var(--h-header);
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          gap: 20px;
          padding: 0 16px;
          background: var(--bg-1);
          border-bottom: 1px solid var(--border-subtle);
        }
        .brand { display: flex; align-items: center; gap: 10px; padding-right: 14px; border-right: 1px solid var(--border-subtle); height: 28px; }
        .brand-name { font-weight: 600; letter-spacing: -0.01em; font-size: 13px; }
        .brand-name .tech { color: var(--fg-mute); font-weight: 500; }
        .nav { display: flex; align-items: center; gap: 2px; }
        .nav-item {
          display: inline-flex; align-items: center; gap: 7px;
          height: 28px; padding: 0 10px; border-radius: var(--r-md);
          background: transparent; border: 1px solid transparent; color: var(--fg-dim);
          font: 500 12.5px/1 var(--font-sans); cursor: pointer;
          transition: background 100ms linear, color 100ms linear;
        }
        .nav-item:hover { background: var(--bg-2); color: var(--fg); }
        .nav-item[data-active] { background: var(--bg-3); color: var(--fg); border-color: var(--border-subtle); }
        .nav-item:disabled { color: var(--fg-faint); cursor: not-allowed; }
        .nav-item:disabled:hover { background: transparent; color: var(--fg-faint); }
        .nav-count {
          min-width: 16px; height: 16px; padding: 0 4px;
          display: inline-flex; align-items: center; justify-content: center;
          border-radius: 8px; background: var(--accent-faint); color: var(--accent);
          font: 500 10px/1 var(--font-mono); margin-left: 2px;
        }
        .crumb { display: flex; align-items: center; gap: 8px; color: var(--fg-mute); font-size: 12.5px; }
        .crumb .sep { color: var(--fg-faint); }
        .crumb .cur { color: var(--fg); font-weight: 500; }
        .user-cluster { display: flex; align-items: center; gap: 4px; }
        .sse-dot { width: 7px; height: 7px; border-radius: 999px; background: var(--ok); box-shadow: 0 0 0 3px var(--ok-faint); }
        .user-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px 4px 4px; border-radius: 999px; background: var(--bg-2); }
        .user-ava { width: 20px; height: 20px; border-radius: 999px; background: var(--accent-faint); color: var(--accent); display: inline-flex; align-items: center; justify-content: center; font: 600 10px/1 var(--font-sans); }
      `}</style>

      <div style={{display:'flex', alignItems:'center', gap: 16}}>
        <div className="brand">
          <MsLogo />
          <div className="brand-name">MsTechnics <span className="tech">/ ops</span></div>
        </div>
        <nav className="nav">
          <NavItem icon={Ic.Home}      label="Главная"    active={active==='home'} />
          <NavItem icon={Ic.Monitor}   label="Мониторинг" active={active==='monitoring'} count={3} />
          <NavItem icon={Ic.Clipboard} label="Контроль"   active={active==='control'} disabled />
          <NavItem icon={Ic.Wrench}    label="Сервис"     active={active==='service'} count={12} />
          <NavItem icon={Ic.Box}       label="ЗИП"        active={active==='zip'} />
        </nav>
      </div>

      <div className="crumb">
        {crumb}
      </div>

      <div className="user-cluster">
        <button className="btn btn-ghost sm" title="Поиск · /">
          <Ic.Search size={13}/> <span style={{color:'var(--fg-mute)'}}>Поиск</span>
          <span className="kbd" style={{marginLeft:4}}>/</span>
        </button>
        <span className="vsep"/>
        <button className="icon-btn" title="SSE подключён">
          <span className="sse-dot"/>
        </button>
        <button className="icon-btn" title="Уведомления"><Ic.Bell/></button>
        <button className="icon-btn" title="Shortcut-help · ?"><Ic.Command/></button>
        <span className="vsep"/>
        <div className="user-chip">
          <div className="user-ava">АП</div>
          <span style={{fontSize:12.5,color:'var(--fg-dim)'}}>Артём П.</span>
          <Ic.ChevD size={12}/>
        </div>
      </div>
    </header>
  );
};

window.Header = Header;
window.MsLogo = MsLogo;
