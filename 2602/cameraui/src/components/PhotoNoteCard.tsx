import Typography from '@mui/material/Typography'
import TextField from '@mui/material/TextField'
import AlarmRounded from '@mui/icons-material/AlarmRounded'
import GestureRounded from '@mui/icons-material/GestureRounded'
import CardShell from './CardShell'
import RoundIconButton from './RoundIconButton'
import styles from './PhotoNoteCard.module.css'

interface PhotoNoteCardProps {
  date: Date
  subtitle?: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  onAlarmClick?: () => void
  onScribbleClick?: () => void
  minHeight?: number | string
}

const dateFormatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'long',
})

export default function PhotoNoteCard({
  date,
  subtitle = 'Today',
  value,
  onChange,
  placeholder = 'Tap to write a note..',
  onAlarmClick,
  onScribbleClick,
  minHeight = 420,
}: PhotoNoteCardProps) {
  return (
    <CardShell
      minHeight={minHeight}
      leftAction={
        <RoundIconButton onClick={onAlarmClick} size="small">
          <AlarmRounded fontSize="small" />
        </RoundIconButton>
      }
      centerContent={
        <div className={styles.headerText}>
          <Typography variant="subtitle1" className={styles.dateLabel}>
            {dateFormatter.format(date)}
          </Typography>
          <Typography variant="body2" className={styles.subtitleLabel}>
            {subtitle}
          </Typography>
        </div>
      }
      rightAction={
        <RoundIconButton onClick={onScribbleClick} size="small">
          <GestureRounded fontSize="small" />
        </RoundIconButton>
      }
    >
      <TextField
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        multiline
        variant="standard"
        fullWidth
        slotProps={{ input: { disableUnderline: true } }}
        className={styles.noteField}
      />
    </CardShell>
  )
}
