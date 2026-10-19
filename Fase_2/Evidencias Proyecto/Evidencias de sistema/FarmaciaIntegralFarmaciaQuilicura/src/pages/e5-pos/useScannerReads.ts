import { useEffect, useEffectEvent, useRef, useState } from 'react'

import { ApiError } from '../../services/http'
import { errorMessage, posApi, type Product } from './pos.api'
import { scannerApi } from './scanner.api'

export type ScannerAddResult = 'added' | 'rejected' | 'paused'

type Options = {
  linkId: string | null
  canReceive: () => boolean
  onProduct: (product: Product) => ScannerAddResult
}

export default function useScannerReads({
  linkId,
  canReceive,
  onProduct,
}: Options) {
  const processed = useRef(new Set<string>())
  const reading = useRef(false)

  const [notice, setNotice] = useState({ linkId: '', text: '' })
  const [failure, setFailure] = useState({ linkId: '', text: '' })

  const ready = useEffectEvent(canReceive)
  const addProduct = useEffectEvent(onProduct)

  useEffect(() => {
    if (!linkId) return

    const currentLink = linkId
    let disposed = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      let stop = false
      if (disposed) return

      if (!reading.current && ready()) {
        reading.current = true

        try {
          const reads = await scannerApi.pendingReads(currentLink)

          for (const read of reads) {
            if (disposed || !ready()) return

            if (read.link_id !== currentLink) {
              throw new Error('La lectura pertenece a otra vinculación.')
            }

            const key = `${currentLink}:${read.id}`

            if (!processed.current.has(key)) {
              let text = ''

              if (read.result === 'NOT_FOUND') {
                text = `Código ${read.code}: producto no encontrado.`
              } else if (read.result === 'INACTIVE') {
                text = `Código ${read.code}: producto desactivado.`
              } else {
                if (!read.product_id) {
                  throw new Error('Lectura sin producto.')
                }

                const result = await posApi.products(read.product_id)

                if (disposed || !ready()) return

                const product = result.products.find(
                  item => item.id === read.product_id,
                )

                if (!product) {
                  text = `Código ${read.code}: el producto ya no está disponible.`
                } else {
                  const outcome = addProduct(product)

                  if (outcome === 'paused') return

                  text = outcome === 'added'
                    ? `${product.name}: una unidad agregada desde el teléfono.`
                    : `${product.name}: no se agregó por falta de stock vendible.`
                }
              }

              // Si falla la confirmación, no se vuelve a sumar el producto.
              processed.current.add(key)
              setNotice({ linkId: currentLink, text })
            }

            await scannerApi.acknowledgeRead(currentLink, read.id)
          }

          if (!disposed) {
            setFailure({ linkId: currentLink, text: '' })
          }
        } catch (cause) {
          if (!disposed) {
            setFailure({
              linkId: currentLink,
              text: errorMessage(cause),
            })

            stop = cause instanceof ApiError &&
              [401, 403, 404, 409].includes(cause.status)
          }
        } finally {
          reading.current = false

          if (!disposed && !stop) {
            timer = setTimeout(() => void poll(), 1200)
          }
        }

        return
      }

      timer = setTimeout(() => void poll(), 1200)
    }

    timer = setTimeout(() => void poll(), 500)

    return () => {
      disposed = true
      if (timer !== undefined) clearTimeout(timer)
    }
  }, [linkId])

  return {
    scannerNotice: notice.linkId === linkId ? notice.text : '',
    scannerError: failure.linkId === linkId ? failure.text : '',
  }
}