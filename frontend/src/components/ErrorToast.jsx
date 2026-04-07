import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import useStore from '../store/useStore'

export default function ErrorToast() {
  const error    = useStore(s => s.error)
  const setError = useStore(s => s.setError)

  useEffect(() => {
    if (!error) return
    const t = setTimeout(() => setError(null), 5000)
    return () => clearTimeout(t)
  }, [error, setError])

  return (
    <div className="fixed top-16 right-4 z-50 pointer-events-none">
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded"
            style={{
              background: '#2d1515',
              border: '1px solid #e53e3e44',
              color: '#e53e3e',
              maxWidth: '320px',
              fontSize: '13px',
            }}
            onClick={() => setError(null)}
          >
            <span>⚠️</span>
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
