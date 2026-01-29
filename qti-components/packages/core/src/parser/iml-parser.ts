/**
 * IML (IOSYS Markup Language) Parser
 * Parses IML XML documents into ImlItem objects
 */

import type {
  ImlItem,
  ImlItemTypeCode,
  ImlChoiceItem,
  ImlTrueFalseItem,
  ImlShortAnswerItem,
  ImlFillBlankItem,
  ImlMatchingItem,
  ImlEssayShortItem,
  ImlEssayLongItem,
  ImlBlockContent,
  ImlParagraph,
  ImlImage,
  ImlMath,
  ImlBlank,
  ImlTable,
  ImlTableRow,
  ImlTableCell,
  ImlExampleBox,
  ImlChoiceAnswer,
  ImlMatchItem,
  ImlMatchPair,
  ImlQuestion,
  ImlExplanation,
} from '../types/iml'

import { IML_ITEM_TYPES } from '../types/iml'

import {
  parseXmlString,
  getTextContent,
  getAttribute,
  getNumberAttribute,
  getBooleanAttribute,
  getChildElement,
  getChildElements,
  generateId,
} from './xml-utils'

/**
 * Parse IML XML string to ImlItem
 */
export function parseIml(xmlString: string): ImlItem {
  const doc = parseXmlString(xmlString)
  const root = doc.documentElement

  // Navigate to the actual item element
  // Structure: <문항종류> -> <단위문항> -> <문항>
  const itemElement = findItemElement(root)

  // Get item type from element attribute
  const itemTypeCode = getItemTypeCode(itemElement)

  switch (itemTypeCode) {
    case IML_ITEM_TYPES.CHOICE:
      return parseChoiceItem(itemElement, itemTypeCode)
    case IML_ITEM_TYPES.TRUE_FALSE:
      return parseTrueFalseItem(itemElement, itemTypeCode)
    case IML_ITEM_TYPES.SHORT_ANSWER:
      return parseShortAnswerItem(itemElement, itemTypeCode)
    case IML_ITEM_TYPES.FILL_BLANK:
      return parseFillBlankItem(itemElement, itemTypeCode)
    case IML_ITEM_TYPES.MATCHING:
      return parseMatchingItem(itemElement, itemTypeCode)
    case IML_ITEM_TYPES.ESSAY_SHORT:
      return parseEssayItem(itemElement, itemTypeCode) as ImlEssayShortItem
    case IML_ITEM_TYPES.ESSAY_LONG:
      return parseEssayItem(itemElement, itemTypeCode) as ImlEssayLongItem
    default:
      throw new Error(`Unsupported item type: ${itemTypeCode}`)
  }
}

/**
 * Find the actual item element in the IML document
 * Handles structures like: <문항종류> -> <단위문항> -> <문항>
 */
function findItemElement(root: Element): Element {
  // Direct <문항> element
  if (root.tagName === '문항' || root.tagName === 'item') {
    return root
  }

  // Look for <문항> in children
  const itemEl = getChildElement(root, '문항') || getChildElement(root, 'item')
  if (itemEl) {
    return itemEl
  }

  // Look inside <단위문항> wrapper
  const wrapperEl = getChildElement(root, '단위문항')
  if (wrapperEl) {
    const innerItemEl = getChildElement(wrapperEl, '문항') || getChildElement(wrapperEl, 'item')
    if (innerItemEl) {
      return innerItemEl
    }
    return wrapperEl
  }

  // Return root if no specific element found
  return root
}

/**
 * Extract item type code from element
 */
function getItemTypeCode(element: Element): ImlItemTypeCode {
  // Try qt attribute (format: "34 완결형" -> extract "34")
  const qtAttr = getAttribute(element, 'qt')
  if (qtAttr) {
    const typeCode = qtAttr.split(' ')[0]
    if (isValidItemType(typeCode)) {
      return typeCode
    }
  }

  // Try vt attribute (variant type)
  const vtAttr = getAttribute(element, 'vt')
  if (vtAttr) {
    const typeCode = vtAttr.split(' ')[0]
    if (isValidItemType(typeCode)) {
      return typeCode
    }
  }

  // Try different attribute names
  const typeAttr =
    getAttribute(element, '문항유형') ||
    getAttribute(element, 'itemType') ||
    getAttribute(element, 'type')

  if (typeAttr && isValidItemType(typeAttr)) {
    return typeAttr
  }

  // Try to find 문항종류 element
  const typeElement = getChildElement(element, '문항종류')
  if (typeElement) {
    const typeCode = getTextContent(typeElement)
    if (isValidItemType(typeCode)) {
      return typeCode
    }
  }

  // Default to choice
  return IML_ITEM_TYPES.CHOICE
}

