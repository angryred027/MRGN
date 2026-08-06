import { useState } from 'react'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import CameraCaptureCard from './components/CameraCaptureCard'
import PhotoNoteCard from './components/PhotoNoteCard'

export default function App() {
  const [note, setNote] = useState('')

  return (
    <Box
      sx={{
        minHeight: '100%',
        display: 'flex',
        justifyContent: 'center',
        bgcolor: 'grey.100',
        py: 6,
        px: 2,
      }}
    >
      <Stack spacing={3} sx={{ width: '100%', maxWidth: 420 }}>
        <CameraCaptureCard onPhotoReady={(src) => console.log('photo ready', src)} />
        <PhotoNoteCard date={new Date()} value={note} onChange={setNote} />
      </Stack>
    </Box>
  )
}
