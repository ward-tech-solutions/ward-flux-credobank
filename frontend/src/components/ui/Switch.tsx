import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

export interface SwitchProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  checked?: boolean
  label?: string
  helperText?: string
}

const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked = false, label, helperText, className, disabled, ...props }, ref) => {
    return (
      <div className={cn('flex flex-col gap-1', disabled && 'opacity-60')}>
        {label && (
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
        )}
        <button
          ref={ref}
          type="button"
          role="switch"
          aria-checked={checked}
          disabled={disabled}
          className={cn(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            checked ? 'bg-ward-green' : 'bg-gray-300 dark:bg-gray-600',
            disabled ? 'cursor-not-allowed' : 'cursor-pointer',
            className
          )}
          {...props}
        >
          <span
            className={cn(
              'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform',
              checked ? 'translate-x-5' : 'translate-x-1'
            )}
          />
        </button>
        {helperText && (
          <span className="text-xs text-gray-500 dark:text-gray-400">{helperText}</span>
        )}
      </div>
    )
  }
)

Switch.displayName = 'Switch'

export default Switch