function isValidItemType(code: string | undefined): code is ImlItemTypeCode {
  return code !== undefined && ['11', '21', '31', '34', '37', '41', '51'].includes(code)
}

/**
 * Parse common item properties
 */
function parseCommonProps(root: Element, itemType: ImlItemTypeCode) {
  const id = getAttribute(root, 'id') || generateId('item')

  // Parse question: <문제> -> <물음>
  const questionEl = getChildElement(root, '문제') || getChildElement(root, 'question')
  let questionContent: ImlBlockContent[] = []

  if (questionEl) {
    // Check for <물음> inside <문제>
    const questionBodyEl = getChildElement(questionEl, '물음')
    if (questionBodyEl) {
      questionContent = parseBlockContent(questionBodyEl)
    } else {
      questionContent = parseBlockContent(questionEl)
    }
  }

  const question: ImlQuestion = {
    content: questionContent,
  }

  // Parse explanation: <문제> -> <해설> or top-level <해설>
  let explanationEl = getChildElement(root, '해설') || getChildElement(root, 'explanation')
  if (!explanationEl && questionEl) {
    explanationEl = getChildElement(questionEl, '해설')
  }
  const explanation: ImlExplanation | undefined = explanationEl
    ? { content: parseBlockContent(explanationEl) }
    : undefined

  // Parse metadata from attributes
  const dfAttr = getAttribute(root, 'df')
  const difficultyAttr = dfAttr?.split(' ')[1] || getAttribute(root, '난이도') || getAttribute(root, 'difficulty')
  const difficulty: 'high' | 'medium' | 'low' = difficultyAttr === '상' || difficultyAttr === 'high'
    ? 'high'
    : difficultyAttr === '하' || difficultyAttr === 'low'
      ? 'low'
      : 'medium'

  const score = getNumberAttribute(root, '배점') || getNumberAttribute(root, 'score')

  return {
    id,
    itemType,
    question,
    explanation,
    score: score || undefined,
    difficulty,
    curriculum: getAttribute(root, 'cls1')?.split(' ')[1] || getAttribute(root, '교육과정') || undefined,
    achievementStandard: getAttribute(root, '성취기준') || undefined,
    source: getAttribute(root, '출처') || undefined,
  }
}

/**
 * Parse block content (paragraphs, images, math, tables)
 */
function parseBlockContent(parent: Element): ImlBlockContent[] {
  const content: ImlBlockContent[] = []

  for (const child of Array.from(parent.children)) {
    const tagName = child.tagName.toLowerCase()

    switch (tagName) {
      case '단락':
      case 'p':
      case 'paragraph':
        content.push(parseParagraph(child))
        break
      case '그림':
      case 'img':
      case 'image':
        content.push(parseImage(child))
        break
      case '수식':
      case 'math':
        content.push(parseMathElement(child))
        break
      case '테이블':
      case 'table':
        content.push(parseTable(child))
        break
      case '보기':
        // Parse <보기> (example box) as ImlExampleBox
        content.push(parseExampleBox(child))
        break
      case '형판':
        // Skip template element (formatting instruction)
        break
      default:
        // Wrap unknown elements as paragraphs
        if (child.textContent?.trim()) {
          content.push({
            type: 'paragraph',
            content: [child.textContent.trim()],
          })
        }
    }
  }

  // If no children but has text content, create a paragraph
  if (content.length === 0 && parent.textContent?.trim()) {
    content.push({
      type: 'paragraph',
      content: [parent.textContent.trim()],
    })
  }

  return content
}

