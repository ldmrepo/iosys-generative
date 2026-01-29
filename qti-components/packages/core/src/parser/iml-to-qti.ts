/**
 * IML to QTI Converter
 * Converts ImlItem objects to QTI AssessmentItem format
 */

export interface ImlToQtiOptions {
  /** Base URL for image paths (e.g., '/api/search/images/') */
  imageBaseUrl?: string
}

// Module-level options that can be set before conversion
let globalOptions: ImlToQtiOptions = {}

export function setImlToQtiOptions(options: ImlToQtiOptions) {
  globalOptions = { ...globalOptions, ...options }
}

import type {
  ImlItem,
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
  ImlExampleBox,
} from '../types/iml'

import type {
  AssessmentItem,
  ResponseDeclaration,
  OutcomeDeclaration,
  ItemBody,
  Interaction,
  ChoiceInteraction,
  TextEntryInteraction,
  ExtendedTextInteraction,
  MatchInteraction,
  GapMatchInteraction,
  SimpleChoice,
  SimpleAssociableChoice,
  FeedbackBlock,
} from '../types/qti'

// Note: generateId is available from './xml-utils' if needed

/**
 * Convert IML item to QTI AssessmentItem
 */
export function imlToQti(item: ImlItem): AssessmentItem {
  switch (item.itemType) {
    case '11':
      return convertChoiceItem(item)
    case '21':
      return convertTrueFalseItem(item)
    case '31':
      return convertShortAnswerItem(item)
    case '34':
      return convertFillBlankItem(item)
    case '37':
      return convertMatchingItem(item)
    case '41':
    case '51':
      return convertEssayItem(item)
    default:
      throw new Error(`Unsupported item type: ${(item as ImlItem).itemType}`)
  }
}

/**
 * Convert block content to HTML string
 */
function blockContentToHtml(content: ImlBlockContent[]): string {
  return content.map(block => {
    switch (block.type) {
      case 'paragraph':
        return paragraphToHtml(block)
      case 'image':
        return imageToHtml(block)
      case 'math':
        return mathToHtml(block)
      case 'table':
        return tableToHtml(block)
      case 'exampleBox':
        return exampleBoxToHtml(block)
      default:
        return ''
    }
  }).join('\n')
}

function paragraphToHtml(p: ImlParagraph): string {
  // Note: Ignoring p.align - all content should be left-aligned by default
  const content = p.content.map(c => {
    if (typeof c === 'string') {
      return c
    } else if (c.type === 'math') {
      return mathToHtml(c)
    } else if (c.type === 'image') {
      return imageToHtml(c)
    } else if (c.type === 'blank') {
      // 완성형 문항의 빈칸 렌더링
      const width = c.size ? `${c.size * 10}px` : '80px'
      return `<span class="qti-blank" data-blank-id="${c.id}" style="display: inline-block; min-width: ${width}; border-bottom: 1px solid currentColor; margin: 0 2px;">&nbsp;</span>`
    }
    return ''
  }).join('')
  return `<p>${content}</p>`
}

function imageToHtml(img: ImlImage): string {
  // Resolve image src with optional base URL
  let src = img.src || ''

  // Convert Windows backslashes to forward slashes
  src = src.replace(/\\/g, '/')

  // Trim whitespace and newlines from path
  src = src.trim()

  if (src && globalOptions.imageBaseUrl) {
    // Don't modify absolute URLs or data URLs
    if (!src.startsWith('http://') && !src.startsWith('https://') && !src.startsWith('data:')) {
      // Remove leading slash if present to avoid double slashes
      const cleanSrc = src.startsWith('/') ? src.slice(1) : src
      const baseUrl = globalOptions.imageBaseUrl.endsWith('/')
        ? globalOptions.imageBaseUrl
        : globalOptions.imageBaseUrl + '/'
      src = baseUrl + cleanSrc
    }
  }

  const attrs = [`src="${src}"`]
  if (img.alt) attrs.push(`alt="${img.alt}"`)
  if (img.width) attrs.push(`width="${img.width}"`)
  if (img.height) attrs.push(`height="${img.height}"`)

  // Add style for responsive display and alignment
  const styles = ['max-width: 100%', 'height: auto']

  // Handle alignment (already normalized to left/center/right in parser)
  if (img.align === 'center') {
    styles.push('display: block', 'margin: 0 auto')
  } else if (img.align === 'right') {
    styles.push('display: block', 'margin-left: auto')
  }

  attrs.push(`style="${styles.join('; ')}"`)

  return `<img ${attrs.join(' ')} />`
}

