/**
 * IML to QTI Converter
 * Converts ImlItem objects to QTI AssessmentItem format
 */

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
      default:
        return ''
    }
  }).join('\n')
}

function paragraphToHtml(p: ImlParagraph): string {
  const style = p.align ? ` style="text-align: ${p.align}"` : ''
  const content = p.content.map(c => (typeof c === 'string' ? c : '')).join('')
  return `<p${style}>${content}</p>`
}

function imageToHtml(img: ImlImage): string {
  const attrs = [`src="${img.src}"`]
  if (img.alt) attrs.push(`alt="${img.alt}"`)
  if (img.width) attrs.push(`width="${img.width}"`)
  if (img.height) attrs.push(`height="${img.height}"`)
  return `<img ${attrs.join(' ')} />`
}

function mathToHtml(math: ImlMath): string {
  const displayClass = math.display === 'block' ? 'math-block' : 'math-inline'
  return `<span class="math ${displayClass}" data-latex="${math.latex}"></span>`
}

function tableToHtml(table: ImlTable): string {
  const rows = table.rows.map(row => {
    const cells = row.cells.map(cell => {
      const tag = cell.type
      const attrs: string[] = []
      if (cell.colspan) attrs.push(`colspan="${cell.colspan}"`)
      if (cell.rowspan) attrs.push(`rowspan="${cell.rowspan}"`)
      const content = blockContentToHtml(cell.content)
      return `<${tag}${attrs.length ? ' ' + attrs.join(' ') : ''}>${content}</${tag}>`
    }).join('')
    return `<tr>${cells}</tr>`
  }).join('\n')

  const tableAttrs: string[] = []
  if (table.border) tableAttrs.push(`border="${table.border}"`)
  if (table.width) tableAttrs.push(`width="${table.width}"`)

  return `<table${tableAttrs.length ? ' ' + tableAttrs.join(' ') : ''}>\n${rows}\n</table>`
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
    title: `Item ${item.id}`,
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