function parseParagraph(element: Element): ImlParagraph {
  const align = getAttribute(element, 'align') || getAttribute(element, 'justv')
  const alignValue = align === '1' ? 'center' : align === '2' ? 'right' : undefined

  // Parse mixed content: <문자열>, <수식>, <그림>, <답박스> elements
  const content: Array<string | ImlMath | ImlImage | ImlBlank> = []

  for (const child of Array.from(element.childNodes)) {
    if (child.nodeType === 3) { // Text node
      const text = child.textContent?.trim()
      if (text) {
        content.push(text)
      }
    } else if (child.nodeType === 1) { // Element node
      const el = child as Element
      const tagName = el.tagName

      if (tagName === '문자열') {
        const text = getTextContent(el)
        if (text) {
          content.push(text)
        }
      } else if (tagName === '수식') {
        content.push({
          type: 'math',
          latex: getTextContent(el) || getAttribute(el, 'latex') || '',
          display: 'inline',
        })
      } else if (tagName === '그림' || tagName === '문자그림' || tagName === 'img') {
        // IML image: text content contains actual file path (e.g., "ItemID\DrawObjPic\image.jpg")
        const textContent = el.textContent?.trim() || ''
        const hasPathInfo = textContent.includes('\\') || textContent.includes('/') ||
                            /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i.test(textContent)

        const imgSrc = (hasPathInfo ? textContent : '') ||
                       getAttribute(el, 'original') ||
                       getAttribute(el, 'preview') ||
                       getAttribute(el, 'src') ||
                       getAttribute(el, '경로') ||
                       textContent || ''

        // Convert percentage to pixels based on standard item width
        const BASE_WIDTH = 600
        const wPct = getNumberAttribute(el, 'w')
        const hPct = getNumberAttribute(el, 'h')
        const owVal = getNumberAttribute(el, 'ow')
        const ohVal = getNumberAttribute(el, 'oh')

        let imgWidth: number | undefined
        let imgHeight: number | undefined

        if (wPct && hPct) {
          imgWidth = Math.round((wPct / 100) * BASE_WIDTH)
          imgHeight = Math.round((hPct / 100) * BASE_WIDTH)
        } else if (owVal && ohVal) {
          const maxD = 400
          if (owVal > maxD || ohVal > maxD) {
            const sc = Math.min(maxD / owVal, maxD / ohVal)
            imgWidth = Math.round(owVal * sc)
            imgHeight = Math.round(ohVal * sc)
          } else {
            imgWidth = owVal
            imgHeight = ohVal
          }
        }

        // Extract alignment
        const justh = getAttribute(el, 'justh')
        const center = getAttribute(el, 'Center')
        let imgAlign: 'left' | 'center' | 'right' | undefined
        if (justh === 'C' || center === '1') {
          imgAlign = 'center'
        } else if (justh === 'R') {
          imgAlign = 'right'
        } else if (justh === 'L') {
          imgAlign = 'left'
        }

        content.push({
          type: 'image',
          src: imgSrc,
          alt: getAttribute(el, 'alt') || getAttribute(el, '설명') || undefined,
          width: imgWidth,
          height: imgHeight,
          align: imgAlign,
        })
      } else if (tagName === '답박스') {
        // 완성형 문항의 빈칸 (did: 답박스 순서 ID, iLenEng: 영문 기준 길이)
        const did = getAttribute(el, 'did') || generateId('blank')
        const iLenEng = getNumberAttribute(el, 'iLenEng')
        content.push({
          type: 'blank',
          id: did,
          size: iLenEng,
        })
      }
    }
  }

  // Fallback: if no content parsed, get text content
  if (content.length === 0) {
    const text = getTextContent(element)
    if (text) {
      content.push(text)
    }
  }

  return {
    type: 'paragraph',
    align: alignValue as ImlParagraph['align'],
    content,
  }
}

