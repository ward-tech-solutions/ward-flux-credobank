import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

export interface LoadingSpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

const LoadingSpinner = forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ className, size = 'md', text, ...props }, ref) => {
    const sizes = {
      sm: 'h-4 w-4',
      md: 'h-8 w-8',
      lg: 'h-12 w-12',
    }

    return (
      <div
        ref={ref}
        className={cn('flex flex-col items-center justify-center gap-3', className)}
        {...props}
      >
        <Loader2 className={cn('animate-spin text-ward-green', sizes[size])} />
        {text && <p className="text-sm text-gray-600">{text}</p>}
      </div>
    )
  }
)

LoadingSpinner.displayName = 'LoadingSpinner'

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'card' | 'circle' | 'rect'
  lines?: number
}

const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant = 'rect', lines = 1, ...props }, ref) => {
    if (variant === 'text' && lines > 1) {
      return (
        <div className="space-y-2">
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className={cn(
                'h-4 bg-gray-200 rounded animate-pulse',
                i === lines - 1 && 'w-3/4',
                className
              )}
            />
          ))}
        </div>
      )
    }

    const variants = {
      text: 'h-4 w-full rounded',
      card: 'h-32 w-full rounded-xl',
      circle: 'h-12 w-12 rounded-full',
      rect: 'h-20 w-full rounded-lg',
    }

    return (
      <div
        ref={ref}
        className={cn('bg-gray-200 animate-pulse', variants[variant], className)}
        {...props}
      />
    )
  }
)

Skeleton.displayName = 'Skeleton'

export interface LoadingOverlayProps extends HTMLAttributes<HTMLDivElement> {
  loading: boolean
  text?: string
}

const LoadingOverlay = forwardRef<HTMLDivElement, LoadingOverlayProps>(
  ({ className, loading, text = 'Loading...', children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('relative', className)} {...props}>
        {children}
        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
            <LoadingSpinner size="lg" text={text} />
          </div>
        )}
      </div>
    )
  }
)

LoadingOverlay.displayName = 'LoadingOverlay'

export { LoadingSpinner, Skeleton, LoadingOverlay }
