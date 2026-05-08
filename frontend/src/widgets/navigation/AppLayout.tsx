import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { CrumbContext } from './CrumbContext'
import { useState } from 'react'

export function AppLayout() {
  const [crumb, setCrumb] = useState<React.ReactNode>(null)
  return (
    <CrumbContext.Provider value={{ crumb, setCrumb }}>
      <div
        className="flex flex-col h-screen overflow-hidden"
        style={{ background: 'var(--bg-0)', color: 'var(--fg)' }}
      >
        <Header crumb={crumb} />
        <main className="flex-1 min-h-0 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </CrumbContext.Provider>
  )
}
