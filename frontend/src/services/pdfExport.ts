/**
 * WARD FLUX - PDF Export Service
 * Client-side PDF generation using jsPDF and html2canvas
 */
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { toast } from 'sonner'

export class PDFExportService {
  /**
   * Export HTML element to PDF with WARD branding
   * @param elementId - ID of the HTML element to export
   * @param filename - Name of the PDF file to download
   */
  static async exportToPDF(elementId: string, filename: string): Promise<void> {
    try {
      const element = document.getElementById(elementId)
      if (!element) {
        throw new Error(`Element with id '${elementId}' not found`)
      }

      // Show loading toast
      const loadingToast = toast.loading('📄 Generating PDF...')

      // Generate canvas from HTML element
      const canvas = await html2canvas(element, {
        scale: 2, // Higher quality
        useCORS: true, // Allow cross-origin images
        logging: false, // Disable console logs
        backgroundColor: '#ffffff',
        windowWidth: element.scrollWidth,
        windowHeight: element.scrollHeight,
      })

      // Convert canvas to image data
      const imgData = canvas.toDataURL('image/png')

      // Create PDF document
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: 'a4',
      })

      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const imgWidth = pageWidth - 20 // 10mm margins on each side
      const imgHeight = (canvas.height * imgWidth) / canvas.width

      // Add WARD header
      pdf.setFontSize(20)
      pdf.setTextColor(94, 187, 168) // WARD green
      pdf.text('WARD FLUX - Network Monitoring Report', 10, 15)

      pdf.setFontSize(10)
      pdf.setTextColor(100, 100, 100)
      const now = new Date().toLocaleString('en-GB', {
        timeZone: 'Asia/Tbilisi',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
      pdf.text(`Generated: ${now} (Tbilisi Time)`, 10, 22)
      pdf.text('CredoBank Network Operations', 10, 27)

      // Add content
      const contentY = 35
      const availableHeight = pageHeight - contentY - 10

      if (imgHeight <= availableHeight) {
        // Single page
        pdf.addImage(imgData, 'PNG', 10, contentY, imgWidth, imgHeight)
      } else {
        // Multi-page support
        let currentPage = 1
        let yOffset = 0

        while (yOffset < imgHeight) {
          if (currentPage > 1) {
            pdf.addPage()
          }

          const remainingHeight = imgHeight - yOffset
          const sliceHeight = Math.min(availableHeight, remainingHeight)

          // Add image slice
          pdf.addImage(
            imgData,
            'PNG',
            10,
            contentY - yOffset,
            imgWidth,
            imgHeight
          )

          yOffset += sliceHeight
          currentPage++

          // Prevent infinite loop
          if (currentPage > 100) {
            console.warn('PDF generation exceeded 100 pages, stopping')
            break
          }
        }
      }

      // Add footer to all pages
      const totalPages = pdf.getNumberOfPages()
      for (let i = 1; i <= totalPages; i++) {
        pdf.setPage(i)
        pdf.setFontSize(8)
        pdf.setTextColor(150, 150, 150)
        pdf.text(
          `Page ${i} of ${totalPages} | WARD FLUX © 2025 | CredoBank`,
          pageWidth / 2,
          pageHeight - 5,
          { align: 'center' }
        )
      }

      // Save PDF
      pdf.save(filename)

      // Success notification
      toast.dismiss(loadingToast)
      toast.success('✅ PDF exported successfully!', {
        description: `Downloaded: ${filename}`,
        duration: 3000,
      })
    } catch (error) {
      console.error('PDF export failed:', error)
      toast.error('❌ Failed to export PDF', {
        description: error instanceof Error ? error.message : 'Unknown error',
        duration: 5000,
      })
      throw error
    }
  }

  /**
   * Export table data to PDF (alternative method for structured data)
   * @param data - Array of data objects
   * @param columns - Column definitions
   * @param title - Report title
   * @param filename - PDF filename
   */
  static async exportTableToPDF(
    data: any[],
    columns: { header: string; key: string; width?: number }[],
    title: string,
    filename?: string
  ): Promise<void> {
    try {
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: 'a4',
      })

      const pageWidth = pdf.internal.pageSize.getWidth()

      // Add header
      pdf.setFontSize(16)
      pdf.setTextColor(94, 187, 168) // WARD green
      pdf.text(title, 10, 15)

      pdf.setFontSize(9)
      pdf.setTextColor(100, 100, 100)
      const now = new Date().toLocaleString('en-GB', {
        timeZone: 'Asia/Tbilisi',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
      pdf.text(`Generated: ${now}`, 10, 22)

      // Prepare table data
      const headers = columns.map((col) => col.header)
      const rows = data.map((row) =>
        columns.map((col) => {
          const value = row[col.key]
          return value !== null && value !== undefined ? String(value) : 'N/A'
        })
      )

      // Simple table rendering (without autoTable plugin for now)
      let y = 30
      const cellHeight = 7
      const cellPadding = 2

      // Calculate column widths
      const totalWidth = pageWidth - 20
      const colWidths = columns.map((col) => col.width || totalWidth / columns.length)

      // Draw header row
      pdf.setFillColor(94, 187, 168)
      pdf.setTextColor(255, 255, 255)
      pdf.setFontSize(9)

      let x = 10
      headers.forEach((header, i) => {
        pdf.rect(x, y, colWidths[i], cellHeight, 'F')
        pdf.text(header, x + cellPadding, y + cellHeight - cellPadding)
        x += colWidths[i]
      })

      y += cellHeight

      // Draw data rows
      pdf.setTextColor(0, 0, 0)
      rows.forEach((row, rowIndex) => {
        // Check if we need a new page
        if (y > pdf.internal.pageSize.getHeight() - 20) {
          pdf.addPage()
          y = 15
        }

        // Alternating row colors
        if (rowIndex % 2 === 0) {
          pdf.setFillColor(245, 245, 245)
          pdf.rect(10, y, pageWidth - 20, cellHeight, 'F')
        }

        let x = 10
        row.forEach((cell, i) => {
          pdf.text(cell.substring(0, 50), x + cellPadding, y + cellHeight - cellPadding)
          x += colWidths[i]
        })

        y += cellHeight
      })

      // Save
      const finalFilename = filename || `${title.toLowerCase().replace(/\s/g, '-')}.pdf`
      pdf.save(finalFilename)

      toast.success('✅ PDF table exported successfully!', {
        description: `Downloaded: ${finalFilename}`,
      })
    } catch (error) {
      console.error('PDF table export failed:', error)
      toast.error('❌ Failed to export table')
      throw error
    }
  }
}
