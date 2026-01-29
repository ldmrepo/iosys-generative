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
  getInnerHtml,
  generateId,
} from './xml-utils'

/**
 * Parse IML XML string to ImlItem
 */
export function parseIml(xmlString: string): ImlItem {
  const doc = parseXmlString(xmlString)
  const root = doc.documentElement

  // Get item type from root element or attribute
  const itemTypeCode = getItemTypeCode(root)

  switch (itemTypeCode) {
    case IML_ITEM_TYPES.CHOICE:
      return parseChoiceItem(root, itemTypeCode)
    case IML_ITEM_TYPES.TRUE_FALSE:
      return parseTrueFalseItem(root, itemTypeCode)
    case IML_ITEM_TYPES.SHORT_ANSWER:
      return parseShortAnswerItem(root, itemTypeCode)
    case IML_ITEM_TYPES.FILL_BLANK:
      return parseFillBlankItem(root, itemTypeCode)
    case IML_ITEM_TYPES.MATCHING:
      return parseMatchingItem(root, itemTypeCode)
    case IML_ITEM_TYPES.ESSAY_SHORT:
      return parseEssayItem(root, itemTypeCode) as ImlEssayShortItem
    case IML_ITEM_TYPES.ESSAY_LONG:
      return parseEssayItem(root, itemTypeCode) as ImlEssayLongItem
    default:
      throw new Error(`Unsupported item type: ${itemTypeCode}`)
  }
}

/**
 * Extract item type code from root element
 */
function getItemTypeCode(root: Element): ImlItemTypeCode {
  // Try different attribute names
  const typeAttr =
    getAttribute(root, '문항유형') ||
    getAttribute(root, 'itemType') ||
    getAttribute(root, 'type')

  if (typeAttr && isValidItemType(typeAttr)) {
    return typeAttr
  }

  // Try to find 문항종류 element
  const typeElement = getChildElement(root, '문항종류')
  if (typeElement) {
    const typeCode = getTextContent(typeElement)
    if (isValidItemType(typeCode)) {
      return typeCode
    }
  }

  // Default to choice
  return IML_ITEM_TYPES.CHOICE
}

function isValidItemType(code: string): code is ImlItemTypeCode {
  return ['11', '21', '31', '34', '37', '41', '51'].includes(code)
}

/**
 * Parse common item properties
 */
function parseCommonProps(root: Element, itemType: ImlItemTypeCode) {
  const id = getAttribute(root, 'id') || generateId('item')

  // Parse question
  const questionEl = getChildElement(root, '문제') || getChildElement(root, 'question')
  const question: ImlQuestion = {
    content: questionEl ? parseBlockContent(questionEl) : [],
  }

  // Parse explanation
  const explanationEl = getChildElement(root, '해설') || getChildElement(root, 'explanation')
  const explanation: ImlExplanation | undefined = explanationEl
    ? { content: parseBlockContent(explanationEl) }
    : undefined

  // Parse metadata
  const score = getNumberAttribute(root, '배점') || getNumberAttribute(root, 'score')
  const difficultyAttr = getAttribute(root, '난이도') || getAttribute(root, 'difficulty')
  const difficulty: 'high' | 'medium' | 'low' = difficultyAttr === '상' || difficultyAttr === 'high'
    ? 'high'
    : difficultyAttr === '하' || difficultyAttr === 'low'
      ? 'low'
      : 'medium'

  return {
    id,
    itemType,
    question,
    explanation,
    score: score || undefined,
    difficulty,
    curriculum: getAttribute(root, '교육과정') || undefined,
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
  const align = getAttribute(element, 'align') as ImlParagraph['align'] | ''
  return {
    type: 'paragraph',
    align: align || undefined,
    content: [getInnerHtml(element) || getTextContent(element)],
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

  for (const tr of getChildElements(element, 'tr')) {
    const cells: ImlTableCell[] = []

    for (const cell of Array.from(tr.children)) {
      if (cell.tagName.toLowerCase() === 'td' || cell.tagName.toLowerCase() === 'th') {
        cells.push({
          type: cell.tagName.toLowerCase() as 'td' | 'th',
          content: parseBlockContent(cell),
          colspan: getNumberAttribute(cell, 'colspan') || undefined,
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
    border: getNumberAttribute(element, 'border') || undefined,
    width: getAttribute(element, 'width') || undefined,
  }
}

/**
 * Parse choice item (선다형 - type 11)
 */
function parseChoiceItem(root: Element, itemType: '11'): ImlChoiceItem {
  const common = parseCommonProps(root, itemType)

  // Parse choices
  const choicesEl = getChildElement(root, '답항목록') || getChildElement(root, 'choices')
  const choices: ImlChoiceAnswer[] = []

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

  // Parse correct answer from 정답 element if not marked in choices
  const correctEl = getChildElement(root, '정답')
  if (correctEl && choices.every(c => !c.isCorrect)) {
    const correctId = getTextContent(correctEl)
    const correctChoice = choices.find(c => c.id === correctId)
    if (correctChoice) {
      correctChoice.isCorrect = true
    }
  }

  return {
    ...common,
    itemType,
    choices,
    multipleAnswers: choices.filter(c => c.isCorrect).length > 1,
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
