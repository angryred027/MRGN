import { useRef, useState } from 'react'
import IconButton from '@mui/material/IconButton'
import CloseRounded from '@mui/icons-material/CloseRounded'
import PhotoCameraRounded from '@mui/icons-material/PhotoCameraRounded'
import PhotoLibraryRounded from '@mui/icons-material/PhotoLibraryRounded'
import CardShell from './CardShell'
import RoundIconButton from './RoundIconButton'
import FullScreenCamera from './FullScreenCamera'
import { useCameraStream } from './useCameraStream'
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

  const {
    videoRef,
    canSwitchFacing,
    toggleFacing,
    torchSupported,
    torchOn,
    toggleTorch,
    zoomRange,
    zoom,
    setZoom,
    focusAt,
    captureFrame,
  } = useCameraStream({
    active: !photoSrc,
    initialFacingMode,
    width: resolution?.width,
    height: resolution?.height,
    frameRate: resolution?.frameRate,
  })

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

  const handleCapture = () => {
    const src = captureFrame()
    if (src) {
      setPhotoSrc(src)
      setIsCameraOpen(false)
      onPhotoReady?.(src)
    }
  }

  const handlePreviewClick = () => {
    if (photoSrc) {
      // Discard the current photo so the live stream reactivates for retaking.
      setPhotoSrc(null)
    }
    setIsCameraOpen(true)
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
        <IconButton onClick={handleCapture} className={styles.captureButton}>
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
        className={styles.previewArea}
        onClick={handlePreviewClick}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            handlePreviewClick()
          }
        }}
        role="button"
        tabIndex={0}
      >
        {photoSrc ? (
          <img className={styles.previewMedia} src={photoSrc} alt="Captured" />
        ) : (
          // Only mount this <video> while the full-screen view isn't also mounted -
          // both share one videoRef from the same hook instance, and two elements
          // can't both hold that live at once.
          !isCameraOpen && <video ref={videoRef} autoPlay muted playsInline className={styles.previewMedia} />
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
          videoRef={videoRef}
          onClose={() => setIsCameraOpen(false)}
          onCapture={handleCapture}
          canSwitchFacing={canSwitchFacing}
          toggleFacing={toggleFacing}
          torchSupported={torchSupported}
          torchOn={torchOn}
          toggleTorch={toggleTorch}
          zoomRange={zoomRange}
          zoom={zoom}
          setZoom={setZoom}
          focusAt={focusAt}
        />
      )}
    </CardShell>
  )
}
