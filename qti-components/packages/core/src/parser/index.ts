/**
 * Parser module exports
 */

// XML utilities (escapeXml and generateId are exported from utils)
export {
  parseXmlString,
  getTextContent,
  getAttribute,
  getNumberAttribute,
  getBooleanAttribute,
  getChildElements,
  getChildElement,
  getInnerHtml,
} from './xml-utils'

// IML parser
export { parseIml } from './iml-parser'

// IML to QTI converter
export { imlToQti } from './iml-to-qti'
