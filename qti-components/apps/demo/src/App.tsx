import { useState } from 'react'
import type { AssessmentItem } from '@iosys/qti-core'
import { QtiViewer } from '@iosys/qti-viewer'
import { QtiAssessment } from '@iosys/qti-assessment'
import { QtiEditor } from '@iosys/qti-editor'
import './index.css'

// Sample QTI Assessment Item
const sampleItem: AssessmentItem = {
  identifier: 'ITEM_001',
  title: '삼각형의 넓이',
  responseDeclarations: [
    {
      identifier: 'RESPONSE',
      cardinality: 'single',
      baseType: 'identifier',
      correctResponse: {
        values: ['B'],
      },
    },
  ],
  outcomeDeclarations: [
    {
      identifier: 'SCORE',
      cardinality: 'single',
      baseType: 'float',
      defaultValue: 0,
    },
  ],
  itemBody: {
    content: `
      <p>밑변의 길이가 6cm이고, 높이가 4cm인 삼각형의 넓이를 구하시오.</p>
    `,
    interactions: [
      {
        type: 'choiceInteraction',
        responseIdentifier: 'RESPONSE',
        maxChoices: 1,
        shuffle: false,
        simpleChoices: [
          { identifier: 'A', content: '10 cm²' },
          { identifier: 'B', content: '12 cm²' },
          { identifier: 'C', content: '24 cm²' },
          { identifier: 'D', content: '20 cm²' },
        ],
      },
    ],
    feedbackBlocks: [
      {
        outcomeIdentifier: 'SCORE',
        identifier: 'correct',
        showHide: 'show',
        content: '정답입니다! 삼각형의 넓이 = (밑변 × 높이) / 2 = (6 × 4) / 2 = 12 cm²',
      },
      {
        outcomeIdentifier: 'SCORE',
        identifier: 'incorrect',
        showHide: 'show',
        content: '오답입니다. 삼각형의 넓이 공식은 (밑변 × 높이) / 2 입니다.',
      },
    ],
  },
}

type TabType = 'viewer' | 'assessment' | 'editor'

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('assessment')
  const [editorContent, setEditorContent] = useState('<p>문항 내용을 입력하세요...</p>')

  const tabs: { id: TabType; label: string }[] = [
    { id: 'viewer', label: 'Viewer (뷰어)' },
    { id: 'assessment', label: 'Assessment (응시)' },
    { id: 'editor', label: 'Editor (편집)' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            QTI Components Demo
          </h1>
          <p className="text-gray-600 mt-1">
            QTI 3.0 기반 문항 컴포넌트 라이브러리
          </p>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-4">
          <nav className="flex gap-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-3 text-sm font-medium border-b-2 transition-colors
                  ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          {/* Viewer Mode */}
          {activeTab === 'viewer' && (
            <div>
              <div className="mb-4 text-sm text-gray-500">
                뷰어 모드: 문항을 읽기 전용으로 표시하고, 정답과 해설을 확인할 수 있습니다.
              </div>
              <QtiViewer
                item={sampleItem}
                showAnswer={true}
                showExplanation={true}
              />
            </div>
          )}

          {/* Assessment Mode */}
          {activeTab === 'assessment' && (
            <div>
              <div className="mb-4 text-sm text-gray-500">
                응시 모드: 문항에 답변하고 채점 결과를 확인할 수 있습니다.
              </div>
              <QtiAssessment
                item={sampleItem}
                mode="practice"
                onSubmit={result => {
                  console.log('Scoring result:', result)
                }}
              />
            </div>
          )}

          {/* Editor Mode */}
          {activeTab === 'editor' && (
            <div>
              <div className="mb-4 text-sm text-gray-500">
                편집 모드: ProseMirror 기반 WYSIWYG 에디터로 문항을 편집합니다.
              </div>
              <QtiEditor
                value={editorContent}
                onChange={setEditorContent}
                placeholder="문항 내용을 입력하세요..."
              />
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <div className="text-sm font-medium text-gray-700 mb-2">HTML 출력:</div>
                <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                  {editorContent}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Package Info */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium text-gray-900">@iosys/qti-core</h3>
            <p className="text-sm text-gray-500 mt-1">
              QTI/IML 타입 정의 및 유틸리티
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium text-gray-900">@iosys/qti-viewer</h3>
            <p className="text-sm text-gray-500 mt-1">
              읽기 전용 뷰어 컴포넌트
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium text-gray-900">@iosys/qti-assessment</h3>
            <p className="text-sm text-gray-500 mt-1">
              응시 모드 및 채점 엔진
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium text-gray-900">@iosys/qti-editor</h3>
            <p className="text-sm text-gray-500 mt-1">
              ProseMirror 기반 WYSIWYG 편집기
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium text-gray-900">@iosys/qti-ui</h3>
            <p className="text-sm text-gray-500 mt-1">
              공통 UI 컴포넌트
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
