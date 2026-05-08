// Main Menu v2 — без hero, KPI строкой сверху, 4 колонки департаментов.
// Операционный дашборд для смены: что случилось, что требует моего действия.

const MainMenu = () => {
  const { Ic, Header } = window;

  return (
    <div className="mm-view">
      <style>{`
        .mm-view {
          width: 1920px; height: 1080px;
          background: var(--bg-0);
          display: flex; flex-direction: column;
          overflow: hidden; font-size: 13px;
        }

        /* KPI strip — под хедером, одной строкой, без hero */
        .kpi-strip {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          border-bottom: 1px solid var(--border-subtle);
          background: var(--bg-0);
        }
        .kpi {
          display: grid;
          grid-template-columns: 1fr auto;
          align-items: center;
          padding: 14px 20px;
          border-right: 1px solid var(--border-subtle);
          cursor: pointer;
          transition: background 80ms linear;
        }
        .kpi:last-child { border-right: none; }
        .kpi:hover { background: var(--bg-1); }
        .kpi-l { display: flex; flex-direction: column; gap: 3px; }
        .kpi-label { font: 500 10.5px/1 var(--font-mono); text-transform: uppercase; letter-spacing: 0.08em; color: var(--fg-mute); }
        .kpi-val { display: flex; align-items: baseline; gap: 6px; }
        .kpi-num { font-family: var(--font-mono); font-size: 28px; font-weight: 600; letter-spacing: -0.02em; color: var(--fg); line-height: 1; }
        .kpi-delta { font-size: 11.5px; color: var(--fg-mute); font-family: var(--font-mono); }
        .kpi-delta.up { color: var(--err); }
        .kpi-delta.dn { color: var(--ok); }
        .kpi-hint { font-size: 11px; color: var(--fg-mute); margin-top: 2px; }
        .kpi-spark { display: flex; align-items: end; gap: 2px; height: 28px; }
        .kpi-spark span { width: 3px; background: var(--bg-4); border-radius: 1px; }
        .kpi-spark.err span:last-child { background: var(--err); }
        .kpi-spark.warn span:last-child { background: var(--warn); }
        .kpi-spark.info span:last-child { background: var(--info); }
        .kpi-spark.brand span:last-child { background: var(--brand); }

        /* 4 колонки департаментов */
        .mm-body {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          flex: 1; min-height: 0;
        }
        .dept {
          border-right: 1px solid var(--border-subtle);
          display: flex; flex-direction: column;
          min-height: 0;
        }
        .dept:last-child { border-right: none; }
        .dept-head {
          display: flex; justify-content: space-between; align-items: center;
          padding: 14px 16px 10px;
        }
        .dept-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; letter-spacing: -0.01em; }
        .dept-title svg { color: var(--fg-dim); }
        .dept-sub { font-size: 11px; color: var(--fg-mute); font-family: var(--font-mono); }
        .dept-body { flex: 1; overflow-y: auto; padding: 0 10px 12px; }
        .dept-foot {
          padding: 8px 12px; border-top: 1px solid var(--border-subtle);
          display: flex; justify-content: space-between; align-items: center;
          background: var(--bg-1);
        }

        /* Section внутри колонки */
        .sec { margin: 6px 0 14px; }
        .sec-h {
          display: flex; justify-content: space-between; align-items: center;
          padding: 0 6px 6px;
        }
        .sec-h .label { display: inline-flex; align-items: center; gap: 6px; }
        .sec-count { font-family: var(--font-mono); font-size: 10px; color: var(--fg-faint); }

        /* City row with histogram (a) — срез сейчас */
        .city-row {
          display: grid; grid-template-columns: 1fr auto; gap: 8px;
          align-items: center; padding: 8px; border-radius: var(--r-md);
          cursor: pointer; transition: background 80ms linear;
        }
        .city-row:hover { background: var(--bg-2); }
        .city-name { font-size: 12.5px; color: var(--fg); display: flex; align-items: center; gap: 6px; }
        .city-sub { font-size: 10.5px; color: var(--fg-mute); font-family: var(--font-mono); margin-left: 6px; }
        .city-hist { display: flex; gap: 2px; height: 22px; align-items: end; }
        .city-hist span { width: 3px; border-radius: 1px; }

        /* Queue card — заявки в контроле */
        .queue-card {
          display: grid; grid-template-columns: auto 1fr auto; gap: 10px;
          align-items: center; padding: 9px 10px;
          border: 1px solid var(--border-subtle);
          background: var(--bg-1);
          border-radius: var(--r-md);
          margin-bottom: 6px; cursor: pointer;
          transition: border-color 80ms linear, background 80ms linear;
        }
        .queue-card:hover { border-color: var(--border-strong); background: var(--bg-2); }
        .queue-body { min-width: 0; }
        .queue-title { font-size: 12.5px; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .queue-meta { font-size: 11px; color: var(--fg-mute); display: flex; gap: 6px; margin-top: 2px; }
        .queue-meta .mono { font-family: var(--font-mono); color: var(--fg-dim); }
        .queue-actions { display: flex; gap: 2px; }

        /* Service — мои заявки */
        .mine-row {
          display: grid; grid-template-columns: auto 1fr auto; gap: 10px;
          align-items: center; padding: 9px 10px;
          border-radius: var(--r-md); cursor: pointer;
          border-left: 2px solid transparent;
          transition: background 80ms linear, border-color 80ms linear;
        }
        .mine-row:hover { background: var(--bg-2); }
        .mine-row.hot { border-left-color: var(--err); background: color-mix(in oklch, var(--err-faint) 40%, transparent); }
        .mine-row.hot:hover { background: var(--err-faint); }
        .mine-title { font-size: 12.5px; }
        .mine-meta { font-size: 11px; color: var(--fg-mute); font-family: var(--font-mono); margin-top: 2px; }

        /* ZIP stocks + departures */
        .stocks-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 0 6px; }
        .stock {
          padding: 10px 12px; border-radius: var(--r-md);
          background: var(--bg-1); border: 1px solid var(--border-subtle);
        }
        .stock-lbl { font: 500 10px/1 var(--font-mono); text-transform: uppercase; letter-spacing: 0.08em; color: var(--fg-mute); }
        .stock-num { font-family: var(--font-mono); font-size: 22px; font-weight: 600; color: var(--fg); margin-top: 6px; line-height: 1; }
        .stock-num small { font-size: 12px; color: var(--fg-mute); font-weight: 400; margin-left: 3px; }
        .stock-hint { font-size: 10.5px; color: var(--fg-mute); margin-top: 4px; }
        .stock.warn .stock-num { color: var(--warn); }

        .dep-row {
          display: grid; grid-template-columns: auto 1fr auto; gap: 10px;
          align-items: center; padding: 8px 10px;
          border-radius: var(--r-md); cursor: pointer;
        }
        .dep-row:hover { background: var(--bg-2); }
        .dep-time { font-family: var(--font-mono); font-size: 11px; color: var(--fg-dim); min-width: 42px; }
        .dep-title { font-size: 12.5px; color: var(--fg); }
        .dep-meta { font-size: 11px; color: var(--fg-mute); margin-top: 2px; }
        .dep-status { font-size: 10.5px; font-family: var(--font-mono); color: var(--fg-mute); }

        /* Hotkeys bar */
        .hk-bar {
          display: flex; justify-content: space-between; align-items: center;
          padding: 6px 16px; border-top: 1px solid var(--border-subtle);
          background: var(--bg-1); font-size: 11px; color: var(--fg-mute);
        }
        .hk { display: inline-flex; align-items: center; gap: 4px; }
      `}</style>

      <Header active="home" crumb={
        <>
          <span className="cur">Главная</span>
          <span className="mono" style={{color:'var(--fg-faint)', marginLeft:2}}>/menu</span>
          <span style={{marginLeft:10, fontSize:11}}>смена началась <span className="mono" style={{color:'var(--fg-dim)'}}>08:00 МСК</span> · <span className="mono" style={{color:'var(--fg-dim)'}}>6 ч 22 мин</span></span>
        </>
      }/>

      {/* KPI strip */}
      <div className="kpi-strip">
        <div className="kpi" title="Заявки со статусом sent_to_control — ждут контролёра">
          <div className="kpi-l">
            <div className="kpi-label">Новых заявок</div>
            <div className="kpi-val">
              <span className="kpi-num">7</span>
              <span className="kpi-delta up">+3 за час</span>
            </div>
            <div className="kpi-hint">→ контроль: принять в работу</div>
          </div>
          <div className="kpi-spark warn">
            {[4,6,3,5,4,7,5,6,8,5,7,9,7].map((h,i)=><span key={i} style={{height: `${h*3}px`}}/>)}
          </div>
        </div>

        <div className="kpi" title="Мои активные заявки в сервисе">
          <div className="kpi-l">
            <div className="kpi-label">В работе у меня</div>
            <div className="kpi-val">
              <span className="kpi-num">5</span>
              <span className="kpi-delta dn">−1 сегодня</span>
            </div>
            <div className="kpi-hint">2 в ремонте · 3 ждут запчасти</div>
          </div>
          <div className="kpi-spark info">
            {[6,6,5,5,6,7,7,6,6,5,6,6,5].map((h,i)=><span key={i} style={{height: `${h*3}px`}}/>)}
          </div>
        </div>

        <div className="kpi" title="Выездов сегодня по расписанию">
          <div className="kpi-l">
            <div className="kpi-label">Выездов сегодня</div>
            <div className="kpi-val">
              <span className="kpi-num">4</span>
              <span className="kpi-delta">2 завершено · 1 сейчас · 1 запланирован</span>
            </div>
            <div className="kpi-hint">след. в <span className="mono" style={{color:'var(--fg-dim)'}}>16:30</span> · Ижевск, Колизей</div>
          </div>
          <div className="kpi-spark brand">
            {[2,3,2,4,3,3,4,5,3,4,4,3,4].map((h,i)=><span key={i} style={{height: `${h*4}px`}}/>)}
          </div>
        </div>

        <div className="kpi" title="Заявки без изменений > 24 ч в активных статусах">
          <div className="kpi-l">
            <div className="kpi-label">Просрочено SLA</div>
            <div className="kpi-val">
              <span className="kpi-num" style={{color:'var(--err)'}}>3</span>
              <span className="kpi-delta up">+1 с вчера</span>
            </div>
            <div className="kpi-hint">→ разобрать: 2 в контроле · 1 в сервисе</div>
          </div>
          <div className="kpi-spark err">
            {[1,1,2,1,2,2,1,2,3,2,2,3,3].map((h,i)=><span key={i} style={{height: `${h*6}px`}}/>)}
          </div>
        </div>
      </div>

      {/* 4 колонки */}
      <div className="mm-body">
        {/* Мониторинг */}
        <div className="dept">
          <div className="dept-head">
            <div className="dept-title"><Ic.Monitor/> Мониторинг</div>
            <div className="dept-sub">6 городов · 38 экранов</div>
          </div>
          <div className="dept-body scroll">
            <div className="sec">
              <div className="sec-h">
                <span className="label">Здоровье парка · срез сейчас</span>
                <span className="sec-count">38 экранов</span>
              </div>
              {[
                {city:'Ижевск', screens:12, hist:[2,2,1,2,1,2,2,1,3,2,1,2], bad: 4},
                {city:'Казань', screens:9,  hist:[2,2,2,1,2,2,2,2,1], bad: 1},
                {city:'Уфа', screens:6,   hist:[1,1,2,3,1,2], bad: 2},
                {city:'Пермь', screens:5, hist:[2,1,1,2,1], bad: 0},
                {city:'Самара', screens:4, hist:[2,2,1,2], bad: 1},
                {city:'Набережные Челны', screens:2, hist:[2,1], bad: 0},
              ].map(c=>(
                <div key={c.city} className="city-row">
                  <div>
                    <div className="city-name">
                      <Ic.Map size={12}/>{c.city}
                      <span className="city-sub">{c.screens} экр.</span>
                      {c.bad>0 && <span className="pill pill-err" style={{marginLeft:6}}><span className="dot"/>{c.bad}</span>}
                    </div>
                  </div>
                  <div className="city-hist">
                    {c.hist.map((lvl,i)=>{
                      const color = lvl===1 ? 'var(--ok)' : lvl===2 ? 'var(--warn)' : 'var(--err)';
                      const h = lvl===1 ? 8 : lvl===2 ? 14 : 20;
                      return <span key={i} style={{background: color, height: h}} title={lvl===1?'работает':lvl===2?'проблема':'сломан'}/>;
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div className="sec">
              <div className="sec-h"><span className="label">Последние события</span></div>
              <div style={{fontSize:12, color:'var(--fg-dim)', padding:'0 6px'}}>
                <div style={{display:'flex', gap:8, padding:'6px 4px'}}>
                  <span className="mono" style={{color:'var(--fg-mute)', minWidth:40}}>14:22</span>
                  <span>Ижевск · Колизей · <span className="mono" style={{color:'var(--err)'}}>cell 27</span> отмечена сломанной</span>
                </div>
                <div style={{display:'flex', gap:8, padding:'6px 4px'}}>
                  <span className="mono" style={{color:'var(--fg-mute)', minWidth:40}}>13:40</span>
                  <span>Ижевск · Колизей · <span className="mono" style={{color:'var(--warn)'}}>cell 34</span> моргает</span>
                </div>
                <div style={{display:'flex', gap:8, padding:'6px 4px'}}>
                  <span className="mono" style={{color:'var(--fg-mute)', minWidth:40}}>13:12</span>
                  <span>Казань · ТЦ Мега · <span className="mono" style={{color:'var(--warn)'}}>cell 05</span> моргает</span>
                </div>
                <div style={{display:'flex', gap:8, padding:'6px 4px'}}>
                  <span className="mono" style={{color:'var(--fg-mute)', minWidth:40}}>12:08</span>
                  <span>Уфа · Аэропорт · <span className="mono" style={{color:'var(--err)'}}>cell 52</span> сломалась</span>
                </div>
              </div>
            </div>
          </div>
          <div className="dept-foot">
            <span style={{fontSize:11.5, color:'var(--fg-mute)'}}>5 новых с начала смены</span>
            <button className="btn btn-secondary sm">Открыть <Ic.ArrowR size={11}/></button>
          </div>
        </div>

        {/* Контроль */}
        <div className="dept">
          <div className="dept-head">
            <div className="dept-title"><Ic.Clipboard/> Контроль</div>
            <div className="dept-sub">очередь · 7</div>
          </div>
          <div className="dept-body scroll">
            <div className="sec">
              <div className="sec-h">
                <span className="label">Ждут приёма</span>
                <span className="sec-count">sent_to_control</span>
              </div>
              {[
                {id:'ID-4570', panel:'COLOSSEUM-30', cell:'27', city:'Ижевск', ago:'5 мин', bg:'var(--err-faint)', fg:'var(--err)'},
                {id:'ID-4569', panel:'MEGA-07', cell:'05', city:'Казань', ago:'18 мин', bg:'var(--warn)', fg:'var(--warn-ink)'},
                {id:'ID-4568', panel:'AIRPORT-54', cell:'52', city:'Уфа', ago:'42 мин', bg:'var(--err-faint)', fg:'var(--err)'},
                {id:'ID-4567', panel:'COLOSSEUM-37', cell:'34', city:'Ижевск', ago:'1 ч 12 мин', bg:'var(--warn)', fg:'var(--warn-ink)'},
              ].map(q=>(
                <div key={q.id} className="queue-card">
                  <span className="idchip" style={{'--chip-bg': q.bg, '--chip-fg': q.fg}}>{q.id}</span>
                  <div className="queue-body">
                    <div className="queue-title">{q.panel}</div>
                    <div className="queue-meta">
                      <span className="mono">cell {q.cell}</span>·<span>{q.city}</span>·<span>{q.ago}</span>
                    </div>
                  </div>
                  <div className="queue-actions">
                    <button className="btn btn-primary sm"><Ic.Check size={11}/></button>
                    <button className="icon-btn" title="Ещё"><Ic.MoreH/></button>
                  </div>
                </div>
              ))}
            </div>

            <div className="sec">
              <div className="sec-h">
                <span className="label">В работе у контроля</span>
                <span className="sec-count">apply_in_control · 3</span>
              </div>
              {[
                {id:'ID-4565', panel:'COLOSSEUM-17', assignee:'Миша К.'},
                {id:'ID-4564', panel:'COLOSSEUM-74', assignee:'—'},
                {id:'ID-4563', panel:'MEGA-09', assignee:'Миша К.'},
              ].map(r=>(
                <div key={r.id} style={{display:'grid', gridTemplateColumns:'auto 1fr auto', gap:10, alignItems:'center', padding:'7px 10px', borderRadius:'var(--r-md)', cursor:'pointer'}}>
                  <span className="idchip" style={{'--chip-bg':'var(--info-faint)','--chip-fg':'var(--info)'}}>{r.id}</span>
                  <span style={{fontSize:12.5, color:'var(--fg-dim)'}}>{r.panel}</span>
                  <span style={{fontSize:11, color:'var(--fg-mute)'}}>{r.assignee}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="dept-foot">
            <span style={{fontSize:11.5, color:'var(--fg-mute)'}}>Миша К. · ты сейчас 1 из 2 контролёров онлайн</span>
            <button className="btn btn-secondary sm">Открыть <Ic.ArrowR size={11}/></button>
          </div>
        </div>

        {/* Сервис */}
        <div className="dept">
          <div className="dept-head">
            <div className="dept-title"><Ic.Wrench/> Сервис</div>
            <div className="dept-sub">5 активных</div>
          </div>
          <div className="dept-body scroll">
            <div className="sec">
              <div className="sec-h">
                <span className="label">Мои заявки</span>
                <span className="sec-count">work_in_service</span>
              </div>
              {[
                {id:'ID-4567', panel:'COLOSSEUM-30', cell:'27', note:'моргает верхний ряд · проверить шлейф', upd:'5 мин', hot:true, bg:'var(--warn)', fg:'var(--warn-ink)'},
                {id:'ID-4561', panel:'COLOSSEUM-70', cell:'67', note:'моргает при нагреве', upd:'2 дня', hot:true, bg:'var(--warn)', fg:'var(--warn-ink)'},
                {id:'ID-4566', panel:'COLOSSEUM-37', cell:'34', note:'битый чип, полная замена', upd:'22 мин', bg:'var(--info-faint)', fg:'var(--info)'},
                {id:'ID-4563', panel:'COLOSSEUM-47', cell:'44', note:'полная замена модуля', upd:'вчера', bg:'var(--info-faint)', fg:'var(--info)'},
                {id:'ID-4559', panel:'MEGA-12', cell:'41', note:'драйвер плывёт по цвету', upd:'3 дня', bg:'var(--info-faint)', fg:'var(--info)'},
              ].map(r=>(
                <div key={r.id} className={`mine-row ${r.hot?'hot':''}`}>
                  <span className="idchip" style={{'--chip-bg':r.bg,'--chip-fg':r.fg}}>{r.id}</span>
                  <div>
                    <div className="mine-title">{r.panel} · <span style={{color:'var(--fg-mute)'}}>{r.note}</span></div>
                    <div className="mine-meta">cell {r.cell} · обновлено {r.upd} назад</div>
                  </div>
                  <button className="icon-btn" title="Открыть"><Ic.ArrowR size={12}/></button>
                </div>
              ))}
            </div>

            <div className="sec">
              <div className="sec-h">
                <span className="label">В очереди на меня</span>
                <span className="sec-count">sent_to_service · 2</span>
              </div>
              {[
                {id:'ID-4562', panel:'MEGA-03', note:'не горит', by:'Миша К.', ago:'10 мин'},
                {id:'ID-4560', panel:'AIRPORT-18', note:'требуется диагностика', by:'Миша К.', ago:'4 ч'},
              ].map(r=>(
                <div key={r.id} className="queue-card">
                  <span className="idchip" style={{'--chip-bg':'var(--accent-faint)','--chip-fg':'var(--accent)'}}>{r.id}</span>
                  <div className="queue-body">
                    <div className="queue-title">{r.panel} · <span style={{color:'var(--fg-mute)'}}>{r.note}</span></div>
                    <div className="queue-meta"><span>от {r.by}</span>·<span>{r.ago}</span></div>
                  </div>
                  <button className="btn btn-primary sm"><Ic.Wrench size={11}/></button>
                </div>
              ))}
            </div>
          </div>
          <div className="dept-foot">
            <span style={{fontSize:11.5, color:'var(--fg-mute)'}}>ты на смене до <span className="mono" style={{color:'var(--fg-dim)'}}>20:00</span></span>
            <button className="btn btn-secondary sm">Открыть <Ic.ArrowR size={11}/></button>
          </div>
        </div>

        {/* ЗИП + Выезды */}
        <div className="dept">
          <div className="dept-head">
            <div className="dept-title"><Ic.Box/> ЗИП и выезды</div>
            <div className="dept-sub">склад · маршруты</div>
          </div>
          <div className="dept-body scroll">
            <div className="sec">
              <div className="sec-h">
                <span className="label">Панели на складе</span>
                <span className="sec-count">по отделам</span>
              </div>
              <div className="stocks-grid">
                <div className="stock">
                  <div className="stock-lbl">В ЗИП</div>
                  <div className="stock-num">142<small>шт</small></div>
                  <div className="stock-hint">рабочих · доступно</div>
                </div>
                <div className="stock warn">
                  <div className="stock-lbl">В сервисе</div>
                  <div className="stock-num">38<small>шт</small></div>
                  <div className="stock-hint">на ремонте</div>
                </div>
                <div className="stock">
                  <div className="stock-lbl">На руках</div>
                  <div className="stock-num">12<small>шт</small></div>
                  <div className="stock-hint">у техников</div>
                </div>
                <div className="stock">
                  <div className="stock-lbl">В утиль</div>
                  <div className="stock-num" style={{color:'var(--fg-mute)'}}>7<small>шт</small></div>
                  <div className="stock-hint">unrecoverable</div>
                </div>
              </div>
            </div>

            <div className="sec">
              <div className="sec-h">
                <span className="label">Расходники</span>
                <span className="sec-count">хабы · ламели · провода</span>
              </div>
              <div style={{padding:'0 6px', fontSize:12.5}}>
                <div style={{display:'grid', gridTemplateColumns:'1fr auto auto', gap:10, padding:'6px 4px', color:'var(--fg-dim)'}}>
                  <span>Хабы</span><span className="mono" style={{color:'var(--fg)'}}>24</span><span style={{color:'var(--fg-mute)',fontSize:11}}>ок</span>
                </div>
                <div style={{display:'grid', gridTemplateColumns:'1fr auto auto', gap:10, padding:'6px 4px', color:'var(--fg-dim)'}}>
                  <span>Ламели</span><span className="mono" style={{color:'var(--fg)'}}>86</span><span style={{color:'var(--fg-mute)',fontSize:11}}>ок</span>
                </div>
                <div style={{display:'grid', gridTemplateColumns:'1fr auto auto', gap:10, padding:'6px 4px', color:'var(--warn)'}}>
                  <span>Провода силовые</span><span className="mono">4</span><span style={{fontSize:11}}>мало</span>
                </div>
                <div style={{display:'grid', gridTemplateColumns:'1fr auto auto', gap:10, padding:'6px 4px', color:'var(--fg-dim)'}}>
                  <span>Провода сигнальные</span><span className="mono" style={{color:'var(--fg)'}}>31</span><span style={{color:'var(--fg-mute)',fontSize:11}}>ок</span>
                </div>
              </div>
            </div>

            <div className="sec">
              <div className="sec-h">
                <span className="label">Выезды сегодня</span>
                <span className="sec-count">4 всего</span>
              </div>
              {[
                {t:'10:00', who:'Артём П.', where:'Ижевск · Колизей', st:'done', stLbl:'завершено'},
                {t:'13:00', who:'Игорь В.', where:'Казань · ТЦ Мега', st:'done', stLbl:'завершено'},
                {t:'15:00', who:'Артём П.', where:'Ижевск · Вокзал', st:'go', stLbl:'в пути'},
                {t:'16:30', who:'Игорь В.', where:'Ижевск · Колизей', st:'plan', stLbl:'план'},
              ].map((d,i)=>(
                <div key={i} className="dep-row">
                  <span className="dep-time">{d.t}</span>
                  <div>
                    <div className="dep-title">{d.where}</div>
                    <div className="dep-meta">{d.who}</div>
                  </div>
                  <span className={`pill ${d.st==='done'?'pill-ok':d.st==='go'?'pill-info':'pill-neutral'}`}>
                    <span className="dot"/>{d.stLbl}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="dept-foot">
            <span style={{fontSize:11.5, color:'var(--fg-mute)'}}><span style={{color:'var(--warn)'}}>1 расходник</span> к пополнению</span>
            <button className="btn btn-secondary sm">В ЗИП <Ic.ArrowR size={11}/></button>
          </div>
        </div>
      </div>

      <div className="hk-bar">
        <div style={{display:'flex', gap:16}}>
          <span className="hk"><span className="kbd">g</span><span className="kbd">m</span> меню</span>
          <span className="hk"><span className="kbd">g</span><span className="kbd">c</span> контроль</span>
          <span className="hk"><span className="kbd">g</span><span className="kbd">s</span> сервис</span>
          <span className="hk"><span className="kbd">g</span><span className="kbd">z</span> ЗИП</span>
          <span className="hk"><span className="kbd">/</span> поиск</span>
          <span className="hk"><span className="kbd">?</span> все шорткаты</span>
        </div>
        <div style={{display:'flex', gap:14}}>
          <span className="hk"><span className="mono">updated 3с назад</span></span>
          <span className="hk"><Ic.Activity size={11}/> SSE подключён</span>
        </div>
      </div>
    </div>
  );
};

window.MainMenu = MainMenu;
