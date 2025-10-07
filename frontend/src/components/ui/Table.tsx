import { HTMLAttributes, ThHTMLAttributes, TdHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils.ts'

export interface TableProps extends HTMLAttributes<HTMLTableElement> {}

const Table = forwardRef<HTMLTableElement, TableProps>(
  ({ className, ...props }, ref) => (
    <div className="w-full overflow-auto rounded-lg border border-gray-200 dark:border-gray-700">
      <table
        ref={ref}
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  )
)

Table.displayName = 'Table'

export interface TableHeaderProps extends HTMLAttributes<HTMLTableSectionElement> {}

const TableHeader = forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  ({ className, ...props }, ref) => (
    <thead
      ref={ref}
      className={cn('bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700', className)}
      {...props}
    />
  )
)

TableHeader.displayName = 'TableHeader'

export interface TableBodyProps extends HTMLAttributes<HTMLTableSectionElement> {}

const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className, ...props }, ref) => (
    <tbody
      ref={ref}
      className={cn('divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900', className)}
      {...props}
    />
  )
)

TableBody.displayName = 'TableBody'

export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  hover?: boolean
}

const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, hover = true, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        'transition-colors',
        hover && 'hover:bg-gray-50 dark:hover:bg-gray-800',
        className
      )}
      {...props}
    />
  )
)

TableRow.displayName = 'TableRow'

export interface TableHeadProps extends ThHTMLAttributes<HTMLTableCellElement> {}

const TableHead = forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn(
        'px-6 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider',
        className
      )}
      {...props}
    />
  )
)

TableHead.displayName = 'TableHead'

export interface TableCellProps extends TdHTMLAttributes<HTMLTableCellElement> {}

const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, ...props }, ref) => (
    <td
      ref={ref}
      className={cn('px-6 py-4 text-gray-900 dark:text-gray-100', className)}
      {...props}
    />
  )
)

TableCell.displayName = 'TableCell'

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell }
