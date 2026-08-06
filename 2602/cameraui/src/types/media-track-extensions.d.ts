export {}

declare global {
  interface MediaTrackCapabilities {
    torch?: boolean
    zoom?: { min: number; max: number; step: number }
  }

  interface MediaTrackConstraintSet {
    torch?: boolean
    zoom?: number
    pointsOfInterest?: Array<{ x: number; y: number }>
  }

  interface MediaTrackSettings {
    zoom?: number
  }
}
