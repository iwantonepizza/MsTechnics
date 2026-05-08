import { createContext, useContext } from 'react'

interface CrumbContextValue {
  crumb: React.ReactNode
  setCrumb: (node: React.ReactNode) => void
}
export const CrumbContext = createContext<CrumbContextValue>({
  crumb: null,
  setCrumb: () => {},
})
export const useCrumb = () => useContext(CrumbContext)
