import { useState } from 'react'
import clsx from 'clsx'
import styles from './ShutterButton.module.css'

interface ShutterButtonProps {
  onCapture: () => void
}

export default function ShutterButton({ onCapture }: ShutterButtonProps) {
  const [pressed, setPressed] = useState(false)

  return (
    <button
      type="button"
      aria-label="Take photo"
      className={clsx(styles.root, pressed && styles.pressed)}
      onPointerDown={() => setPressed(true)}
      onPointerUp={() => setPressed(false)}
      onPointerLeave={() => setPressed(false)}
      onPointerCancel={() => setPressed(false)}
      onClick={onCapture}
    />
  )
}
