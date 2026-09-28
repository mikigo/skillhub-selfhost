import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Skeleton } from './ui/skeleton'
import type { ReactNode } from 'react'

export default function ProtectedRoute({ children, admin }: { children: ReactNode; admin?: boolean }) {
  const { user, initializing } = useAuth()

  if (initializing) return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  if (admin && !user.is_admin) return <Navigate to="/" replace />

  return <>{children}</>
}