import { HTMLAttributes, forwardRef, useEffect } from 'react'
import { cn } from '@/lib/utils.ts'
import { X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  open: boolean
  onClose: () => void
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  closeOnOverlayClick?: boolean
  title?: string
}

const Modal = forwardRef<HTMLDivElement, ModalProps>(
  ({ className, open, onClose, size = 'md', closeOnOverlayClick = true, title, children }, _ref) => {
    const sizes = {
      sm: 'max-w-md',
      md: 'max-w-2xl',
      lg: 'max-w-4xl',
      xl: 'max-w-6xl',
      full: 'max-w-full mx-4',
    }

    useEffect(() => {
      if (open) {
        document.body.style.overflow = 'hidden'
      } else {
        document.body.style.overflow = 'unset'
      }
      return () => {
        document.body.style.overflow = 'unset'
      }
    }, [open])

    const handleOverlayClick = () => {
      if (closeOnOverlayClick) {
        onClose()
      }
    }

    return (
      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm"
              onClick={handleOverlayClick}
            />

            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ type: 'spring', duration: 0.3 }}
              className={cn(
                'relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-h-[90vh] flex flex-col z-10 overflow-hidden',
                sizes[size],
                className
              )}
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
              {children}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    )
  }
)

Modal.displayName = 'Modal'

export interface ModalHeaderProps extends HTMLAttributes<HTMLDivElement> {
  onClose?: () => void
}

const ModalHeader = forwardRef<HTMLDivElement, ModalHeaderProps>(
  ({ className, onClose, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 flex-shrink-0', className)}
      {...props}
    >
      <div className="flex-1">{children}</div>
      {onClose && (
        <button
          onClick={onClose}
          className="ml-4 p-2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  )
)

ModalHeader.displayName = 'ModalHeader'

export interface ModalTitleProps extends HTMLAttributes<HTMLHeadingElement> {}

const ModalTitle = forwardRef<HTMLHeadingElement, ModalTitleProps>(
  ({ className, ...props }, ref) => (
    <h2
      ref={ref}
      className={cn('text-xl font-semibold text-gray-900 dark:text-gray-100', className)}
      {...props}
    />
  )
)

ModalTitle.displayName = 'ModalTitle'

export interface ModalContentProps extends HTMLAttributes<HTMLDivElement> {}

const ModalContent = forwardRef<HTMLDivElement, ModalContentProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('p-6 overflow-y-auto flex-1', className)}
      {...props}
    />
  )
)

ModalContent.displayName = 'ModalContent'

export interface ModalFooterProps extends HTMLAttributes<HTMLDivElement> {}

const ModalFooter = forwardRef<HTMLDivElement, ModalFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700 flex-shrink-0', className)}
      {...props}
    />
  )
)

ModalFooter.displayName = 'ModalFooter'

export { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter }
