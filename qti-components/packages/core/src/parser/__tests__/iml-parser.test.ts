/**
 * IML Parser Tests
 */

import { describe, it, expect } from 'vitest'
import { parseIml } from '../iml-parser'
import { imlToQti } from '../iml-to-qti'

describe('IML Parser', () => {
  describe('parseIml', () => {
    it('should parse choice item (선다형)', () => {
      const xml = `
        <문항 문항유형="11" id="choice-001">
          <문제>
            <단락>다음 중 가장 큰 수는?</단락>
          </문제>
          <답항목록>
            <답항 id="a" 정답="false">10</답항>
            <답항 id="b" 정답="true">100</답항>
            <답항 id="c" 정답="false">50</답항>
          </답항목록>
          <해설>
            <단락>100이 가장 큰 수입니다.</단락>
          </해설>
        </문항>
      `

      const item = parseIml(xml)

      expect(item.itemType).toBe('11')
      expect(item.id).toBe('choice-001')
      expect(item.question.content).toHaveLength(1)

      if (item.itemType === '11') {
        expect(item.choices).toHaveLength(3)
        expect(item.choices.find(c => c.isCorrect)?.id).toBe('b')
      }
    })

    it('should parse true/false item (진위형)', () => {
      const xml = `
        <문항 문항유형="21" id="tf-001">
          <문제>
            <단락>지구는 태양 주위를 돈다.</단락>
          </문제>
          <정답>true</정답>
        </문항>
      `

      const item = parseIml(xml)

      expect(item.itemType).toBe('21')
      if (item.itemType === '21') {
        expect(item.correctAnswer).toBe(true)
      }
    })

    it('should parse short answer item (단답형)', () => {
      const xml = `
        <문항 문항유형="31" id="sa-001">
          <문제>
            <단락>대한민국의 수도는?</단락>
          </문제>
          <정답>서울|Seoul</정답>
        </문항>
      `

      const item = parseIml(xml)

      expect(item.itemType).toBe('31')
      if (item.itemType === '31') {
        expect(item.correctAnswers).toContain('서울')
        expect(item.correctAnswers).toContain('Seoul')
      }
    })

    it('should parse matching item (배합형)', () => {
      const xml = `
        <문항 문항유형="37" id="match-001">
          <문제>
            <단락>나라와 수도를 연결하세요.</단락>
          </문제>
          <왼쪽항목>
            <항목 id="s1">한국</항목>
            <항목 id="s2">일본</항목>
          </왼쪽항목>
          <오른쪽항목>
            <항목 id="t1">서울</항목>
            <항목 id="t2">도쿄</항목>
          </오른쪽항목>
          <정답매칭>
            <매칭 왼쪽="s1" 오른쪽="t1" />
            <매칭 왼쪽="s2" 오른쪽="t2" />
          </정답매칭>
        </문항>
      `

      const item = parseIml(xml)

      expect(item.itemType).toBe('37')
      if (item.itemType === '37') {
        expect(item.sourceItems).toHaveLength(2)
        expect(item.targetItems).toHaveLength(2)
        expect(item.correctMatches).toHaveLength(2)
      }
    })

    it('should parse essay item (서술형)', () => {
      const xml = `
        <문항 문항유형="41" id="essay-001">
          <문제>
            <단락>민주주의의 장점을 서술하시오.</단락>
          </문제>
          <예시답안>
            <단락>민주주의는 국민의 의사를 반영하여...</단락>
          </예시답안>
        </문항>
      `

      const item = parseIml(xml)

      expect(item.itemType).toBe('41')
      if (item.itemType === '41') {
        expect(item.sampleAnswer).toBeDefined()
      }
    })
  })

  describe('imlToQti', () => {
    it('should convert choice item to QTI', () => {
      const xml = `
        <문항 문항유형="11" id="choice-001">
          <문제>
            <단락>2 + 2 = ?</단락>
          </문제>
          <답항목록>
            <답항 id="a" 정답="false">3</답항>
            <답항 id="b" 정답="true">4</답항>
            <답항 id="c" 정답="false">5</답항>
          </답항목록>
        </문항>
      `

      const imlItem = parseIml(xml)
      const qtiItem = imlToQti(imlItem)

      expect(qtiItem.identifier).toBe('choice-001')
      expect(qtiItem.responseDeclarations).toHaveLength(1)
      expect(qtiItem.responseDeclarations[0].correctResponse?.values).toContain('b')
      expect(qtiItem.itemBody.interactions[0].type).toBe('choiceInteraction')
    })

    it('should convert true/false item to QTI', () => {
      const xml = `
        <문항 문항유형="21" id="tf-001">
          <문제>
            <단락>1 + 1 = 2</단락>
          </문제>
          <정답>true</정답>
        </문항>
      `

      const imlItem = parseIml(xml)
      const qtiItem = imlToQti(imlItem)

      expect(qtiItem.identifier).toBe('tf-001')
      expect(qtiItem.responseDeclarations[0].correctResponse?.values).toContain('true')
    })

    it('should convert short answer item to QTI', () => {
      const xml = `
        <문항 문항유형="31" id="sa-001">
          <문제>
            <단락>5 × 5 = ?</단락>
          </문제>
          <정답>25</정답>
        </문항>
      `

      const imlItem = parseIml(xml)
      const qtiItem = imlToQti(imlItem)

      expect(qtiItem.identifier).toBe('sa-001')
      expect(qtiItem.itemBody.interactions[0].type).toBe('textEntryInteraction')
      expect(qtiItem.responseDeclarations[0].correctResponse?.values).toContain('25')
    })

    it('should convert matching item to QTI', () => {
      const xml = `
        <문항 문항유형="37" id="match-001">
          <문제>
            <단락>연결하세요</단락>
          </문제>
          <왼쪽항목>
            <항목 id="s1">A</항목>
            <항목 id="s2">B</항목>
          </왼쪽항목>
          <오른쪽항목>
            <항목 id="t1">1</항목>
            <항목 id="t2">2</항목>
          </오른쪽항목>
          <정답매칭>
            <매칭 왼쪽="s1" 오른쪽="t1" />
            <매칭 왼쪽="s2" 오른쪽="t2" />
          </정답매칭>
        </문항>
      `

      const imlItem = parseIml(xml)
      const qtiItem = imlToQti(imlItem)

      expect(qtiItem.identifier).toBe('match-001')
      expect(qtiItem.itemBody.interactions[0].type).toBe('matchInteraction')
    })

    it('should convert essay item to QTI', () => {
      const xml = `
        <문항 문항유형="41" id="essay-001">
          <문제>
            <단락>설명하시오</단락>
          </문제>
        </문항>
      `

      const imlItem = parseIml(xml)
      const qtiItem = imlToQti(imlItem)

      expect(qtiItem.identifier).toBe('essay-001')
      expect(qtiItem.itemBody.interactions[0].type).toBe('extendedTextInteraction')
    })
  })
})
