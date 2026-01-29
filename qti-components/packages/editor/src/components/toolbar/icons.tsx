/**
 * Toolbar Icons - SVG icons for editor toolbar
 */

interface IconProps {
  className?: string | undefined
}

const iconClass = 'w-4 h-4'

export function BoldIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 4h8a4 4 0 014 4 4 4 0 01-4 4H6z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 12h9a4 4 0 014 4 4 4 0 01-4 4H6z" />
    </svg>
  )
}

export function ItalicIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 4h4m0 0l-4 16m4-16h4M6 20h4" />
    </svg>
  )
}

export function UnderlineIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v7a5 5 0 0010 0V4" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 20h14" />
    </svg>
  )
}

export function StrikeIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.5 7.5A5 5 0 007 8v1a5 5 0 005 5h2" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6.5 16.5A5 5 0 0017 16v-1a5 5 0 00-5-5h-2" />
    </svg>
  )
}

export function SuperscriptIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M5 19l6-6m-6 0l6 6m5-17h3a1 1 0 011 1v1a1 1 0 01-1 1h-2v2h3v1h-4V3z" />
    </svg>
  )
}

export function SubscriptIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M5 8l6 6m-6 0l6-6m5 10h3a1 1 0 001-1v-1a1 1 0 00-1-1h-2v-2h3v-1h-4v6z" />
    </svg>
  )
}

export function CodeIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  )
}

export function LinkIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  )
}

export function ImageIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

export function MathIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <text x="4" y="17" fontSize="14" fontFamily="serif" fontStyle="italic">f</text>
      <text x="10" y="17" fontSize="10" fontFamily="serif">(x)</text>
    </svg>
  )
}

export function HeadingIcon({ className = iconClass, level }: IconProps & { level: number }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <text x="2" y="17" fontSize="14" fontFamily="sans-serif" fontWeight="bold">H</text>
      <text x="14" y="19" fontSize="10" fontFamily="sans-serif">{level}</text>
    </svg>
  )
}

export function ParagraphIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
    </svg>
  )
}

export function UndoIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
    </svg>
  )
}

export function RedoIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10H11a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6" />
    </svg>
  )
}

export function ChoiceIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="7" cy="8" r="3" strokeWidth={2} />
      <circle cx="7" cy="16" r="3" strokeWidth={2} />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8h8M12 16h8" />
    </svg>
  )
}

export function TextEntryIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="3" y="6" width="18" height="12" rx="2" strokeWidth={2} />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 10v4" />
    </svg>
  )
}

export function ExtendedTextIcon({ className = iconClass }: IconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="3" y="3" width="18" height="18" rx="2" strokeWidth={2} />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h10M7 11h10M7 15h6" />
    </svg>
  )
}