function parseImage(element: Element): ImlImage {
  // IML image path priority:
  // 1. Text content (actual file path like "ItemID\DrawObjPic\image.jpg")
  // 2. original/preview attributes (full path)
  // 3. src/경로 attributes (standard)
  // 4. name attribute (just identifier, not actual path - avoid using)
  const textContent = element.textContent?.trim() || ''

  // Text content is the actual file path if it contains path separators or file extension
  const hasPathInfo = textContent.includes('\\') || textContent.includes('/') ||
                      /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/i.test(textContent)

  const src = (hasPathInfo ? textContent : '') ||
              getAttribute(element, 'original') ||
              getAttribute(element, 'preview') ||
              getAttribute(element, 'src') ||
              getAttribute(element, '경로') ||
              textContent || ''

  // IML size attributes:
  // - w, h: percentage of item width (use this for display)
  // - ow, oh: original image pixel size (too large, only use for aspect ratio)
  // Convert percentage to pixels based on standard item width (~600px)
  const BASE_ITEM_WIDTH = 600
  const wPercent = getNumberAttribute(element, 'w')
  const hPercent = getNumberAttribute(element, 'h')
  const ow = getNumberAttribute(element, 'ow')
  const oh = getNumberAttribute(element, 'oh')

  let width: number | undefined
  let height: number | undefined

  if (wPercent && hPercent) {
    // Use percentage values converted to pixels
    width = Math.round((wPercent / 100) * BASE_ITEM_WIDTH)
    height = Math.round((hPercent / 100) * BASE_ITEM_WIDTH)
  } else if (ow && oh) {
    // Fallback to original size but cap at reasonable max
    const maxDim = 400
    if (ow > maxDim || oh > maxDim) {
      const scale = Math.min(maxDim / ow, maxDim / oh)
      width = Math.round(ow * scale)
      height = Math.round(oh * scale)
    } else {
      width = ow
      height = oh
    }
  }

  // IML alignment: justh (L=left, C=center, R=right), Center (1=center)
  const justh = getAttribute(element, 'justh')
  const center = getAttribute(element, 'Center')
  let align: 'left' | 'center' | 'right' | undefined
  if (justh === 'C' || center === '1') {
    align = 'center'
  } else if (justh === 'R') {
    align = 'right'
  } else if (justh === 'L') {
    align = 'left'
  }

  return {
    type: 'image',
    src,
    alt: getAttribute(element, 'alt') || getAttribute(element, '설명') || undefined,
    width,
    height,
    align,
  }
}

function parseMathElement(element: Element): ImlMath {
  return {
    type: 'math',
    latex: getTextContent(element) || getAttribute(element, 'latex'),
    display: getAttribute(element, 'display') === 'block' ? 'block' : 'inline',
  }
}

function parseTable(element: Element): ImlTable {
  const rows: ImlTableRow[] = []

  // Parse column width ratios (format: "width1;width2;...;widthN")
  const colWidthsAttr = getAttribute(element, 'colBaseWidthRates')
  let colWidths: number[] | undefined
  if (colWidthsAttr) {
    colWidths = colWidthsAttr.split(';').map(w => parseFloat(w)).filter(w => !isNaN(w))
    if (colWidths.length === 0) colWidths = undefined
  }

  // Handle both <TR> and <tr> elements
  const trElements = getChildElements(element, 'TR').length > 0
    ? getChildElements(element, 'TR')
    : getChildElements(element, 'tr')

  for (const tr of trElements) {
    const cells: ImlTableCell[] = []

    for (const cell of Array.from(tr.children)) {
      const cellTagName = cell.tagName.toUpperCase()
      // Handle CELL (IML format) and TD/TH (standard HTML)
      if (cellTagName === 'CELL' || cellTagName === 'TD' || cellTagName === 'TH') {
        // For CELL elements, parse the content inside (may have <물음> wrapper)
        let cellContent: ImlBlockContent[]
        const innerContent = getChildElement(cell, '물음')
        if (innerContent) {
          cellContent = parseBlockContent(innerContent)
        } else {
          cellContent = parseBlockContent(cell)
        }

        // Parse cell position/size (IML uses percentage)
        const x = getNumberAttribute(cell, 'x')
        const y = getNumberAttribute(cell, 'y')
        const w = getNumberAttribute(cell, 'w')
        const h = getNumberAttribute(cell, 'h')

        // Parse colspan/rowspan from cnt attribute (format: "cols,rows")
        const cntAttr = getAttribute(cell, 'cnt')
        let colspan: number | undefined
        let rowspan: number | undefined
        if (cntAttr) {
          const parts = cntAttr.split(',')
          if (parts[0]) colspan = parseInt(parts[0], 10)
          if (parts[1]) rowspan = parseInt(parts[1], 10)
          if (colspan === 1) colspan = undefined
          if (rowspan === 1) rowspan = undefined
        }
        // Also check standard HTML attributes
        colspan = colspan || getNumberAttribute(cell, 'colspan') || undefined
        rowspan = rowspan || getNumberAttribute(cell, 'rowspan') || undefined

        // Parse vertical alignment (cjustv: 1=top, 2=bottom, 3=center)
        const cjustv = getAttribute(cell, 'cjustv')
        let valign: 'top' | 'middle' | 'bottom' | undefined
        if (cjustv === '1') valign = 'top'
        else if (cjustv === '2') valign = 'bottom'
        else if (cjustv === '3') valign = 'middle'

        // Parse background color (RGB integer)
        const colbk = getAttribute(cell, 'colbk')
        let backgroundColor: string | undefined
        if (colbk) {
          const colorNum = parseInt(colbk, 10)
          if (!isNaN(colorNum)) {
            const r = colorNum & 0xff
            const g = (colorNum >> 8) & 0xff
            const b = (colorNum >> 16) & 0xff
            backgroundColor = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
          }
        }

        // Parse border info (format: "left,top,right,bottom")
        const borderInfoAttr = getAttribute(cell, 'borderinfo')
        let borderInfo: [number, number, number, number] | undefined
        if (borderInfoAttr) {
          const parts = borderInfoAttr.split(',').map(p => parseInt(p, 10))
          if (parts.length === 4 && parts.every(p => !isNaN(p))) {
            borderInfo = parts as [number, number, number, number]
          }
        }

        const cellData: ImlTableCell = {
          type: cellTagName === 'TH' ? 'th' : 'td',
          content: cellContent,
        }

        // Only add optional properties if they have values
        if (x !== undefined) cellData.x = x
        if (y !== undefined) cellData.y = y
        if (w !== undefined) cellData.w = w
        if (h !== undefined) cellData.h = h
        if (colspan) cellData.colspan = colspan
        if (rowspan) cellData.rowspan = rowspan
        if (valign) cellData.valign = valign
        if (backgroundColor) cellData.backgroundColor = backgroundColor
        if (borderInfo) cellData.borderInfo = borderInfo

        cells.push(cellData)
      }
    }

    if (cells.length > 0) {
      rows.push({ cells })
    }
  }

  const result: ImlTable = {
    type: 'table',
    rows,
  }

  if (colWidths) result.colWidths = colWidths

  // Legacy attributes
  const border = getNumberAttribute(element, 'border')
  if (border !== undefined) result.border = border
  const width = getAttribute(element, 'width')
  if (width) result.width = width

  return result
}

