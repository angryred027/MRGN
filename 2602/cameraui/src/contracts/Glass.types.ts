import type { ReactNode } from 'react'

export type TGlassVariant = 'frosted' | 'clear'
export type TGlassBorder = 'solid' | 'none'

export interface TGlassContainerProps {
  children?: ReactNode
  variant?: TGlassVariant
  border?: TGlassBorder
  title?: ReactNode
  action?: ReactNode
  className?: string
  noNoise?: boolean
  stopPropagation?: boolean
  preventDefault?: boolean
}
