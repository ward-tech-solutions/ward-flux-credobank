import { useState, useRef, useEffect } from 'react'
import { Check, X, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface MultiSelectOption {
  value: string
  label: string
}

type RawOption = string | MultiSelectOption

interface MultiSelectProps {
  options: RawOption[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  label?: string
  helperText?: string
  disabled?: boolean
  maxSelected?: number
}

const normalizeOptions = (options: RawOption[]): MultiSelectOption[] =>
  options.map(option =>
    typeof option === 'string' ? { value: option, label: option } : option
  )

export default function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = 'Select...',
  label,
  helperText,
  disabled = false,
  maxSelected = Infinity,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const normalizedOptions = normalizeOptions(options)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggleOption = (option: string) => {
    if (disabled) return

    if (selected.includes(option)) {
      onChange(selected.filter(item => item !== option))
    } else {
      if (maxSelected === 1) {
        onChange([option])
        setIsOpen(false)
      } else {
        if (selected.length >= maxSelected) return
        onChange([...selected, option])
      }
    }
  }

  const removeOption = (option: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (disabled) return
    onChange(selected.filter(item => item !== option))
  }

  const clearAll = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (disabled) return
    onChange([])
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}

      <div
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={cn(
          'min-h-[42px] px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors flex items-center justify-between gap-2',
          disabled
            ? 'opacity-60 cursor-not-allowed'
            : 'cursor-pointer hover:border-ward-green dark:hover:border-ward-green'
        )}
      >
        <div className="flex flex-wrap gap-1.5 flex-1">
          {selected.length === 0 ? (
            <span className="text-gray-500 dark:text-gray-400 text-sm">{placeholder}</span>
          ) : (
            selected.map(option => {
              const optionLabel = normalizedOptions.find(o => o.value === option)?.label || option
              return (
                <span
                  key={option}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-ward-green/10 text-ward-green rounded-md text-sm font-medium"
                >
                  {optionLabel}
                  {!disabled && (
                    <button
                      onClick={(e) => removeOption(option, e)}
                      className="hover:bg-ward-green/20 rounded-full p-0.5 transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </span>
              )
            })
          )}
        </div>
        <div className="flex items-center gap-1">
          {selected.length > 0 && !disabled && (
            <button
              onClick={clearAll}
              className="hover:bg-gray-100 dark:hover:bg-gray-700 rounded p-1 transition-colors"
              title="Clear all"
            >
              <X className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </button>
          )}
          <ChevronDown
            className={cn(
              'h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform',
              isOpen ? 'rotate-180' : '',
              disabled && 'opacity-50'
            )}
          />
        </div>
      </div>

      {helperText && (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
      )}

      {isOpen && !disabled && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {normalizedOptions.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No options available</div>
          ) : (
            normalizedOptions.map(option => {
              const isSelected = selected.includes(option.value)
              return (
                <div
                  key={option.value}
                  onClick={() => toggleOption(option.value)}
                  className={`px-3 py-2 cursor-pointer transition-colors flex items-center justify-between ${
                    isSelected
                      ? 'bg-ward-green/10 text-ward-green'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100'
                  }`}
                >
                  <span className="text-sm font-medium">{option.label}</span>
                  {isSelected && <Check className="h-4 w-4" />}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
