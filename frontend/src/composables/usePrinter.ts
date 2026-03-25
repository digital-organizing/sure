import { ref, computed } from 'vue'
import { jsPDF } from 'jspdf'
import JsBarcode from 'jsbarcode'

// DYMO Connect Framework types
declare global {
  interface Window {
    dymo: {
      label: {
        framework: {
          init: () => void
          checkEnvironment: () => Promise<DymoEnvironment>
          getPrinters: () => DymoPrinter[]
          openLabelXml: (labelXml: string) => DymoLabel
          printLabel: (
            printerName: string,
            printParamsXml: string,
            labelXml: string,
            labelSetXml: string,
          ) => void
          renderLabel: (labelXml: string, renderParamsXml: string, printerName: string) => string
        }
      }
    }
  }
}

interface DymoEnvironment {
  isFrameworkInstalled: boolean
  isBrowserSupported: boolean
  isWebServicePresent: boolean
  errorDetails: string
}

interface DymoPrinter {
  name: string
  modelName: string
  isConnected: boolean
  isLocal: boolean
  isTwinTurbo: boolean
}

interface DymoLabel {
  isValidLabel: () => boolean
  isDCDLabel: () => boolean
  isDLSLabel: () => boolean
  setObjectText: (objectName: string, text: string) => void
  getLabelXml: () => string
}

// Barcode label template for DYMO LabelWriter
// Uses a standard 1" x 2" label with a Code128 barcode
const createBarcodeLabelXml = (
  barcodeValue: string,
): string => `<?xml version="1.0" encoding="utf-8"?>
<DesktopLabel Version="1">
  <DYMOLabel Version="3">
    <Description>Barcode Label</Description>
    <Orientation>Landscape</Orientation>
    <LabelName>Address</LabelName>
    <InitialLength>0</InitialLength>
    <BorderStyle>SolidLine</BorderStyle>
    <DYMORect>
      <DYMOPoint>
        <X>0</X>
        <Y>0</Y>
      </DYMOPoint>
      <Size>
        <Width>1896</Width>
        <Height>522</Height>
      </Size>
    </DYMORect>
    <BorderColor>
      <SolidColorBrush>
        <Color A="1" R="0" G="0" B="0"></Color>
      </SolidColorBrush>
    </BorderColor>
    <BorderThickness>1</BorderThickness>
    <Show_Border>False</Show_Border>
    <DynamicLayoutManager>
      <RotationBehavior>ClearObjects</RotationBehavior>
      <LabelObjects>
        <BarcodeObject>
          <Name>Barcode</Name>
          <Brushes>
            <BackgroundBrush>
              <SolidColorBrush>
                <Color A="0" R="255" G="255" B="255"></Color>
              </SolidColorBrush>
            </BackgroundBrush>
            <BorderBrush>
              <SolidColorBrush>
                <Color A="1" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </BorderBrush>
            <StrokeBrush>
              <SolidColorBrush>
                <Color A="1" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </StrokeBrush>
            <FillBrush>
              <SolidColorBrush>
                <Color A="1" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </FillBrush>
          </Brushes>
          <Rotation>Rotation0</Rotation>
          <OutlineThickness>1</OutlineThickness>
          <IsOutlined>False</IsOutlined>
          <BorderStyle>SolidLine</BorderStyle>
          <Margin>
            <DYMOThickness Left="0" Top="0" Right="0" Bottom="0" />
          </Margin>
          <BarcodeFormat>Code128Auto</BarcodeFormat>
          <Data>
            <DataString>${escapeXml(barcodeValue)}</DataString>
          </Data>
          <HorizontalAlignment>Center</HorizontalAlignment>
          <VerticalAlignment>Middle</VerticalAlignment>
          <Size>Large</Size>
          <TextPosition>Bottom</TextPosition>
          <FontInfo>
            <FontName>Arial</FontName>
            <FontSize>10</FontSize>
            <IsBold>False</IsBold>
            <IsItalic>False</IsItalic>
            <IsUnderline>False</IsUnderline>
            <FontBrush>
              <SolidColorBrush>
                <Color A="1" R="0" G="0" B="0"></Color>
              </SolidColorBrush>
            </FontBrush>
          </FontInfo>
          <ObjectLayout>
            <DYMOPoint>
              <X>100</X>
              <Y>50</Y>
            </DYMOPoint>
            <Size>
              <Width>1696</Width>
              <Height>422</Height>
            </Size>
          </ObjectLayout>
        </BarcodeObject>
      </LabelObjects>
    </DynamicLayoutManager>
  </DYMOLabel>
</DesktopLabel>`

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

