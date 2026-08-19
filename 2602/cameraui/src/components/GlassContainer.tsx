import type { MouseEvent } from 'react'
import clsx from 'clsx'
import type { TGlassContainerProps } from '../contracts/Glass.types'
import css from './GlassContainer.module.css'

export function GlassContainer({
  children,
  variant = 'frosted',
  border = 'solid',
  title,
  action,
  className,
  noNoise,
  stopPropagation = false,
  preventDefault = false,
}: TGlassContainerProps) {
  const handleClick = (e: MouseEvent<HTMLDivElement>) => {
    if (stopPropagation) e.stopPropagation()
    if (preventDefault) e.preventDefault()
  }

  return (
    <div
      className={clsx('glassContainer', css.glassContainer, css[variant], css[border], noNoise && css.noNoise, className)}
      onClick={handleClick}
    >
      <div className={css.filter} />
      <div className={css.overlay} />
      <div className={css.specular} />
      <section>
        {title && <header>{title}</header>}
        <main>{children}</main>
        {action && <footer>{action}</footer>}
      </section>
    </div>
  )
}
