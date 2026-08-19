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
  const streamRef = useRef<MediaStream | null>(null)
  const devicesRef = useRef<MediaDeviceInfo[]>([])

  const [facingMode, setFacingMode] = useState<FacingMode>(initialFacingMode)
  const [deviceId, setDeviceId] = useState<string | null>(null)
  const [canSwitchFacing, setCanSwitchFacing] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [torchOn, setTorchOn] = useState(false)
  const [zoomRange, setZoomRange] = useState<ZoomRange | null>(null)
  const [zoom, setZoomState] = useState(1)

  useEffect(() => {
    if (!active) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      trackRef.current = null
      return
    }

    let cancelled = false
    // Keep the outgoing stream alive until the incoming one is attached, so the
    // <video> element always has live frames to show instead of going black
    // while the new device negotiates.
    const previousStream = streamRef.current

    const videoConstraints: MediaTrackConstraints = deviceId
      ? {
          deviceId: { exact: deviceId },
          width: { ideal: width },
          height: { ideal: height },
          frameRate: { ideal: frameRate },
        }
      : {
          facingMode,
          width: { ideal: width },
          height: { ideal: height },
          frameRate: { ideal: frameRate },
        }

    navigator.mediaDevices
      .getUserMedia({ video: videoConstraints })
      .then(async (mediaStream) => {
        if (cancelled) {
          mediaStream.getTracks().forEach((track) => track.stop())
          return
        }

        streamRef.current = mediaStream
        const [track] = mediaStream.getVideoTracks()
        trackRef.current = track ?? null

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream
        }

        // Only release the old device now that the new stream is live on screen.
        previousStream?.getTracks().forEach((track) => track.stop())

        const capabilities = track?.getCapabilities?.() ?? {}
        setTorchSupported(Boolean(capabilities.torch))
        setTorchOn(false)
        setZoomRange(capabilities.zoom ?? null)
        setZoomState(track?.getSettings?.().zoom ?? capabilities.zoom?.min ?? 1)

        const devices = await navigator.mediaDevices.enumerateDevices()
        if (!cancelled) {
          const videoInputs = devices.filter((device) => device.kind === 'videoinput')
          devicesRef.current = videoInputs
          setCanSwitchFacing(videoInputs.length > 1)
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [active, facingMode, deviceId, width, height, frameRate])

  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((track) => track.stop())
    },
    [],
  )

  const toggleFacing = useCallback(() => {
    const devices = devicesRef.current
    if (devices.length > 1) {
      const currentId = trackRef.current?.getSettings?.().deviceId ?? deviceId
      const currentIndex = devices.findIndex((device) => device.deviceId === currentId)
      const next = devices[(currentIndex + 1) % devices.length]
      if (next) setDeviceId(next.deviceId)
      return
    }
    setDeviceId(null)
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))
  }, [deviceId])

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