/**
 * Parse example box (보기)
 */
function parseExampleBox(element: Element): ImlExampleBox {
  // Get title attribute
  const title = getAttribute(element, 'title') || '보기'

  // Get title alignment: 0=left, 1=center, 2=right
  const titlejust = getAttribute(element, 'titlejust')
  let titleAlign: 'left' | 'center' | 'right' | undefined
  if (titlejust === '1') {
    titleAlign = 'center'
  } else if (titlejust === '2') {
    titleAlign = 'right'
  } else if (titlejust === '0') {
    titleAlign = 'left'
  }

  // Get border attribute (0=no border, non-zero=has border)
  const borderAttr = getAttribute(element, 'border')
  const border = borderAttr ? borderAttr !== '0' : true // default to border

  // Get background color (colbk attribute, RGB value)
  const colbk = getAttribute(element, 'colbk')
  let backgroundColor: string | undefined
  if (colbk) {
    // Convert RGB number to hex if needed
    const colorNum = parseInt(colbk, 10)
    if (!isNaN(colorNum)) {
      // Convert RGB integer to hex color
      const r = colorNum & 0xff
      const g = (colorNum >> 8) & 0xff
      const b = (colorNum >> 16) & 0xff
      backgroundColor = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
    } else {
      backgroundColor = colbk
    }
  }

  // Parse content: <보기> contains <물음> elements
  let boxContent: ImlBlockContent[] = []
  const questionElements = getChildElements(element, '물음')
  if (questionElements.length > 0) {
    for (const qEl of questionElements) {
      boxContent.push(...parseBlockContent(qEl))
    }
  } else {
    // Fallback: parse direct children
    boxContent = parseBlockContent(element)
  }

  const result: ImlExampleBox = {
    type: 'exampleBox',
    title,
    border,
    content: boxContent,
  }

  // Only add optional properties if they have values
  if (titleAlign) {
    result.titleAlign = titleAlign
  }
  if (backgroundColor) {
    result.backgroundColor = backgroundColor
  }

  return result
}

/**
 * Parse choice item (선다형 - type 11)
 */
