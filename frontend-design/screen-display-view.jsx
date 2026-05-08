// Display View — Сервис · v2
// Fixes:
//  (1) Adaptive grid aspect-ratio {cols}/{rows}, max-width up to 1100 for >10 cols
//  (2) ID chips use CSS vars --chip-bg/--chip-fg (prod: from DB hex)
//  (3) Application row comment: 3-line clamp + hover popover with full text
//  (4) Timeline rows clickable → open application modal

const DisplayView = () => {
  const { Ic, Header } = window;
  const [selectedCell, setSelectedCell] = React.useState(27);
  const [activeTab, setActiveTab] = React.useState('received');
  const [hoverRow, setHoverRow] = React.useState(null);
  const [modalApp, setModalApp] = React.useState(null);

  // Configure display geometry here; could come from API
  const ROWS = 10, COLS = 10;
  const maxGridWidth = COLS > 10 ? 1100 : 800;

  const cells = React.useMemo(() => {
    const seed = {
      3:'work', 7:'work', 14:'warn', 22:'work', 25:'work',
      27:'err', 31:'work', 34:'info', 41:'work', 44:'warn',
      55:'work', 61:'work', 67:'warn', 71:'err', 82:'work',
      84:'info', 92:'work', 95:'empty', 98:'work'
    };
    return Array.from({length: ROWS*COLS}, (_, i) => ({
      idx: i,
      pos: String(i+1).padStart(2,'0'),
      status: seed[i] ?? 'work',
      panel: seed[i] === 'empty' ? null : `COLOSSEUM-${String(i+3).padStart(2,'0')}`
    }));
  }, []);

  const cell = cells[selectedCell];

  // Full comment map for popover on row hover
  const fullComments = {
    'ID-4567': 'Моргает верхний ряд — проверить шлейф. После вчерашней замены блока питания проблема вернулась через 4 часа. Подозрение на окисление контактов в разъёме на задней крышке. Нужна полная ревизия соединений.',
    'ID-4566': 'Битый чип, полная замена. При прогреве плывёт красный канал, уходит в жёлтый. Менять модуль целиком, ремонт на месте не поможет — это заводской дефект драйвера.',
    'ID-4565': 'Ушла в сервис, жду запчасть. Поставщик обещал привезти в четверг. После получения — диагностика и замена конденсаторов на плате питания.',
    'ID-4564': 'Моргает при нагреве > 40°C. Проявляется после 2-3 часов работы на полной яркости. Скорее всего, деградировал один из конденсаторов в цепи питания драйвера.',
    'ID-4563': 'Полная замена модуля, битый драйвер. На стенде подтвердилось — драйвер не держит нагрузку выше 60%. Модуль списывается в unrecoverable.',
    'ID-4561': 'Моргает при нагреве. Похоже, тот же дефект, что и на COLOSSEUM-74. Возможно, партия от одного поставщика. Нужно проверить партию по серийным номерам.',
    'ID-4560': 'Требуется диагностика. Мониторщик сообщил про периодические чёрные квадраты. На месте воспроизвести не удалось. Поставить на стенд и гонять под нагрузкой.',
    'ID-4559': 'Драйвер плывёт по цвету. Классический симптом — менять модуль.',
  };

  return (
    <div className="ds-view">
      <style>{`
        .ds-view {
          width: 1920px; height: 1080px;
          background: var(--bg-0);
          display: flex; flex-direction: column;
          overflow: hidden; font-size: 13px;
        }

        .title-bar {
          height: 44px; display: grid; grid-template-columns: 1fr auto;
          align-items: center; padding: 0 16px;
          border-bottom: 1px solid var(--border-subtle); background: var(--bg-0);
        }
        .tb-left { display: flex; align-items: center; gap: 10px; }
        .tb-title { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
        .tb-meta { display:flex; gap: 10px; color: var(--fg-mute); font-size: 12px; }
        .tb-meta .mono { color: var(--fg-dim); }
        .tb-right { display:flex; align-items:center; gap:4px; }

        .ds-body {
          display: grid;
          grid-template-columns: 1fr 360px 320px;
          flex: 1; min-height: 0;
        }

        .grid-col {
          padding: 14px 16px 0;
          display: flex; flex-direction: column;
          min-height: 0;
          border-right: 1px solid var(--border-subtle);
        }
        .grid-head { display:flex; align-items:center; justify-content:space-between; padding-bottom: 10px; }
        .grid-legend { display:flex; gap:12px; align-items:center; font-size: 11.5px; color: var(--fg-mute); }
        .legend-item { display:flex; gap:5px; align-items:center; }
        .legend-sw { width: 10px; height: 10px; border-radius: 2px; }

        .display-wrap { flex: 1; min-height: 0; display: grid; place-items: center; padding: 16px 0; }
        .display {
          width: 100%;
          max-width: ${maxGridWidth}px;
          aspect-ratio: ${COLS} / ${ROWS};
          background: var(--bg-1);
          border: 1px solid var(--border);
          border-radius: var(--r-md);
          padding: 10px;
          display: grid;
          grid-template-columns: 32px 1fr;
          grid-template-rows: 24px 1fr;
          gap: 4px;
        }
        .rulers-top { display: grid; grid-template-columns: repeat(${COLS}, 1fr); gap: 3px;
          font-family: var(--font-mono); font-size: 9px; color: var(--fg-faint); }
        .rulers-top span { display: flex; align-items: center; justify-content: center; }
        .rulers-left { display: grid; grid-template-rows: repeat(${ROWS}, 1fr); gap: 3px;
          font-family: var(--font-mono); font-size: 9px; color: var(--fg-faint); }
        .rulers-left span { display: flex; align-items: center; justify-content: center; }
        .cells {
          display: grid;
          grid-template-columns: repeat(${COLS}, 1fr);
          grid-template-rows: repeat(${ROWS}, 1fr);
          gap: 3px;
        }
        .cell {
          border-radius: 3px;
          cursor: pointer;
          display: flex; align-items: flex-end; justify-content: flex-start;
          padding: 3px 4px;
          font: 500 9px/1 var(--font-mono);
          transition: box-shadow 80ms linear, transform 80ms linear;
        }
        .cell[data-s=work]  { background: var(--bg-3); color: var(--fg-faint); }
        .cell[data-s=warn]  { background: var(--warn); color: var(--warn-ink); }
        .cell[data-s=err]   { background: var(--err); color: var(--err-ink); }
        .cell[data-s=info]  { background: var(--info); color: var(--info-ink); }
        .cell[data-s=empty] { background: transparent; border: 1px dashed var(--border-subtle); color: var(--fg-faint); }
        .cell:hover { box-shadow: inset 0 0 0 1px var(--fg-dim); }
        .cell[data-sel] { box-shadow: inset 0 0 0 2px var(--accent), 0 0 0 2px var(--bg-0); transform: scale(1.02); z-index: 2; }

        .grid-foot {
          display: flex; justify-content: space-between; align-items: center;
          padding: 8px 0 10px; border-top: 1px solid var(--border-subtle);
          color: var(--fg-mute); font-size: 11.5px;
        }
        .grid-foot .mono { color: var(--fg-dim); }

        .pnl-col {
          padding: 14px 16px; border-right: 1px solid var(--border-subtle);
          display: flex; flex-direction: column; min-height: 0; overflow-y: auto;
        }
        .pnl-head { display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px; }
        .pnl-title-row { display: flex; align-items: center; gap: 8px; }
        .pnl-title { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
        .pnl-sub { font-size: 11.5px; color: var(--fg-mute); margin-top: 2px; }

        .kv { display: grid; grid-template-columns: 92px 1fr; gap: 6px 12px; margin: 10px 0 14px; }
        .kv dt { font-size: 11px; color: var(--fg-mute); }
        .kv dd { margin: 0; font-size: 12.5px; color: var(--fg); }

        .subtitle {
          display: flex; justify-content: space-between; align-items: center;
          font-size: 11px; color: var(--fg-mute);
          text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500;
          font-family: var(--font-mono);
          margin: 14px 0 8px; padding-top: 12px; border-top: 1px solid var(--border-subtle);
        }
        .subtitle:first-of-type { padding-top: 0; border-top: none; }

        .comment-box {
          background: var(--bg-1); border: 1px solid var(--border-subtle);
          border-radius: var(--r-md); padding: 10px 12px;
          font-size: 12.5px; color: var(--fg-dim); line-height: 1.5;
        }

        .action-row { display: flex; gap: 6px; flex-wrap: wrap; }

        .rail { padding: 14px 16px; display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }

        /* Timeline rows — clickable */
        .tl-item {
          display: grid; grid-template-columns: 60px 1fr; gap: 8px;
          padding: 8px 10px; margin: 0 -10px;
          border-radius: var(--r-md);
          cursor: pointer;
          transition: background 80ms linear;
        }
        .tl-item:hover { background: var(--bg-2); }
        .tl-item.has-app:hover { background: var(--accent-faint); }
        .tl-time { font-family: var(--font-mono); font-size: 10.5px; color: var(--fg-mute); padding-top: 2px; }
        .tl-body { font-size: 12px; color: var(--fg-dim); line-height: 1.45; }
        .tl-body b { color: var(--fg); font-weight: 500; }
        .tl-app-ref { color: var(--accent); }

        /* Applications table */
        .apps {
          border-top: 1px solid var(--border-subtle);
          background: var(--bg-0);
          display: flex; flex-direction: column;
          min-height: 360px; max-height: 360px;
        }
        .apps-head {
          display: flex; align-items: center; justify-content: space-between;
          padding: 8px 16px; border-bottom: 1px solid var(--border-subtle);
          background: var(--bg-1);
        }
        .apps-tabs { display: flex; gap: 2px; align-items: center; }
        .tab {
          display: inline-flex; align-items: center; gap: 6px;
          height: 28px; padding: 0 10px; border-radius: var(--r-md);
          background: transparent; border: none; color: var(--fg-mute);
          font: 500 12.5px/1 var(--font-sans); cursor: pointer;
        }
        .tab:hover { color: var(--fg); background: var(--bg-2); }
        .tab[data-on] { color: var(--fg); background: var(--bg-3); }
        .tab-count {
          min-width: 16px; height: 16px; padding: 0 4px;
          display: inline-flex; align-items: center; justify-content: center;
          border-radius: 8px; background: var(--bg-4); color: var(--fg-dim);
          font: 500 10px/1 var(--font-mono);
        }
        .tab[data-on] .tab-count { background: var(--accent-faint); color: var(--accent); }
        .apps-filters { display:flex; align-items:center; gap: 6px; }

        .apps-table { flex:1; overflow-y: auto; }
        .tr-head, .tr {
          display: grid;
          grid-template-columns: 100px 60px 1fr 140px 140px 90px 80px 28px;
          gap: 14px; align-items: start;
          padding: 0 16px;
        }
        .tr-head {
          height: 26px; align-items: center;
          font: 500 10px/1 var(--font-mono);
          text-transform: uppercase; letter-spacing: 0.08em;
          color: var(--fg-mute);
          background: var(--bg-0); position: sticky; top: 0; z-index: 1;
          border-bottom: 1px solid var(--border-subtle);
        }
        .tr {
          min-height: 60px;
          padding-top: 10px; padding-bottom: 10px;
          border-bottom: 1px solid var(--border-subtle);
          font-size: 12.5px; cursor: pointer;
          transition: background 80ms linear;
          position: relative;
        }
        .tr:hover { background: var(--bg-1); }
        .tr[data-sel] { background: var(--accent-faint); }
        .tr .muted { color: var(--fg-mute); }

        /* 3-line clamp for comment */
        .tr-body {
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
          line-height: 1.4;
          font-size: 12.5px;
        }
        .tr-body .title { color: var(--fg); font-family: var(--font-mono); }
        .tr-body .rest { color: var(--fg-mute); }

        /* Popover on row hover */
        .tr-popover {
          position: absolute;
          left: 196px; /* past ID + cell cols */
          top: calc(100% - 6px);
          z-index: 20;
          pointer-events: none;
        }

        .hk-row { display: flex; justify-content: space-between; padding: 6px 16px; border-top: 1px solid var(--border-subtle); background: var(--bg-1); font-size: 11px; color: var(--fg-mute); }
        .hk-group { display: flex; gap: 14px; align-items: center; }
        .hk { display: inline-flex; align-items: center; gap: 4px; }

        /* Modal */
        .modal-overlay {
          position: absolute; inset: 0; background: rgba(0,0,0,0.55);
          display: flex; align-items: center; justify-content: center;
          z-index: 100;
        }
        .modal {
          width: 560px; background: var(--bg-1);
          border: 1px solid var(--border); border-radius: var(--r-lg);
          box-shadow: var(--shadow-modal);
          display: flex; flex-direction: column;
        }
        .modal-head {
          display: flex; justify-content: space-between; align-items: center;
          padding: 14px 18px; border-bottom: 1px solid var(--border-subtle);
        }
        .modal-body { padding: 16px 18px; }
        .modal-foot { padding: 12px 18px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: flex-end; gap: 6px; }
      `}</style>

      <Header active="service" crumb={
        <>
          <Ic.Map size={13}/>
          <span>Ижевск</span>
          <Ic.ChevR size={11} className="sep"/>
          <span className="cur">Колизей-Большой</span>
          <span className="mono" style={{color:'var(--fg-faint)', marginLeft:2}}>/service/izhevsk/colosseum-big</span>
        </>
      }/>

      <div className="title-bar">
        <div className="tb-left">
          <div className="tb-title">Сервис · Колизей-Большой</div>
          <span className="pill pill-ok"><span className="dot"/>онлайн</span>
          <div className="tb-meta">
            <span>{ROWS}×{COLS}</span><span>·</span>
            <span className="mono">98/{ROWS*COLS}</span>
            <span>ячеек занято</span><span>·</span>
            <span className="mono">UTC+3</span>
          </div>
        </div>
        <div className="tb-right">
          <button className="btn btn-ghost sm"><Ic.Image/> Электросхема</button>
          <button className="btn btn-ghost sm"><Ic.FileText/> Проект</button>
          <button className="btn btn-ghost sm"><Ic.Camera/> Камера</button>
          <span className="vsep"/>
          <button className="btn btn-secondary sm"><Ic.Box size={12}/> ЗИП <Ic.ArrowR size={11}/></button>
          <button className="icon-btn" title="Обновить"><Ic.Refresh/></button>
          <button className="icon-btn" title="Ещё"><Ic.MoreH/></button>
        </div>
      </div>

      <div className="ds-body">
        <div className="grid-col scroll">
          <div className="grid-head">
            <div className="label">Сетка экрана · {ROWS}×{COLS}</div>
            <div className="grid-legend">
              <div className="legend-item"><span className="legend-sw" style={{background:'var(--bg-3)'}}/> Работает</div>
              <div className="legend-item"><span className="legend-sw" style={{background:'var(--warn)'}}/> Моргает</div>
              <div className="legend-item"><span className="legend-sw" style={{background:'var(--err)'}}/> Сломана</div>
              <div className="legend-item"><span className="legend-sw" style={{background:'var(--info)'}}/> В сервисе</div>
              <div className="legend-item"><span className="legend-sw" style={{background:'transparent',border:'1px dashed var(--border)'}}/> Пусто</div>
            </div>
          </div>

          <div className="display-wrap">
            <div className="display">
              <div/>
              <div className="rulers-top">
                {Array.from({length:COLS}).map((_,i)=><span key={i}>{String(i+1).padStart(2,'0')}</span>)}
              </div>
              <div className="rulers-left">
                {Array.from({length:ROWS}).map((_,i)=><span key={i}>{String.fromCharCode(65+i)}</span>)}
              </div>
              <div className="cells">
                {cells.map(c => (
                  <div key={c.idx} className="cell" data-s={c.status}
                    data-sel={c.idx===selectedCell || undefined}
                    onClick={()=>setSelectedCell(c.idx)}
                    title={c.panel ? `${c.panel} · ${c.pos}` : `слот ${c.pos} · пусто`}>
                    {c.pos}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid-foot">
            <div>
              <span className="mono">{cells.filter(c=>c.status==='err').length}</span> сломано ·
              <span className="mono"> {cells.filter(c=>c.status==='warn').length}</span> моргает ·
              <span className="mono"> {cells.filter(c=>c.status==='info').length}</span> в сервисе
            </div>
            <div>
              Выбрано: <span className="mono" style={{color:'var(--accent)'}}>cell {cell.pos}</span>
              {cell.panel && <> · <span className="mono">{cell.panel}</span></>}
            </div>
          </div>
        </div>

        <div className="pnl-col scroll">
          <div className="pnl-head">
            <div>
              <div className="pnl-title-row">
                <span className="pnl-title">{cell.panel || 'Пустой слот'}</span>
                <span className="pill pill-err"><span className="dot"/>сломана</span>
              </div>
              <div className="pnl-sub">
                <span className="mono">cell {cell.pos}</span> · <span className="mono">row 3 · col 8</span>
              </div>
            </div>
            <div style={{display:'flex',gap:2}}>
              <button className="icon-btn" title="История"><Ic.Clock/></button>
              <button className="icon-btn" title="Ещё"><Ic.MoreH/></button>
            </div>
          </div>

          <dl className="kv">
            <dt>ID панели</dt><dd className="mono">P-COLOSSEUM-30</dd>
            <dt>Модель</dt><dd>LED P2.5 · 160×160 · HD</dd>
            <dt>Состояние</dt><dd><span className="pill pill-err"><span className="dot"/>broken · битый чип</span></dd>
            <dt>Отдел</dt><dd>В экране · сервис</dd>
            <dt>Принята</dt><dd className="mono">12 апр 2024 · 09:14</dd>
          </dl>

          <div className="subtitle">
            Комментарий
            <button className="icon-btn" title="Редактировать"><Ic.Pencil size={12}/></button>
          </div>
          <div className="comment-box">
            После замены шлейфа моргает верхний ряд диодов. Пробовал менять блок питания — без эффекта.
            Похоже, битый драйвер. Нужна полная замена модуля.
          </div>

          <div className="subtitle">Действия с панелью</div>
          <div className="action-row" style={{marginBottom:6}}>
            <button className="btn btn-primary"><Ic.Wrench size={12}/> Взять в работу <span className="kbd" style={{marginLeft:4,background:'rgba(0,0,0,.2)',color:'rgba(0,0,0,.55)',borderColor:'transparent'}}>R</span></button>
            <button className="btn btn-secondary"><Ic.ArrowR size={12}/> Снять</button>
          </div>
          <div className="action-row">
            <button className="btn btn-ghost sm"><Ic.Box size={12}/> В ЗИП</button>
            <button className="btn btn-ghost sm"><Ic.User size={12}/> На руки</button>
            <button className="btn btn-ghost sm"><Ic.Wrench size={12}/> В сервис</button>
          </div>

          <div className="subtitle">Активные заявки · 2</div>
          <div style={{display:'flex', flexDirection:'column', gap:6}}>
            <div style={{display:'grid', gridTemplateColumns:'auto 1fr auto', gap:8, alignItems:'center', padding:'8px 10px', background:'var(--bg-1)', border:'1px solid var(--border-subtle)', borderRadius:'var(--r-md)', cursor:'pointer'}}
                 onClick={()=>setModalApp('ID-4567')}>
              <span className="idchip" style={{'--chip-bg':'var(--warn)','--chip-fg':'var(--warn-ink)'}}>ID-4567</span>
              <div style={{fontSize:12.5, color:'var(--fg-dim)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>Моргает верхний ряд · проверить шлейф</div>
              <span className="pill pill-warn"><span className="dot"/>в работе</span>
            </div>
            <div style={{display:'grid', gridTemplateColumns:'auto 1fr auto', gap:8, alignItems:'center', padding:'8px 10px', background:'var(--bg-1)', border:'1px solid var(--border-subtle)', borderRadius:'var(--r-md)', cursor:'pointer'}}
                 onClick={()=>setModalApp('ID-4566')}>
              <span className="idchip" style={{'--chip-bg':'var(--info-faint)','--chip-fg':'var(--info)'}}>ID-4566</span>
              <div style={{fontSize:12.5, color:'var(--fg-dim)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>Битый чип, полная замена</div>
              <span className="pill pill-info"><span className="dot"/>в сервисе</span>
            </div>
          </div>
        </div>

        <div className="rail scroll">
          <div className="subtitle">История места · cell {cell.pos}</div>
          <div>
            <div className="tl-item has-app" onClick={()=>setModalApp('ID-4567')}>
              <div className="tl-time">сегодня<br/>14:22</div>
              <div className="tl-body"><b>Артём П.</b> создал заявку <span className="mono tl-app-ref">ID-4567</span> · «моргает верхний ряд»</div>
            </div>
            <div className="tl-item" onClick={()=>{}}>
              <div className="tl-time">сегодня<br/>11:05</div>
              <div className="tl-body"><b>Катя С.</b> отметила панель как <span style={{color:'var(--warn)'}}>problem</span></div>
            </div>
            <div className="tl-item" onClick={()=>{}}>
              <div className="tl-time">12 апр<br/>09:14</div>
              <div className="tl-body"><b>Миша К.</b> установил панель <span className="mono" style={{color:'var(--fg)'}}>P-COLOSSEUM-30</span></div>
            </div>
            <div className="tl-item has-app" onClick={()=>setModalApp('ID-4412')}>
              <div className="tl-time">08 апр<br/>16:30</div>
              <div className="tl-body"><b>Артём П.</b> снял панель по заявке <span className="mono tl-app-ref">ID-4412</span> · отправлена в сервис</div>
            </div>
          </div>

          <div className="subtitle">История панели · <span className="mono" style={{color:'var(--fg-dim)', textTransform:'none', letterSpacing:0}}>P-COLOSSEUM-30</span></div>
          <div>
            <div className="tl-item has-app" onClick={()=>setModalApp('ID-4567')}>
              <div className="tl-time">сегодня<br/>11:05</div>
              <div className="tl-body">Смена состояния · <span style={{color:'var(--ok)'}}>work</span> → <span style={{color:'var(--warn)'}}>problem</span> по заявке <span className="mono tl-app-ref">ID-4567</span></div>
            </div>
            <div className="tl-item" onClick={()=>{}}>
              <div className="tl-time">12 апр<br/>09:14</div>
              <div className="tl-body">Перемещена <span style={{color:'var(--fg-mute)'}}>zip</span> → <span style={{color:'var(--fg)'}}>monitor</span> · cell {cell.pos}</div>
            </div>
            <div className="tl-item" onClick={()=>{}}>
              <div className="tl-time">28 мар<br/>14:50</div>
              <div className="tl-body">Принята в ЗИП · поставщик <b>VNNOX</b></div>
            </div>
          </div>
        </div>
      </div>

      {/* Applications */}
      <div className="apps">
        <div className="apps-head">
          <div className="apps-tabs">
            {[['received','Запросы',3],['at_work','В работе',5],['complete','Выполненные',12],['archive','Архив',84],['unable','Невозможные',2],['history','История',null],['all','Все',106]].map(([k,l,c])=>(
              <button key={k} className="tab" data-on={activeTab===k || undefined} onClick={()=>setActiveTab(k)}>
                {l}{c!=null && <span className="tab-count">{c}</span>}
              </button>
            ))}
          </div>
          <div className="apps-filters">
            <button className="btn btn-ghost sm"><Ic.Filter size={12}/> Все исполнители</button>
            <button className="btn btn-ghost sm">по дате убыв. <Ic.ChevD size={11}/></button>
            <span className="vsep"/>
            <button className="btn btn-primary sm"><Ic.Plus size={12}/> Новая заявка</button>
          </div>
        </div>

        <div className="apps-table scroll">
          <div className="tr-head">
            <span>ID</span><span>Ячейка</span><span>Панель · комментарий</span>
            <span>Исполнитель</span><span>Создана</span><span>Обновлена</span><span>Статус</span><span/>
          </div>
          {[
            {id:'ID-4567', slot:'27', panel:'COLOSSEUM-30', comment:fullComments['ID-4567'], user:'Артём П.', created:'22 апр · 14:22', updated:'5 мин назад', stat:'warn', statLbl:'в работе', sel:true, chipBg:'var(--warn)', chipFg:'var(--warn-ink)'},
            {id:'ID-4566', slot:'34', panel:'COLOSSEUM-37', comment:fullComments['ID-4566'], user:'Артём П.', created:'22 апр · 13:40', updated:'22 мин назад', stat:'info', statLbl:'в сервисе', chipBg:'var(--info-faint)', chipFg:'var(--info)'},
            {id:'ID-4565', slot:'14', panel:'COLOSSEUM-17', comment:fullComments['ID-4565'], user:'—', created:'22 апр · 12:08', updated:'2 ч назад', stat:'info', statLbl:'в сервисе', chipBg:'var(--info-faint)', chipFg:'var(--info)'},
            {id:'ID-4564', slot:'71', panel:'COLOSSEUM-74', comment:fullComments['ID-4564'], user:'Миша К.', created:'21 апр · 16:02', updated:'вчера 18:44', stat:'warn', statLbl:'моргает', chipBg:'var(--warn)', chipFg:'var(--warn-ink)'},
            {id:'ID-4563', slot:'44', panel:'COLOSSEUM-47', comment:fullComments['ID-4563'], user:'Артём П.', created:'21 апр · 10:18', updated:'вчера 14:12', stat:'info', statLbl:'в сервисе', chipBg:'var(--info-faint)', chipFg:'var(--info)'},
            {id:'ID-4561', slot:'67', panel:'COLOSSEUM-70', comment:fullComments['ID-4561'], user:'—', created:'20 апр · 08:44', updated:'2 дня назад', stat:'warn', statLbl:'моргает', chipBg:'var(--warn)', chipFg:'var(--warn-ink)'},
            {id:'ID-4560', slot:'03', panel:'COLOSSEUM-06', comment:fullComments['ID-4560'], user:'Миша К.', created:'20 апр · 08:10', updated:'3 дня назад', stat:'warn', statLbl:'моргает', chipBg:'var(--warn)', chipFg:'var(--warn-ink)'},
          ].map((r)=>(
            <div key={r.id} className="tr" data-sel={r.sel || undefined}
                 onMouseEnter={()=>setHoverRow(r.id)} onMouseLeave={()=>setHoverRow(null)}
                 onClick={()=>setModalApp(r.id)}>
              <span><span className="idchip" style={{'--chip-bg':r.chipBg, '--chip-fg':r.chipFg}}>{r.id}</span></span>
              <span className="mono muted" style={{paddingTop:2}}>{r.slot}</span>
              <div className="tr-body">
                <span className="title">{r.panel}</span>
                <span className="rest"> · {r.comment}</span>
              </div>
              <span style={{paddingTop:2}}>{r.user === '—' ? <span className="muted">—</span> : r.user}</span>
              <span className="mono muted" style={{paddingTop:2}}>{r.created}</span>
              <span className="muted" style={{paddingTop:2}}>{r.updated}</span>
              <span style={{paddingTop:1}}>
                <span className={`pill pill-${r.stat}`}><span className="dot"/>{r.statLbl}</span>
              </span>
              <span style={{paddingTop:1}}>
                <button className="icon-btn" title="Ещё" onClick={(e)=>e.stopPropagation()}><Ic.MoreH/></button>
              </span>

              {hoverRow === r.id && (
                <div className="tr-popover">
                  <div className="popover">
                    <div className="popover-title">{r.id} · {r.panel} · cell {r.slot}</div>
                    <div>{r.comment}</div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="hk-row">
          <div className="hk-group">
            <span className="hk"><span className="kbd">j</span><span className="kbd">k</span> навигация</span>
            <span className="hk"><span className="kbd">Enter</span> открыть</span>
            <span className="hk"><span className="kbd">r</span> взять в работу</span>
            <span className="hk"><span className="kbd">d</span> выполнить</span>
            <span className="hk"><span className="kbd">Esc</span> снять выбор</span>
          </div>
          <div className="hk-group">
            <span className="hk"><span className="mono">updated 5с назад</span></span>
            <span className="hk"><Ic.Activity size={11}/> SSE подключён</span>
          </div>
        </div>
      </div>

      {modalApp && (
        <div className="modal-overlay" onClick={()=>setModalApp(null)}>
          <div className="modal" onClick={(e)=>e.stopPropagation()}>
            <div className="modal-head">
              <div style={{display:'flex', alignItems:'center', gap:8}}>
                <span className="idchip" style={{'--chip-bg':'var(--accent-faint)','--chip-fg':'var(--accent)'}}>{modalApp}</span>
                <span style={{fontSize:14, fontWeight:600}}>Детали заявки</span>
              </div>
              <button className="icon-btn" onClick={()=>setModalApp(null)}><Ic.X/></button>
            </div>
            <div className="modal-body">
              <div className="label" style={{marginBottom:6}}>Панель</div>
              <div className="mono" style={{marginBottom:12}}>P-COLOSSEUM-30 · cell 27</div>
              <div className="label" style={{marginBottom:6}}>Комментарий</div>
              <div style={{fontSize:13, color:'var(--fg-dim)', lineHeight:1.5, marginBottom:12}}>
                {fullComments[modalApp] || '—'}
              </div>
              <div className="label" style={{marginBottom:6}}>Статус</div>
              <span className="pill pill-warn"><span className="dot"/>в работе</span>
            </div>
            <div className="modal-foot">
              <button className="btn btn-ghost" onClick={()=>setModalApp(null)}>Закрыть</button>
              <button className="btn btn-secondary"><Ic.Eye size={12}/> Открыть в экране</button>
              <button className="btn btn-primary">Перейти к истории</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

window.DisplayView = DisplayView;
