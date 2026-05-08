import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-24 text-center">
      <p className="text-[64px] leading-none mb-4">404</p>
      <p className="text-md font-medium text-fg mb-1">Страница не найдена</p>
      <p className="text-sm text-fg-mute mb-6">Проверьте URL или вернитесь на главную</p>
      <Link to="/menu" className="btn btn-secondary text-sm px-4 py-2 rounded-md">
        На главную
      </Link>
    </div>
  )
}
