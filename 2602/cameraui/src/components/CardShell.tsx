import type { ReactNode } from 'react'
import clsx from 'clsx'
import { GlassContainer } from './GlassContainer'
import styles from './CardShell.module.css'

interface CardShellProps {
  leftAction: ReactNode
  centerContent?: ReactNode
  rightAction: ReactNode
  children: ReactNode
  active?: boolean
  contentPadded?: boolean
  minHeight?: number | string
  maxHeight?: number | string
}

export default function CardShell({
  leftAction,
  centerContent,
  rightAction,
  children,
  active = true,
  contentPadded = false,
  minHeight = 420,
  maxHeight,
}: CardShellProps) {
  return (
    <GlassContainer
      className={clsx(styles.root, active && styles.active)}
      title={
        <div className={clsx(styles.header, contentPadded && styles.headerPadded)}>
          {leftAction}
          {centerContent}
          {rightAction}
        </div>
      }
    >
      <div className={clsx(styles.content, contentPadded && styles.contentPadded)} style={{ minHeight, maxHeight }}>
        {children}
      </div>
    </GlassContainer>
  )
}