function parseChoiceItem(root: Element, itemType: '11'): ImlChoiceItem {
  const common = parseCommonProps(root, itemType)

  // Parse choices from <문제> element
  // IML structure: <문항> -> <문제> -> <답항>*
  const questionEl = getChildElement(root, '문제') || getChildElement(root, 'question')
  const choices: ImlChoiceAnswer[] = []

  if (questionEl) {
    // <답항> elements are direct children of <문제>
    const choiceElements = getChildElements(questionEl, '답항')

    choiceElements.forEach((choiceEl, i) => {
      const id = getAttribute(choiceEl, 'id') || `choice_${i + 1}`
      const isCorrect =
        getBooleanAttribute(choiceEl, '정답') || getBooleanAttribute(choiceEl, 'correct')

      choices.push({
        id,
        content: parseBlockContent(choiceEl),
        isCorrect,
      })
    })
  }

  // Also check for choices wrapper (alternative format)
  if (choices.length === 0) {
    const choicesEl = getChildElement(root, '답항목록') || getChildElement(root, 'choices')
    if (choicesEl) {
      for (const choiceEl of getChildElements(choicesEl, '답항').concat(
        getChildElements(choicesEl, 'choice')
      )) {
        const id = getAttribute(choiceEl, 'id') || generateId('choice')
        const isCorrect =
          getBooleanAttribute(choiceEl, '정답') || getBooleanAttribute(choiceEl, 'correct')

        choices.push({
          id,
          content: parseBlockContent(choiceEl),
          isCorrect,
        })
      }
    }
  }

  // Parse correct answer from 정답 element
  // Format could be: "1:번호" where 1 is the choice number
  const correctEl = getChildElement(root, '정답') ||
                   (questionEl && getChildElement(questionEl, '정답'))
  if (correctEl) {
    const correctText = getTextContent(correctEl)
    // Handle format like "1:7\\,일곱" - extract the choice number
    const match = correctText.match(/^(\d+):/)
    if (match && match[1]) {
      const correctNum = parseInt(match[1], 10)
      if (correctNum > 0 && correctNum <= choices.length) {
        const targetChoice = choices[correctNum - 1]
        if (targetChoice) {
          targetChoice.isCorrect = true
        }
      }
    } else if (choices.every(c => !c.isCorrect)) {
      // Try to find choice by id
      const correctChoice = choices.find(c => c.id === correctText)
      if (correctChoice) {
        correctChoice.isCorrect = true
      }
    }
  }

  // daps attribute indicates number of correct answers
  const dapsAttr = getAttribute(root, 'daps')
  const multipleAnswers = dapsAttr ? parseInt(dapsAttr, 10) > 1 : choices.filter(c => c.isCorrect).length > 1

  // dcols attribute specifies number of columns for choice layout
  // 1 = vertical, 2+ = grid layout
  const dcolsAttr = getNumberAttribute(root, 'dcols')
  const choiceColumns = dcolsAttr && dcolsAttr > 0 ? dcolsAttr : undefined

  return {
    ...common,
    itemType,
    choices,
    multipleAnswers,
    shuffle: getBooleanAttribute(root, 'shuffle'),
    choiceColumns,
  }
}

/**
 * Parse true/false item (진위형 - type 21)
 */
function parseTrueFalseItem(root: Element, itemType: '21'): ImlTrueFalseItem {
  const common = parseCommonProps(root, itemType)

  const correctEl = getChildElement(root, '정답')
  const correctText = getTextContent(correctEl).toLowerCase()
  const correctAnswer =
    correctText === 'true' || correctText === '참' || correctText === 'o' || correctText === '1'

  return {
    ...common,
    itemType,
    correctAnswer,
  }
}

/**
 * Parse short answer item (단답형 - type 31)
 */
function parseShortAnswerItem(root: Element, itemType: '31'): ImlShortAnswerItem {
  const common = parseCommonProps(root, itemType)

  const correctEl = getChildElement(root, '정답')
  const correctAnswers: string[] = []

  if (correctEl) {
    // Multiple answers can be separated by | or in multiple elements
    const text = getTextContent(correctEl)
    if (text.includes('|')) {
      correctAnswers.push(...text.split('|').map(s => s.trim()))
    } else {
      correctAnswers.push(text)
    }

    // Also check for 동의어 elements
    for (const synEl of getChildElements(correctEl, '동의어')) {
      correctAnswers.push(getTextContent(synEl))
    }
  }

  return {
    ...common,
    itemType,
    correctAnswers,
    caseSensitive: getBooleanAttribute(root, 'caseSensitive'),
    maxLength: getNumberAttribute(root, 'maxLength') || undefined,
  }
}

/**
 * Parse fill-in-the-blank item (완성형 - type 34)
 */
