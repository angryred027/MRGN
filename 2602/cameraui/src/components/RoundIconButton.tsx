import IconButton, { type IconButtonProps } from '@mui/material/IconButton'
import clsx from 'clsx'
import styles from './RoundIconButton.module.css'

export default function RoundIconButton({ className, ...props }: IconButtonProps) {
  return <IconButton className={clsx(styles.root, className)} {...props} />
}
