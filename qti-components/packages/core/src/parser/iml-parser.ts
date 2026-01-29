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
  ImlTable,
  ImlTableRow,
  ImlTableCell,
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
        // Parse <보기> (example box) - contains paragraphs inside
        const boxTitle = getAttribute(child, 'title') || '<보기>'
        content.push({
          type: 'paragraph',
          content: [`[${boxTitle}]`],
        })
        // Recursively parse content inside <보기>
        content.push(...parseBlockContent(child))
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

  // Parse mixed content: <문자열>, <수식>, <그림> elements
  const content: Array<string | ImlMath | ImlImage> = []

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
      } else if (tagName === '그림' || tagName === 'img') {
        content.push({
          type: 'image',
          src: getAttribute(el, 'src') || getAttribute(el, '경로') || '',
          alt: getAttribute(el, 'alt') || getAttribute(el, '설명') || undefined,
          width: getNumberAttribute(el, 'width') || getNumberAttribute(el, 'w') || undefined,
          height: getNumberAttribute(el, 'height') || getNumberAttribute(el, 'h') || undefined,
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
  return {
    type: 'image',
    src: getAttribute(element, 'src') || getAttribute(element, '경로'),
    alt: getAttribute(element, 'alt') || getAttribute(element, '설명') || undefined,
    width: getNumberAttribute(element, 'width') || undefined,
    height: getNumberAttribute(element, 'height') || undefined,
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

        cells.push({
          type: cellTagName === 'TH' ? 'th' : 'td',
          content: cellContent,
          colspan: getNumberAttribute(cell, 'colspan') ||
                   (getNumberAttribute(cell, 'cnt')?.toString().split(',')[0] ? undefined : undefined),
          rowspan: getNumberAttribute(cell, 'rowspan') || undefined,
        })
      }
    }

    if (cells.length > 0) {
      rows.push({ cells })
    }
  }

  return {
    type: 'table',
    rows,
    border: getNumberAttribute(element, 'border') || 1,
    width: getAttribute(element, 'width') || undefined,
  }
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

  return {
    ...common,
    itemType,
    choices,
    multipleAnswers,
    shuffle: getBooleanAttribute(root, 'shuffle'),
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

  const blanksEl = getChildElement(root, '빈칸목록') || getChildElement(root, 'blanks')
  const blanks: ImlFillBlankItem['blanks'] = []

  if (blanksEl) {
    for (const blankEl of getChildElements(blanksEl, '빈칸').concat(
      getChildElements(blanksEl, 'blank')
    )) {
      const id = getAttribute(blankEl, 'id') || generateId('blank')
      const answersText = getTextContent(blankEl)
      const correctAnswers = answersText.includes('|')
        ? answersText.split('|').map(s => s.trim())
        : [answersText]

      blanks.push({
        id,
        correctAnswers,
        caseSensitive: getBooleanAttribute(blankEl, 'caseSensitive'),
      })
    }
  }

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
