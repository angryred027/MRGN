import { useRef, useState } from 'react'
import clsx from 'clsx'
import IconButton from '@mui/material/IconButton'
import CloseRounded from '@mui/icons-material/CloseRounded'
import PhotoCameraRounded from '@mui/icons-material/PhotoCameraRounded'
import PhotoLibraryRounded from '@mui/icons-material/PhotoLibraryRounded'
import CardShell from './CardShell'
import RoundIconButton from './RoundIconButton'
import FullScreenCamera from './FullScreenCamera'
import styles from './CameraCaptureCard.module.css'

interface CameraCaptureCardProps {
  onClose?: () => void
  onPhotoReady?: (src: string) => void
  minHeight?: number | string
  maxHeight?: number | string
  initialFacingMode?: 'user' | 'environment'
  resolution?: { width?: number; height?: number; frameRate?: number }
}

export default function CameraCaptureCard({
  onClose,
  onPhotoReady,
  minHeight = 240,
  maxHeight = 240,
  initialFacingMode = 'environment',
  resolution,
}: CameraCaptureCardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [photoSrc, setPhotoSrc] = useState<string | null>(null)
  const [isCameraOpen, setIsCameraOpen] = useState(false)

  const handlePickFromLibrary = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    const objectUrl = URL.createObjectURL(file)
    setPhotoSrc(objectUrl)
    onPhotoReady?.(objectUrl)
  }

  const handleCloseClick = () => {
    if (photoSrc) {
      setPhotoSrc(null)
    } else {
      onClose?.()
    }
  }

  const handleCaptured = (src: string) => {
    setPhotoSrc(src)
    setIsCameraOpen(false)
    onPhotoReady?.(src)
  }

  return (
    <CardShell
      minHeight={minHeight}
      maxHeight={maxHeight}
      contentPadded
      leftAction={
        <RoundIconButton onClick={handleCloseClick} size="small">
          <CloseRounded fontSize="small" />
        </RoundIconButton>
      }
      centerContent={
        <IconButton onClick={() => setIsCameraOpen(true)} className={styles.captureButton}>
          <PhotoCameraRounded fontSize="medium" />
        </IconButton>
      }
      rightAction={
        <RoundIconButton onClick={handlePickFromLibrary} size="small">
          <PhotoLibraryRounded fontSize="small" />
        </RoundIconButton>
      }
    >
      <div
        className={clsx(styles.previewArea, !photoSrc && styles.previewAreaTappable)}
        onClick={!photoSrc ? () => setIsCameraOpen(true) : undefined}
        onKeyDown={
          !photoSrc
            ? (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setIsCameraOpen(true)
                }
              }
            : undefined
        }
        role={!photoSrc ? 'button' : undefined}
        tabIndex={!photoSrc ? 0 : undefined}
      >
        {photoSrc ? (
          <img className={styles.previewMedia} src={photoSrc} alt="Captured" />
        ) : (
          <span className={styles.placeholder}>Tap to take a photo</span>
        )}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className={styles.hiddenInput}
      />
      {isCameraOpen && (
        <FullScreenCamera
          initialFacingMode={initialFacingMode}
          resolution={resolution}
          onClose={() => setIsCameraOpen(false)}
          onCapture={handleCaptured}
        />
      )}
    </CardShell>
  )
}
