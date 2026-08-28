import { useRef, useState } from 'react'
import type { Ref } from 'react'
import { createPortal } from 'react-dom'
import IconButton from '@mui/material/IconButton'
import Slider from '@mui/material/Slider'
import CloseRounded from '@mui/icons-material/CloseRounded'
import FlashOnRounded from '@mui/icons-material/FlashOnRounded'
import FlashOffRounded from '@mui/icons-material/FlashOffRounded'
import FlipCameraIosRounded from '@mui/icons-material/FlipCameraIosRounded'
import ShutterButton from './ShutterButton'
import styles from './FullScreenCamera.module.css'

interface ZoomRange {
  min: number
  max: number
  step: number
}

interface FullScreenCameraProps {
  videoRef: Ref<HTMLVideoElement>
  onClose: () => void
  onCapture: () => void
  canSwitchFacing: boolean
  toggleFacing: () => void
  torchSupported: boolean
  torchOn: boolean
  toggleTorch: () => void
  zoomRange: ZoomRange | null
  zoom: number
  setZoom: (value: number) => void
  focusAt: (x: number, y: number) => void
}

interface FocusPoint {
  left: number
  top: number
  key: number
}

export default function FullScreenCamera({
  videoRef,
  onClose,
  onCapture,
  canSwitchFacing,
  toggleFacing,
  torchSupported,
  torchOn,
  toggleTorch,
  zoomRange,
  zoom,
  setZoom,
  focusAt,
}: FullScreenCameraProps) {
  const [focusPoint, setFocusPoint] = useState<FocusPoint | null>(null)
  const focusTimeoutRef = useRef<number | undefined>(undefined)

  const handlePreviewClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const left = event.clientX - rect.left
    const top = event.clientY - rect.top

    focusAt(left / rect.width, top / rect.height)

    window.clearTimeout(focusTimeoutRef.current)
    setFocusPoint({ left, top, key: Date.now() })
    focusTimeoutRef.current = window.setTimeout(() => setFocusPoint(null), 700)
  }

  return createPortal(
    <div className={styles.root}>
      <div className={styles.previewArea} onClick={handlePreviewClick}>
        <video ref={videoRef} className={styles.video} autoPlay muted playsInline />
        {focusPoint && (
          <span
            key={focusPoint.key}
            className={styles.focusRing}
            style={{ left: focusPoint.left, top: focusPoint.top }}
          />
        )}
      </div>

      <div className={styles.topControls}>
        <IconButton onClick={onClose} size="small" className={styles.overlayIconButton}>
          <CloseRounded fontSize="small" />
        </IconButton>
        <div className={styles.topRightControls}>
          {torchSupported && (
            <IconButton onClick={toggleTorch} size="small" className={styles.overlayIconButton}>
              {torchOn ? <FlashOnRounded fontSize="small" /> : <FlashOffRounded fontSize="small" />}
            </IconButton>
          )}
          {canSwitchFacing && (
            <IconButton onClick={toggleFacing} size="small" className={styles.overlayIconButton}>
              <FlipCameraIosRounded fontSize="small" />
            </IconButton>
          )}
        </div>
      </div>

      <div className={styles.bottomControls}>
        {zoomRange && (
          <div className={styles.zoomSliderWrap}>
            <Slider
              value={zoom}
              min={zoomRange.min}
              max={zoomRange.max}
              step={zoomRange.step}
              onChange={(_event, value) => setZoom(value as number)}
              size="small"
              className={styles.zoomSlider}
            />
          </div>
        )}
        <ShutterButton onCapture={onCapture} />
      </div>
    </div>,
    document.body,
  )
}