function mathToHtml(math: ImlMath): string {
  const displayClass = math.display === 'block' ? 'math-block' : 'math-inline'
  const normalizedLatex = normalizeImlLatex(math.latex || '')
  // Escape quotes for HTML attribute
  const escapedLatex = normalizedLatex.replace(/"/g, '&quot;')
  return `<span class="math ${displayClass}" data-latex="${escapedLatex}"></span>`
}

/**
 * Normalize IML LaTeX format for KaTeX compatibility
 * - Remove excessive whitespace
 * - Fix brace patterns
 * - Handle Korean text in math
 */
function normalizeImlLatex(latex: string): string {
  if (!latex) return ''

  let result = latex

  // Remove outer braces if the whole expression is wrapped: { { ... } } -> ...
  result = result.trim()
  while (result.startsWith('{ ') && result.endsWith(' }')) {
    const inner = result.slice(2, -2).trim()
    // Check if braces are balanced
    if (areBracesBalanced(inner)) {
      result = inner
    } else {
      break
    }
  }

  // Normalize whitespace around braces and operators
  result = result
    // Fix spacing around braces: { { -> {{, } } -> }}
    .replace(/\{\s+\{/g, '{{')
    .replace(/\}\s+\}/g, '}}')
    // Fix spacing inside braces: { x } -> {x}
    .replace(/\{\s+/g, '{')
    .replace(/\s+\}/g, '}')
    // Fix multiple spaces -> single space
    .replace(/\s{2,}/g, ' ')
    // Fix spacing around operators
    .replace(/\s*\^\s*/g, '^')
    .replace(/\s*_\s*/g, '_')

  // Handle Korean text - wrap in \text{} if not already
  // Match Korean characters that are not inside \text{}
  result = result.replace(
    /([가-힣]+)/g,
    (match) => `\\text{${match}}`
  )

  return result.trim()
}

function areBracesBalanced(str: string): boolean {
  let count = 0
  for (const char of str) {
    if (char === '{') count++
    else if (char === '}') count--
    if (count < 0) return false
  }
  return count === 0
}

function exampleBoxToHtml(box: ImlExampleBox): string {
  const title = box.title || '보기'
  const innerContent = blockContentToHtml(box.content)

  // Build inline styles
  const boxStyles: string[] = []
  if (box.border === false) {
    boxStyles.push('border: none')
  }
  if (box.backgroundColor) {
    boxStyles.push(`background-color: ${box.backgroundColor}`)
  }
  const boxStyleAttr = boxStyles.length > 0 ? ` style="${boxStyles.join('; ')}"` : ''

  // Title alignment
  const titleStyles: string[] = []
  if (box.titleAlign === 'center') {
    titleStyles.push('text-align: center')
  } else if (box.titleAlign === 'right') {
    titleStyles.push('text-align: right')
  }
  const titleStyleAttr = titleStyles.length > 0 ? ` style="${titleStyles.join('; ')}"` : ''

  return `<div class="example-box"${boxStyleAttr}><div class="example-box-title"${titleStyleAttr}>${title}</div><div class="example-box-content">${innerContent}</div></div>`
}

function tableToHtml(table: ImlTable): string {
  const rows = table.rows.map(row => {
    const cells = row.cells.map(cell => {
      const tag = cell.type
      const attrs: string[] = []
      if (cell.colspan) attrs.push(`colspan="${cell.colspan}"`)
      if (cell.rowspan) attrs.push(`rowspan="${cell.rowspan}"`)

      // Build cell styles
      const styles: string[] = []
      if (cell.w) styles.push(`width: ${cell.w}%`)
      if (cell.h) styles.push(`height: ${cell.h}%`)
      if (cell.valign) {
        const valignMap = { top: 'top', middle: 'middle', bottom: 'bottom' }
        styles.push(`vertical-align: ${valignMap[cell.valign]}`)
      }
      if (cell.backgroundColor) {
        styles.push(`background-color: ${cell.backgroundColor}`)
      }
      if (cell.borderInfo) {
        const [left, top, right, bottom] = cell.borderInfo
        const borderStyle = (val: number) => val === 0 ? 'none' : val === 2 ? 'dotted' : 'solid'
        styles.push(`border-left-style: ${borderStyle(left)}`)
        styles.push(`border-top-style: ${borderStyle(top)}`)
        styles.push(`border-right-style: ${borderStyle(right)}`)
        styles.push(`border-bottom-style: ${borderStyle(bottom)}`)
      }

      if (styles.length > 0) {
        attrs.push(`style="${styles.join('; ')}"`)
      }

      const content = blockContentToHtml(cell.content)
      return `<${tag}${attrs.length ? ' ' + attrs.join(' ') : ''}>${content}</${tag}>`
    }).join('')
    return `<tr>${cells}</tr>`
  }).join('\n')

  const tableAttrs: string[] = ['class="iml-table"']
  if (table.border !== undefined) tableAttrs.push(`border="${table.border}"`)
  if (table.width) tableAttrs.push(`width="${table.width}"`)

  // Add colgroup for column widths
  let colgroup = ''
  if (table.colWidths && table.colWidths.length > 0) {
    const cols = table.colWidths.map(w => `<col style="width: ${w}%">`).join('')
    colgroup = `<colgroup>${cols}</colgroup>\n`
  }

  return `<table ${tableAttrs.join(' ')}>\n${colgroup}${rows}\n</table>`
}

/**
 * Create base assessment item structure
 */
function createBaseItem(item: ImlItem, interactions: Interaction[]): AssessmentItem {
  const responseDeclarations: ResponseDeclaration[] = []
  const outcomeDeclarations: OutcomeDeclaration[] = [
    {
      identifier: 'SCORE',
      cardinality: 'single',
      baseType: 'float',
      defaultValue: 0,
    },
  ]

  // Create response declarations for each interaction
  for (const interaction of interactions) {
    const responseDecl = createResponseDeclaration(interaction, item)
    if (responseDecl) {
      responseDeclarations.push(responseDecl)
    }
  }

  // Create feedback blocks
  const feedbackBlocks: FeedbackBlock[] = []
  if (item.explanation) {
    feedbackBlocks.push({
      outcomeIdentifier: 'SCORE',
      identifier: 'explanation',
      showHide: 'show',
      content: blockContentToHtml(item.explanation.content),
    })
  }

  const itemBody: ItemBody = {
    content: blockContentToHtml(item.question.content),
    interactions,
    feedbackBlocks: feedbackBlocks.length > 0 ? feedbackBlocks : undefined,
  }

  return {
    identifier: item.id,
    title: '',
    responseDeclarations,
    outcomeDeclarations,
    itemBody,
  }
}

/**
 * Create response declaration based on interaction type
 */
function createResponseDeclaration(
  interaction: Interaction,
  item: ImlItem
): ResponseDeclaration | null {
  switch (interaction.type) {
    case 'choiceInteraction': {
      const choiceItem = item as ImlChoiceItem | ImlTrueFalseItem
      const correctChoices = 'choices' in choiceItem
        ? choiceItem.choices.filter(c => c.isCorrect).map(c => c.id)
        : [choiceItem.correctAnswer ? 'true' : 'false']

      return {
        identifier: interaction.responseIdentifier,
        cardinality: correctChoices.length > 1 ? 'multiple' : 'single',
        baseType: 'identifier',
        correctResponse: {
          values: correctChoices,
        },
      }
    }

    case 'textEntryInteraction': {
      const textItem = item as ImlShortAnswerItem
      return {
        identifier: interaction.responseIdentifier,
        cardinality: 'single',
        baseType: 'string',
        correctResponse: {
          values: textItem.correctAnswers,
        },
      }
    }

    case 'extendedTextInteraction': {
      return {
        identifier: interaction.responseIdentifier,
        cardinality: 'single',
        baseType: 'string',
      }
    }

    case 'matchInteraction': {
      const matchItem = item as ImlMatchingItem
      return {
        identifier: interaction.responseIdentifier,
        cardinality: 'multiple',
        baseType: 'directedPair',
        correctResponse: {
          values: matchItem.correctMatches.map(m => `${m.sourceId} ${m.targetId}`),
        },
      }
    }

    case 'gapMatchInteraction': {
      const fillItem = item as ImlFillBlankItem
      return {
        identifier: interaction.responseIdentifier,
        cardinality: 'multiple',
        baseType: 'directedPair',
        correctResponse: {
          values: fillItem.blanks.map(b => `${b.correctAnswers[0]} ${b.id}`),
        },
      }
    }

    default:
      return null
  }
}

/**
 * Convert choice item (선다형)
 */
function convertChoiceItem(item: ImlChoiceItem): AssessmentItem {
  const simpleChoices: SimpleChoice[] = item.choices.map(choice => ({
    identifier: choice.id,
    content: blockContentToHtml(choice.content),
  }))

  const interaction: ChoiceInteraction = {
    type: 'choiceInteraction',
    responseIdentifier: 'RESPONSE',
    maxChoices: item.multipleAnswers ? 0 : 1,
    shuffle: item.shuffle,
    simpleChoices,
    // Pass columns info for grid layout (1=vertical, 2+=grid)
    columns: item.choiceColumns,
  }

  return createBaseItem(item, [interaction])
}

/**
 * Convert true/false item (진위형)
 */
function convertTrueFalseItem(item: ImlTrueFalseItem): AssessmentItem {
  const simpleChoices: SimpleChoice[] = [
    { identifier: 'true', content: '참 (O)' },
    { identifier: 'false', content: '거짓 (X)' },
  ]

  const interaction: ChoiceInteraction = {
    type: 'choiceInteraction',
    responseIdentifier: 'RESPONSE',
    maxChoices: 1,
    shuffle: false,
    simpleChoices,
  }

  return createBaseItem(item, [interaction])
}

/**
 * Convert short answer item (단답형)
 */
function convertShortAnswerItem(item: ImlShortAnswerItem): AssessmentItem {
  const interaction: TextEntryInteraction = {
    type: 'textEntryInteraction',
    responseIdentifier: 'RESPONSE',
    expectedLength: item.maxLength,
  }

  return createBaseItem(item, [interaction])
}

/**
 * Convert fill-in-the-blank item (완성형)
 */
function convertFillBlankItem(item: ImlFillBlankItem): AssessmentItem {
  const interaction: GapMatchInteraction = {
    type: 'gapMatchInteraction',
    responseIdentifier: 'RESPONSE',
    gapChoices: item.blanks.flatMap(blank =>
      blank.correctAnswers.map(answer => ({
        identifier: answer,
        matchMax: 1,
        content: answer,
      }))
    ),
    gaps: item.blanks.map(blank => ({
      identifier: blank.id,
    })),
  }

  return createBaseItem(item, [interaction])
}

/**
 * Convert matching item (배합형)
 */
function convertMatchingItem(item: ImlMatchingItem): AssessmentItem {
  const sourceSet: SimpleAssociableChoice[] = item.sourceItems.map(src => ({
    identifier: src.id,
    matchMax: 1,
    content: blockContentToHtml(src.content),
  }))

  const targetSet: SimpleAssociableChoice[] = item.targetItems.map(tgt => ({
    identifier: tgt.id,
    matchMax: item.sourceItems.length, // Can be matched multiple times
    content: blockContentToHtml(tgt.content),
  }))

  const interaction: MatchInteraction = {
    type: 'matchInteraction',
    responseIdentifier: 'RESPONSE',
    shuffle: false,
    simpleMatchSets: [
      { simpleAssociableChoices: sourceSet },
      { simpleAssociableChoices: targetSet },
    ],
  }

  return createBaseItem(item, [interaction])
}

/**
 * Convert essay item (서술형/논술형)
 */
function convertEssayItem(item: ImlEssayShortItem | ImlEssayLongItem): AssessmentItem {
  const interaction: ExtendedTextInteraction = {
    type: 'extendedTextInteraction',
    responseIdentifier: 'RESPONSE',
    expectedLines: item.itemType === '41' ? 5 : 15,
    format: 'plain',
  }

  const assessmentItem = createBaseItem(item, [interaction])

  // Add sample answer as feedback
  if (item.sampleAnswer) {
    const sampleFeedback: FeedbackBlock = {
      outcomeIdentifier: 'SCORE',
      identifier: 'sampleAnswer',
      showHide: 'show',
      content: `<div class="sample-answer"><strong>예시 답안:</strong>${blockContentToHtml(item.sampleAnswer)}</div>`,
    }

    assessmentItem.itemBody.feedbackBlocks = [
      ...(assessmentItem.itemBody.feedbackBlocks ?? []),
      sampleFeedback,
    ]
  }

  return assessmentItem
}
