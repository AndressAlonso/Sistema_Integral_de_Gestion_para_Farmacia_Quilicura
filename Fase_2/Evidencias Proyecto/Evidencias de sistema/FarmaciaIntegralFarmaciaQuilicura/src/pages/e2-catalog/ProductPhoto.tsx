import { useState } from 'react'

export default function ProductPhoto({ src, name, large = false }: { src?: string | null; name: string; large?: boolean }) {
  const [failed, setFailed] = useState<string | null>(null)
  return <span className={`catalog-photo${large ? ' large' : ''}`}>
    {src && failed !== src ? <img src={src} alt={`Imagen de ${name}`} loading={large ? 'eager' : 'lazy'} onError={() => setFailed(src)} /> : <>
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="2" /><path d="m3 17 6-5 4 3 4-4 4 5" /></svg>
      <span className={large ? '' : 'sr-only'}>Sin imagen</span>
    </>}
  </span>
}