export function usePrinter() {
  const isInitialized = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const printers = ref<DymoPrinter[]>([
    {
      isConnected: true,
      isLocal: true,
      modelName: 'DYMO LabelWriter 450 Twin Turbo',
      isTwinTurbo: true,
      name: 'DYMO LabelWriter 450 Twin Turbo',
    },
    {
      isConnected: false,
      isLocal: true,
      modelName: 'DYMO LabelWriter 450 Twin Turbo',
      isTwinTurbo: true,
      name: 'DYMO LabelWriter 450 Twin Turbo 2',
    },
    {
      isConnected: false,
      isLocal: true,
      modelName: 'DYMO LabelWriter 450 Twin Turbo',
      isTwinTurbo: true,
      name: 'DYMO LabelWriter 450 Twin Turbo 2',
    },
  ])
  const selectedPrinter = ref<string | null>(null)

  const availablePrinters = computed(() => printers.value.filter((p) => p.isConnected))

  const hasConnectedPrinter = computed(() => availablePrinters.value.length > 0)

  /**
   * Initialize the DYMO framework and check environment
   */
  async function initialize(): Promise<boolean> {
    if (isInitialized.value) return true

    isLoading.value = true
    error.value = null

    try {
      if (!window.dymo?.label?.framework) {
        throw new Error(
          'DYMO Connect Framework nicht geladen. Bitte stellen Sie sicher, dass das Script eingebunden ist.',
        )
      }

      window.dymo.label.framework.init()

      const env = await window.dymo.label.framework.checkEnvironment()

      if (!env.isWebServicePresent) {
        throw new Error(
          'DYMO Web Service nicht gefunden. Bitte stellen Sie sicher, dass DYMO Connect Software installiert und gestartet ist.',
        )
      }

      if (!env.isBrowserSupported) {
        throw new Error('Dieser Browser wird von DYMO Connect nicht unterstützt.')
      }

      await refreshPrinters()
      isInitialized.value = true
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unbekannter Fehler bei der Initialisierung'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Refresh the list of available printers
   */
  async function refreshPrinters(): Promise<void> {
    try {
      const printerList = window.dymo.label.framework.getPrinters()
      printers.value = printerList

      // Auto-select first connected printer if none selected
      if (!selectedPrinter.value && printerList.length > 0) {
        const connected = printerList.find((p) => p.isConnected)
        if (connected) {
          selectedPrinter.value = connected.name
        }
      }
    } catch (e) {
      error.value = 'Fehler beim Abrufen der Drucker'
      throw e
    }
  }

  /**
   * Print a single barcode label
   */
  async function printBarcode(code: string, printerName?: string): Promise<void> {
    const printer = printerName || selectedPrinter.value

    if (!printer) {
      throw new Error('Kein Drucker ausgewählt')
    }

    if (!isInitialized.value) {
      const success = await initialize()
      if (!success) {
        throw new Error(error.value || 'Initialisierung fehlgeschlagen')
      }
    }

    const labelXml = createBarcodeLabelXml(code)
    const printParamsXml = ''
    const labelSetXml = ''

    try {
      window.dymo.label.framework.printLabel(printer, printParamsXml, labelXml, labelSetXml)
    } catch (e) {
      throw new Error(`Fehler beim Drucken: ${e instanceof Error ? e.message : 'Unbekannt'}`)
    }
  }

  /**
   * Print multiple barcode labels
   */
  async function printLabels(codes: string[], printerName?: string): Promise<void> {
    if (!codes || codes.length === 0) {
      throw new Error('Keine Barcodes zum Drucken angegeben')
    }

    isLoading.value = true
    error.value = null

    try {
      if (!isInitialized.value) {
        const success = await initialize()
        if (!success) {
          throw new Error(error.value || 'Initialisierung fehlgeschlagen')
        }
      }

      for (const code of codes) {
        await printBarcode(code, printerName)
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Drucken'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get a preview image of a barcode label (base64 PNG)
   */
  async function getPreview(code: string, printerName?: string): Promise<string> {
    const printer = printerName || selectedPrinter.value

    if (!printer) {
      throw new Error('Kein Drucker ausgewählt')
    }

    if (!isInitialized.value) {
      await initialize()
    }

    const labelXml = createBarcodeLabelXml(code)
    const renderParamsXml = ''

    return window.dymo.label.framework.renderLabel(labelXml, renderParamsXml, printer)
  }

  /**
   * Generate a barcode as SVG string
   */
  function generateBarcodeSvg(code: string): string {
    const svgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg')

    JsBarcode(svgElement, code, {
      format: 'CODE128',
      width: 2,
      height: 80,
      displayValue: true,
      fontSize: 14,
      margin: 10,
      background: '#ffffff',
      lineColor: '#000000',
    })

    return new XMLSerializer().serializeToString(svgElement)
  }

  /**
   * Convert SVG string to base64 data URL via canvas
   */
  async function svgToDataUrl(svgString: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const img = new Image()
      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
      const url = URL.createObjectURL(svgBlob)

      img.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = img.width
        canvas.height = img.height

        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Canvas context nicht verfügbar'))
          return
        }

        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(img, 0, 0)

        URL.revokeObjectURL(url)
        resolve(canvas.toDataURL('image/png'))
      }

      img.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('Fehler beim Laden des Barcode-Bildes'))
      }

      img.src = url
    })
  }

  /**
   * Generate a PDF with barcodes as individual pages (fallback for users without printer)
   * Each barcode is on its own page, sized for standard label printing
   */
  async function generateBarcodePdf(
    codes: string[],
    options?: {
      filename?: string
      download?: boolean
      pageWidth?: number // in mm
      pageHeight?: number // in mm
    },
  ): Promise<Blob> {
    if (!codes || codes.length === 0) {
      throw new Error('Keine Barcodes zum Generieren angegeben')
    }

    isLoading.value = true
    error.value = null

    const {
      filename = 'barcodes.pdf',
      download = true,
      pageWidth = 89, // Standard DYMO label width in mm
      pageHeight = 36, // Standard DYMO label height in mm
    } = options || {}

    try {
      // Create PDF with custom page size matching label dimensions
      const pdf = new jsPDF({
        orientation: pageWidth > pageHeight ? 'landscape' : 'portrait',
        unit: 'mm',
        format: [pageWidth, pageHeight],
      })

      for (let i = 0; i < codes.length; i++) {
        const code = codes[i]!

        if (i > 0) {
          pdf.addPage([pageWidth, pageHeight])
        }

        // Generate barcode as SVG and convert to image
        const svgString = generateBarcodeSvg(code)
        const dataUrl = await svgToDataUrl(svgString)

        // Calculate dimensions to fit barcode centered on page
        const margin = 3 // mm
        const availableWidth = pageWidth - 2 * margin
        const availableHeight = pageHeight - 2 * margin

        // Add barcode image centered on page
        const barcodeWidth = availableWidth
        const barcodeHeight = availableHeight
        const x = margin
        const y = margin

        pdf.addImage(dataUrl, 'PNG', x, y, barcodeWidth, barcodeHeight)
      }

      const pdfBlob = pdf.output('blob')

      if (download) {
        // Trigger download
        const url = URL.createObjectURL(pdfBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      }

      return pdfBlob
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Generieren des PDFs'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    isInitialized,
    isLoading,
    error,
    printers,
    selectedPrinter,
    availablePrinters,
    hasConnectedPrinter,

    // Methods
    initialize,
    refreshPrinters,
    printBarcode,
    printLabels,
    getPreview,
    generateBarcodePdf,
  }
}