function parseFillBlankItem(root: Element, itemType: '34'): ImlFillBlankItem {
  const common = parseCommonProps(root, itemType)

  // Extract blanks from question content (답박스 elements)
  const blankIds: string[] = []
  const extractBlanks = (content: ImlBlockContent[]) => {
    for (const block of content) {
      if (block.type === 'paragraph') {
        for (const inline of block.content) {
          if (typeof inline === 'object' && 'type' in inline && inline.type === 'blank') {
            blankIds.push(inline.id)
          }
        }
      } else if (block.type === 'exampleBox') {
        extractBlanks(block.content)
      } else if (block.type === 'table') {
        for (const row of block.rows) {
          for (const cell of row.cells) {
            extractBlanks(cell.content)
          }
        }
      }
    }
  }
  extractBlanks(common.question.content)

  // Parse correct answers from 정답 element
  const answerEl = getChildElement(root, '정답')
  const answerMap: Record<string, string[]> = {}

  if (answerEl) {
    // Parse answer content - may contain multiple answers separated by delimiters
    const answerText = getTextContent(answerEl).trim()
    const answers = answerText.split(/[,;|]/).map(s => s.trim()).filter(Boolean)

    // Map answers to blank IDs in order
    blankIds.forEach((id, index) => {
      if (answers[index]) {
        answerMap[id] = [answers[index]]
      }
    })
  }

  // Build blanks array
  const blanks: ImlFillBlankItem['blanks'] = blankIds.map(id => ({
    id,
    correctAnswers: answerMap[id] || [''],
  }))

  return {
    ...common,
    itemType,
    blanks,
  }
}

/**
 * Parse matching item (배합형 - type 37)
 */
function parseMatchingItem(root: Element, itemType: '37'): ImlMatchingItem {
  const common = parseCommonProps(root, itemType)

  // Parse source items (left column)
  const sourceEl = getChildElement(root, '왼쪽항목') || getChildElement(root, 'sourceItems')
  const sourceItems: ImlMatchItem[] = []

  if (sourceEl) {
    for (const itemEl of getChildElements(sourceEl, '항목').concat(
      getChildElements(sourceEl, 'item')
    )) {
      sourceItems.push({
        id: getAttribute(itemEl, 'id') || generateId('source'),
        content: parseBlockContent(itemEl),
      })
    }
  }

  // Parse target items (right column)
  const targetEl = getChildElement(root, '오른쪽항목') || getChildElement(root, 'targetItems')
  const targetItems: ImlMatchItem[] = []

  if (targetEl) {
    for (const itemEl of getChildElements(targetEl, '항목').concat(
      getChildElements(targetEl, 'item')
    )) {
      targetItems.push({
        id: getAttribute(itemEl, 'id') || generateId('target'),
        content: parseBlockContent(itemEl),
      })
    }
  }

  // Parse correct matches
  const matchesEl = getChildElement(root, '정답매칭') || getChildElement(root, 'correctMatches')
  const correctMatches: ImlMatchPair[] = []

  if (matchesEl) {
    for (const matchEl of getChildElements(matchesEl, '매칭').concat(
      getChildElements(matchesEl, 'match')
    )) {
      correctMatches.push({
        sourceId: getAttribute(matchEl, 'source') || getAttribute(matchEl, '왼쪽'),
        targetId: getAttribute(matchEl, 'target') || getAttribute(matchEl, '오른쪽'),
      })
    }
  }

  return {
    ...common,
    itemType,
    sourceItems,
    targetItems,
    correctMatches,
  }
}

/**
 * Parse essay item (서술형/논술형 - type 41/51)
 */
function parseEssayItem(
  root: Element,
  itemType: '41' | '51'
): ImlEssayShortItem | ImlEssayLongItem {
  const common = parseCommonProps(root, itemType)

  const sampleEl = getChildElement(root, '예시답안') || getChildElement(root, 'sampleAnswer')
  const sampleAnswer = sampleEl ? parseBlockContent(sampleEl) : undefined

  const essayItem = {
    ...common,
    sampleAnswer,
    minLength: getNumberAttribute(root, 'minLength') || undefined,
    maxLength: getNumberAttribute(root, 'maxLength') || undefined,
  }

  if (itemType === '41') {
    return { ...essayItem, itemType: '41' as const } as ImlEssayShortItem
  }
  return { ...essayItem, itemType: '51' as const } as ImlEssayLongItem
}
