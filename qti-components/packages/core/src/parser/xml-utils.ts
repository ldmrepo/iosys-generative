/**
 * XML Parsing Utilities
 */

// Re-export from utils for internal use
export { escapeXml, generateId } from '../utils'

/**
 * Parse XML string to Document
 */
export function parseXmlString(xmlString: string): Document {
  const parser = new DOMParser()
  const doc = parser.parseFromString(xmlString, 'text/xml')

  // Check for parsing errors
  const parseError = doc.querySelector('parsererror')
  if (parseError) {
    throw new Error(`XML parsing error: ${parseError.textContent}`)
  }

  return doc
}

/**
 * Get text content of an element
 */
export function getTextContent(element: Element | null): string {
  return element?.textContent?.trim() ?? ''
}

/**
 * Get attribute value with default
 */
export function getAttribute(
  element: Element,
  name: string,
  defaultValue: string = ''
): string {
  return element.getAttribute(name) ?? defaultValue
}

/**
 * Get numeric attribute value
 */
export function getNumberAttribute(
  element: Element,
  name: string,
  defaultValue: number = 0
): number {
  const value = element.getAttribute(name)
  if (value === null) return defaultValue
  const parsed = parseFloat(value)
  return isNaN(parsed) ? defaultValue : parsed
}

/**
 * Get boolean attribute value
 */
export function getBooleanAttribute(
  element: Element,
  name: string,
  defaultValue: boolean = false
): boolean {
  const value = element.getAttribute(name)
  if (value === null) return defaultValue
  return value.toLowerCase() === 'true' || value === '1'
}

/**
 * Get all child elements with a specific tag name
 */
export function getChildElements(parent: Element, tagName: string): Element[] {
  return Array.from(parent.children).filter(
    child => child.tagName.toLowerCase() === tagName.toLowerCase()
  )
}

/**
 * Get first child element with a specific tag name
 */
export function getChildElement(parent: Element, tagName: string): Element | null {
  return (
    Array.from(parent.children).find(
      child => child.tagName.toLowerCase() === tagName.toLowerCase()
    ) ?? null
  )
}

/**
 * Convert Element's inner content to HTML string
 */
export function getInnerHtml(element: Element): string {
  const serializer = new XMLSerializer()
  let html = ''
  for (const child of Array.from(element.childNodes)) {
    if (child.nodeType === Node.TEXT_NODE) {
      html += child.textContent ?? ''
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      html += serializer.serializeToString(child)
    }
  }
  return html.trim()
}

