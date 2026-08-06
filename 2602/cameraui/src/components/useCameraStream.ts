import { useCallback, useEffect, useRef, useState } from 'react'

type FacingMode = 'user' | 'environment'

interface ZoomRange {
  min: number
  max: number
  step: number
}

interface UseCameraStreamOptions {
  active: boolean
  initialFacingMode?: FacingMode
  width?: number
  height?: number
  frameRate?: number
}

export function useCameraStream({
  active,
  initialFacingMode = 'environment',
  width = 1920,
  height = 1080,
  frameRate = 30,
}: UseCameraStreamOptions) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const trackRef = useRef<MediaStreamTrack | null>(null)

  const [facingMode, setFacingMode] = useState<FacingMode>(initialFacingMode)
  const [canSwitchFacing, setCanSwitchFacing] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [torchOn, setTorchOn] = useState(false)
  const [zoomRange, setZoomRange] = useState<ZoomRange | null>(null)
  const [zoom, setZoomState] = useState(1)

  useEffect(() => {
    if (!active) return

    let cancelled = false
    let stream: MediaStream | undefined

    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode,
          width: { ideal: width },
          height: { ideal: height },
          frameRate: { ideal: frameRate },
        },
      })
      .then(async (mediaStream) => {
        if (cancelled) {
          mediaStream.getTracks().forEach((track) => track.stop())
          return
        }

        stream = mediaStream
        const [track] = mediaStream.getVideoTracks()
        trackRef.current = track ?? null

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream
        }

        const capabilities = track?.getCapabilities?.() ?? {}
        setTorchSupported(Boolean(capabilities.torch))
        setTorchOn(false)
        setZoomRange(capabilities.zoom ?? null)
        setZoomState(track?.getSettings?.().zoom ?? capabilities.zoom?.min ?? 1)

        const devices = await navigator.mediaDevices.enumerateDevices()
        if (!cancelled) {
          setCanSwitchFacing(devices.filter((device) => device.kind === 'videoinput').length > 1)
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
      trackRef.current = null
      stream?.getTracks().forEach((track) => track.stop())
    }
  }, [active, facingMode, width, height, frameRate])

  const toggleFacing = useCallback(() => {
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))
  }, [])

  const toggleTorch = useCallback(() => {
    const track = trackRef.current
    if (!track) return

    const next = !torchOn
    track
      .applyConstraints({ advanced: [{ torch: next }] })
      .then(() => setTorchOn(next))
      .catch(() => {})
  }, [torchOn])

  const setZoom = useCallback((value: number) => {
    const track = trackRef.current
    if (!track) return

    track
      .applyConstraints({ advanced: [{ zoom: value }] })
      .then(() => setZoomState(value))
      .catch(() => {})
  }, [])

  const focusAt = useCallback((x: number, y: number) => {
    const track = trackRef.current
    if (!track) return

    track.applyConstraints({ advanced: [{ pointsOfInterest: [{ x, y }] }] }).catch(() => {})
  }, [])

  const captureFrame = useCallback(() => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return null

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    return canvas.toDataURL('image/jpeg')
  }, [])

  return {
    videoRef,
    facingMode,
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
  }
}
