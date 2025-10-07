import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils.ts'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'bordered'
  hover?: boolean
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', hover = false, children, ...props }, ref) => {
    const variants = {
      default: 'bg-white dark:bg-gray-800 rounded-xl shadow-ward-lg border border-gray-100 dark:border-gray-700',
      glass: 'bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-xl shadow-ward-lg border border-gray-100/50 dark:border-gray-700/50',
      bordered: 'bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700',
    }

    const hoverEffect = hover ? 'transition-all duration-200 hover:shadow-ward-xl hover:scale-[1.02]' : ''

    return (
      <div
        ref={ref}
        className={cn(variants[variant], hoverEffect, className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('p-6 pb-4', className)}
      {...props}
    />
  )
)

CardHeader.displayName = 'CardHeader'

export interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {}

const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('text-lg font-semibold text-gray-900 dark:text-gray-100', className)}
      {...props}
    />
  )
)

CardTitle.displayName = 'CardTitle'

export interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {}

const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-gray-500 mt-1', className)}
      {...props}
    />
  )
)

CardDescription.displayName = 'CardDescription'

export interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('p-6 pt-0', className)}
      {...props}
    />
  )
)

CardContent.displayName = 'CardContent'

export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {}

const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('p-6 pt-0 flex items-center gap-2', className)}
      {...props}
    />
  )
)

CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }
