import type { ReactNode } from 'react'
import Paper from '@mui/material/Paper'
import clsx from 'clsx'
import styles from './CardShell.module.css'

interface CardShellProps {
  leftAction: ReactNode
  centerContent?: ReactNode
  rightAction: ReactNode
  children: ReactNode
  active?: boolean
  contentPadded?: boolean
  minHeight?: number | string
}

export default function CardShell({
  leftAction,
  centerContent,
  rightAction,
  children,
  active = true,
  contentPadded = false,
  minHeight = 420,
}: CardShellProps) {
  return (
    <Paper elevation={0} className={clsx(styles.root, active && styles.active)}>
      <div className={clsx(styles.header, contentPadded && styles.headerPadded)}>
        {leftAction}
        {centerContent}
        {rightAction}
      </div>
      <div className={clsx(styles.content, contentPadded && styles.contentPadded)} style={{ minHeight }}>
        {children}
      </div>
    </Paper>
  )
}
