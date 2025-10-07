import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils.ts'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'default'
  size?: 'sm' | 'md' | 'lg'
  dot?: boolean
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', dot = false, children, ...props }, ref) => {
    const variants = {
      success: 'bg-green-100 text-green-700 border-green-200',
      warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      danger: 'bg-red-100 text-red-700 border-red-200',
      info: 'bg-blue-100 text-blue-700 border-blue-200',
      default: 'bg-gray-100 text-gray-700 border-gray-200',
    }

    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-sm',
      lg: 'px-3 py-1.5 text-base',
    }

    const dotVariants = {
      success: 'bg-green-500',
      warning: 'bg-yellow-500',
      danger: 'bg-red-500',
      info: 'bg-blue-500',
      default: 'bg-gray-500',
    }

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1.5 font-medium rounded-full border transition-colors',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {dot && (
          <span className={cn('w-2 h-2 rounded-full', dotVariants[variant])} />
        )}
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'

export { Badge }
export default Badge
