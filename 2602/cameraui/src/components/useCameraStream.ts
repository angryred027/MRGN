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
  const videoElRef = useRef<HTMLVideoElement | null>(null)
  const trackRef = useRef<MediaStreamTrack | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const devicesRef = useRef<MediaDeviceInfo[]>([])
  const activeDeviceIndexRef = useRef(0)

  const [facingMode, setFacingMode] = useState<FacingMode>(initialFacingMode)
  const [deviceId, setDeviceId] = useState<string | null>(null)
  const [canSwitchFacing, setCanSwitchFacing] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [torchOn, setTorchOn] = useState(false)
  const [zoomRange, setZoomRange] = useState<ZoomRange | null>(null)
  const [zoom, setZoomState] = useState(1)

  // A plain useRef object doesn't work here: the compact card preview and the
  // full-screen view each mount their own <video> element at different times,
  // sharing this same hook instance. A callback ref re-attaches the live
  // stream to whichever <video> element is currently mounted, instead of only
  // attaching once at the moment the stream was first requested.
  const videoRef = useCallback((node: HTMLVideoElement | null) => {
    videoElRef.current = node
    if (node && streamRef.current) {
      node.srcObject = null
      node.srcObject = streamRef.current
      node.play?.().catch((error) => console.error('[camera] play() failed', error))
    }
  }, [])

  useEffect(() => {
    if (!active) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      trackRef.current = null
      return
    }

    let cancelled = false
    // Most camera hardware only allows one open handle at a time, so the old
    // device must be released before the new one can be opened - otherwise
    // getUserMedia rejects (NotReadableError) and the switch silently no-ops.
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    trackRef.current = null

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
        console.log('[camera] new track', track?.label, track?.getSettings?.())

        if (videoElRef.current) {
          const video = videoElRef.current
          // Some browsers keep painting the last frame of the outgoing stream
          // when srcObject is swapped while the element is mid-playback. Force
          // a clean reset before attaching the new stream.
          video.srcObject = null
          video.srcObject = mediaStream
          video.play?.().catch((error) => console.error('[camera] play() failed', error))
        }

        const capabilities = track?.getCapabilities?.() ?? {}
        setTorchSupported(Boolean(capabilities.torch))
        setTorchOn(false)
        setZoomRange(capabilities.zoom ?? null)
        setZoomState(track?.getSettings?.().zoom ?? capabilities.zoom?.min ?? 1)

        const devices = await navigator.mediaDevices.enumerateDevices()
        if (!cancelled) {
          const videoInputs = devices.filter((device) => device.kind === 'videoinput')
          devicesRef.current = videoInputs

          // Best-effort sync to the device actually granted. getSettings().deviceId
          // isn't reliably reported on every browser (notably iOS Safari), so this
          // is advisory only - toggleFacing never depends on it matching.
          const settingsDeviceId = track?.getSettings?.().deviceId
          const matchedIndex = videoInputs.findIndex((device) => device.deviceId === settingsDeviceId)
          if (matchedIndex !== -1) activeDeviceIndexRef.current = matchedIndex

          setCanSwitchFacing(videoInputs.length > 1)
        }
      })
      .catch((error) => {
        if (!cancelled) console.error('Failed to start camera stream', error)
      })

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
      // Advance our own pointer instead of re-deriving "current device" from
      // track.getSettings().deviceId: when that lookup can't find a match in
      // devicesRef (unsupported/unreliable on some browsers, e.g. iOS Safari),
      // findIndex returns -1, and (-1 + 1) % length is 0 - which silently
      // re-requests devices[0] every time. If devices[0] is the device already
      // streaming, that looks like a real "next device id" in logs but never
      // actually changes what's on screen.
      activeDeviceIndexRef.current = (activeDeviceIndexRef.current + 1) % devices.length
      const next = devices[activeDeviceIndexRef.current]
      if (next) setDeviceId(next.deviceId)
      return
    }
    setDeviceId(null)
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
    const video = videoElRef.current
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
